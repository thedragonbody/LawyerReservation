from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import (
    UserSerializer, CustomTokenObtainPairSerializer,
    VerifyOTPSerializer, ForgotPasswordSerializer, ResetPasswordSerializer
)
from .models import PasswordResetCode
from .utils import register_device_for_user

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """ثبت‌نام با شماره موبایل و ارسال OTP"""
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        phone = request.data.get('phone_number')
        if not phone:
            return Response({"detail": "شماره موبایل الزامی است."}, status=400)

        user, created = User.objects.get_or_create(phone_number=phone)
        if not user.is_active:
            user.is_active = False
            user.save(update_fields=['is_active'])

        PasswordResetCode.generate_code(phone, 'signup')
        return Response({"detail": "کد تأیید ارسال شد."}, status=201)


class VerifyOTPView(generics.GenericAPIView):
    """تأیید OTP و فعال‌سازی کاربر"""
    serializer_class = VerifyOTPSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data['phone_number']
        user = User.objects.filter(phone_number=phone).first()
        if not user:
            return Response({"detail": "کاربر یافت نشد."}, status=404)

        user.is_active = True
        user.save(update_fields=['is_active'])

        # ایجاد ClientProfile در صورت عدم وجود
        from client_profile.models import ClientProfile
        ClientProfile.objects.get_or_create(user=user)

        # ثبت دستگاه
        register_device_for_user(user, request)

        # ایجاد توکن
        token_serializer = CustomTokenObtainPairSerializer(data={
            'phone_number': phone,
            'password': None
        })
        token = CustomTokenObtainPairSerializer.get_token(user)
        data = {
            'access': str(token.access_token),
            'refresh': str(token),
        }
        return Response({'detail': 'تأیید شد', 'tokens': data}, status=200)


class LoginView(TokenObtainPairView):
    """ورود با شماره و رمز عبور"""
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            user = User.objects.filter(phone_number=request.data.get('phone_number')).first()
            if user:
                register_device_for_user(user, request)
        return response


class ForgotPasswordView(generics.GenericAPIView):
    serializer_class = ForgotPasswordSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({"detail": "در صورت وجود حساب، کد ارسال شد."}, status=200)


class ResetPasswordView(generics.GenericAPIView):
    serializer_class = ResetPasswordSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "رمز عبور با موفقیت تغییر یافت."}, status=200)