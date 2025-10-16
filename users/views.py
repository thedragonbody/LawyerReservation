from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from rest_framework.pagination import PageNumberPagination

from .models import User, ClientProfile, LawyerProfile
from .serializers import (
    UserSerializer, ClientProfileSerializer, LawyerProfileSerializer,
    ChangePasswordSerializer, LogoutSerializer, LawyerListSerializer,
    CustomTokenObtainPairSerializer,ForgotPasswordSerializer, ResetPasswordSerializer
)

# ================================
# Sign Up (ثبت نام با OTP)
# ================================
User = get_user_model()


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        # ساخت کاربر بدون نیاز به ایمیل یا فعالسازی
        user = serializer.save(is_active=True)
        return user

    def create(self, request, *args, **kwargs):
        """
        override برای ارسال پاسخ ساده‌تر در فرانت
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            {"message": "ثبت‌نام با موفقیت انجام شد", "user": serializer.data},
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

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
    serializer_class = ForgotPasswordSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data["phone_number"]
        code = PasswordResetCode.generate_code()

        PasswordResetCode.objects.create(phone_number=phone, code=code)

        # در حالت واقعی باید SMS ارسال بشه:
        print(f"📱 کد تأیید برای {phone}: {code}")

        return Response({"detail": "کد تأیید ارسال شد."}, status=status.HTTP_200_OK)


class ResetPasswordView(generics.GenericAPIView):
    serializer_class = ResetPasswordSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "رمز عبور با موفقیت تغییر کرد."}, status=status.HTTP_200_OK)