from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import SendOTPSerializer, VerifyOTPSerializer, UserSerializer
from .models import PasswordResetCode
from .utils import send_sms_task_or_sync, register_device_for_user
from .throttles import SMSRequestThrottle
from rest_framework.throttling import AnonRateThrottle
from django.db import transaction

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