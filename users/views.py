from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import SendOTPSerializer, VerifyOTPSerializer, UserSerializer, DeviceListSerializer
from .models import PasswordResetCode
from .utils import send_sms_task_or_sync, register_device_for_user
from .throttles import SMSRequestThrottle
from rest_framework.throttling import AnonRateThrottle
from django.db import transaction
from .serializers import ResendOTPSerializer
from rest_framework.views import APIView
from client_profile.models import ClientProfile
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from rest_framework.permissions import IsAdminUser
from datetime import timedelta
from rest_framework.permissions import IsAuthenticated
from client_profile.models import Device
from django.shortcuts import get_object_or_404

User = get_user_model()


class OTPThrottle(AnonRateThrottle):
    scope = 'otp'  # مطابقت با REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']


class SendLoginOTPView(generics.GenericAPIView):
    """
    ارسال OTP برای ورود/ثبت‌نام (Passwordless) از طریق SMS.
    اگر کاربر وجود نداشته باشد، یک رکورد با is_active=False ساخته می‌شود.
    """
    serializer_class = SendOTPSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [SMSRequestThrottle, OTPThrottle]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data['phone_number']

        # ایجاد یا بازیابی کاربر (inactive تا تایید)
        user, _ = User.objects.get_or_create(phone_number=phone, defaults={'is_active': False})

        # تولید OTP (PasswordResetCode.generate_code وظیفه ذخیره و print/send را دارد)
        code = PasswordResetCode.generate_code(phone, 'login')

        # ارسال پیامک (سعی می‌کنیم با Celery ارسال کنیم و در صورت نبودن fallback کنیم)
        message = f"کد ورود شما: {code}"
        try:
            # send_sms_task_or_sync داخل خودش تلاش می‌کنه از Celery استفاده کنه
            send_sms_task_or_sync(phone, message)
        except Exception:
            # نباید crash کنه — fallback داخلی در send_sms_task_or_sync هست
            pass

        return Response({"detail": "کد ورود ارسال شد."}, status=status.HTTP_200_OK)


class VerifyLoginOTPView(generics.GenericAPIView):
    """
    تایید OTP و صدور توکن JWT. پس از تایید، کاربر فعال می‌شود و توکن‌ها برگردانده می‌شود.
    """
    serializer_class = VerifyOTPSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data['phone_number']

        user = User.objects.filter(phone_number=phone).first()
        if not user:
            return Response({"detail": "کاربر یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        # فعال‌سازی کاربر
        user.is_active = True
        user.save(update_fields=['is_active'])

        # ساخت ClientProfile در صورت وجود اپ (import داخل try برای جلوگیری از circular import)
        try:
            from client_profile.models import ClientProfile
            ClientProfile.objects.get_or_create(user=user)
        except Exception:
            # اگر اپ وجود نداشت یا خطایی وجود داشت، لاگ کن یا نادیده بگیر
            pass

        # ثبت دستگاه (سعی می‌کنیم غیرهمزمان ثبت کنیم)
        try:
            register_device_for_user(user, request)
        except Exception:
            pass

        # صدور توکن JWT
        refresh = RefreshToken.for_user(user)
        tokens = {
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        }

        user_data = UserSerializer(user).data
        return Response({'detail': 'ورود موفق', 'tokens': tokens, 'user': user_data}, status=status.HTTP_200_OK)
    

class ResendOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data['phone_number']

        # کاربر یا پروفایل را پیدا کن
        from users.models import User
        user, _ = User.objects.get_or_create(phone_number=phone, defaults={'is_active': False})
        cp, _ = ClientProfile.objects.get_or_create(user=user)

        # بررسی زمان ارسال قبلی
        if cp.phone_verification_sent_at and timezone.now() - cp.phone_verification_sent_at < timedelta(seconds=60):
            return Response({"detail": "درخواست زود است. لطفاً بعداً دوباره تلاش کنید."},
                            status=status.HTTP_429_TOO_MANY_REQUESTS)

        code = cp.generate_phone_code()
        send_sms_task_or_sync(phone, f"کد تأیید شما: {code}")

        return Response({"detail": "کد تأیید ارسال شد."}, status=status.HTTP_200_OK)


class DeviceListView(generics.ListAPIView):
    serializer_class = DeviceListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        cp = getattr(self.request.user, 'client_profile', None)
        if cp:
            return Device.objects.filter(client=cp).order_by('-last_seen')
        return Device.objects.none()
    
class RevokeDeviceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, device_id):
        cp = getattr(request.user, 'client_profile', None)
        device = get_object_or_404(Device, pk=device_id, client=cp)
        device.revoked = True
        device.save(update_fields=['revoked'])
        return Response({"detail": "دستگاه غیرفعال شد."}, status=status.HTTP_200_OK)
    
class SecurityCheckView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cp = getattr(request.user, 'client_profile', None)
        if not cp:
            return Response({"detail": "Client profile not found."}, status=404)

        current_ip = request.META.get('REMOTE_ADDR')
        last_ip = cp.last_login_ip

        ip_changed = last_ip != current_ip
        last_seen_ago = None
        if cp.last_login_ip:
            last_seen_ago = (timezone.now() - cp.updated_at).total_seconds()

        data = {
            "ip_changed": ip_changed,
            "last_login_ip": last_ip,
            "current_ip": current_ip,
            "last_seen_seconds_ago": last_seen_ago,
        }
        return Response(data, status=200)
    
class BlacklistCleanupView(APIView):
    permission_classes = [IsAdminUser]  # فقط ادمین

    def post(self, request):
        # حذف تمام refresh token های قدیمی تر از 30 روز
        threshold = timezone.now() - timedelta(days=30)
        tokens = OutstandingToken.objects.filter(created__lt=threshold)
        count = tokens.count()
        for token in tokens:
            BlacklistedToken.objects.get_or_create(token=token)
        tokens.delete()
        return Response({"detail": f"{count} refresh token منقضی شدند."})