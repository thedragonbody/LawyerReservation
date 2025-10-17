from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from rest_framework.pagination import PageNumberPagination
from .models import PasswordResetCode
from django.contrib.auth.hashers import make_password
from django.shortcuts import get_object_or_404

from .models import User, ClientProfile, LawyerProfile
from .serializers import (
    UserSerializer, ClientProfileSerializer, LawyerProfileSerializer,
    ChangePasswordSerializer, LogoutSerializer, LawyerListSerializer,
    CustomTokenObtainPairSerializer,ForgotPasswordSerializer, ResetPasswordSerializer,
    PhoneSerializer, VerifyOTPSerializer
)

# ================================
# Sign Up (ثبت نام با OTP)
# ================================
User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()  # کاربر غیرفعال ایجاد می‌شود
        code = PasswordResetCode.generate_code(user.phone_number)

        # TODO: ارسال OTP از طریق سرویس پیامک (در حال حاضر print)
        print(f"📱 کد تأیید ثبت‌نام برای {user.phone_number}: {code}")

        return Response({
            "detail": "کد تأیید به شماره شما ارسال شد. لطفاً برای فعال‌سازی حساب، OTP را وارد کنید."
        }, status=201)

# ================================
# Login (JWT)
# ================================
class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]


# ================================
# Refresh Token (در صورت نیاز)
# ================================
class RefreshTokenView(TokenRefreshView):
    permission_classes = [AllowAny]


# ================================
# Logout (JWT blacklist)
# ================================
class LogoutView(generics.GenericAPIView):
    serializer_class = LogoutSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Logout successful."}, status=status.HTTP_204_NO_CONTENT)


# ================================
# Client Profile
# ================================
class ClientProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ClientProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        profile, _ = ClientProfile.objects.get_or_create(user=self.request.user)
        return profile


# ================================
# Lawyer Profile
# ================================
class LawyerProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = LawyerProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        profile, _ = LawyerProfile.objects.get_or_create(user=self.request.user)
        return profile


# ================================
# Change Password
# ================================
class ChangePasswordView(generics.UpdateAPIView):
    serializer_class = ChangePasswordSerializer
    model = User
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not user.check_password(serializer.validated_data['old_password']):
            return Response({"old_password": ["Wrong password."]}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({"detail": "Password updated successfully."}, status=status.HTTP_200_OK)


# ================================
# List of Lawyers (با pagination)
# ================================

class LawyerListPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50

class LawyerListView(generics.ListAPIView):
    queryset = LawyerProfile.objects.filter(status=LawyerProfile.Status.APPROVED)
    serializer_class = LawyerListSerializer
    permission_classes = [AllowAny]
    pagination_class = LawyerListPagination

# اگر بخوای با SMS واقعی کار کنی، اینجا سرویس Kavenegar یا Ghasedak رو می‌تونی ایمپورت کنی

class ForgotPasswordView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = PhoneSerializer

    def post(self, request):
        phone = request.data.get('phone_number')
        user = get_object_or_404(User, phone_number=phone)

        # تولید OTP و ذخیره خودکار در دیتابیس
        code = PasswordResetCode.generate_code(phone)

        # TODO: ارسال کد از طریق سرویس پیامک
        print(f"📱 کد تأیید برای {phone}: {code}")

        return Response({"detail": "کد تأیید برای بازیابی رمز ارسال شد."})

class ResetPasswordView(generics.GenericAPIView):
    serializer_class = ResetPasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data['phone_number']
        code = serializer.validated_data['code']
        new_password = serializer.validated_data['new_password']

        try:
            otp_obj = PasswordResetCode.objects.filter(phone_number=phone_number, code=code, is_used=False).latest('created_at')
        except PasswordResetCode.DoesNotExist:
            return Response({"detail": "Invalid or expired code."}, status=400)

        if not otp_obj.is_valid():
            return Response({"detail": "OTP expired or already used."}, status=400)

        user = User.objects.get(phone_number=phone_number)
        user.password = make_password(new_password)
        user.save()

        otp_obj.is_used = True
        otp_obj.save()

        return Response({"detail": "Password reset successfully."}, status=200)
    
class VerifyOTPView(generics.GenericAPIView):
    serializer_class = VerifyOTPSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        # ایجاد توکن JWT برای ورود همزمان
        refresh = RefreshToken.for_user(user)

        return Response({
            "detail": "حساب فعال شد و ورود انجام شد.",
            "user": {
                "id": user.id,
                "phone_number": user.phone_number,
                "first_name": user.first_name,
                "last_name": user.last_name,
            },
            "token": {
                "refresh": str(refresh),
                "access": str(refresh.access_token)
            }
        }, status=200)