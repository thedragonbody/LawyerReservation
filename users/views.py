from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.core.mail import send_mail

from .models import User, ClientProfile, LawyerProfile
from .serializers import (
    UserSerializer, ClientProfileSerializer, LawyerProfileSerializer,
    ChangePasswordSerializer, LogoutSerializer, LawyerListSerializer,
    CustomTokenObtainPairSerializer, PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer
)

# ----------------------------
# Register API
# ----------------------------
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        # User با is_active=False ساخته می‌شود
        user = serializer.save(is_active=False)
        # ارسال ایمیل تایید
        token_generator = PasswordResetTokenGenerator()
        token = token_generator.make_token(user)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        verify_link = f"http://localhost:3000/verify-email/{uidb64}/{token}/"

        send_mail(
            "Verify your email",
            f"Click to verify your account: {verify_link}",
            "no-reply@alovakil.com",
            [user.email],
            fail_silently=False,
        )

# ----------------------------
# Email Verification
# ----------------------------
class VerifyEmailView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        uidb64 = request.query_params.get("uidb64")
        token = request.query_params.get("token")
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"detail": "Invalid UID."}, status=status.HTTP_400_BAD_REQUEST)

        token_generator = PasswordResetTokenGenerator()
        if not token_generator.check_token(user, token):
            return Response({"detail": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)

        user.is_active = True
        user.save()
        return Response({"detail": "Email verified successfully."}, status=status.HTTP_200_OK)

# ----------------------------
# Login API (JWT)
# ----------------------------
class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]

# ----------------------------
# Refresh JWT Token
# ----------------------------
class RefreshTokenView(TokenRefreshView):
    permission_classes = [AllowAny]

# ----------------------------
# Logout API (JWT Blacklist)
# ----------------------------
class LogoutView(generics.GenericAPIView):
    serializer_class = LogoutSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Logout successful."}, status=status.HTTP_204_NO_CONTENT)

# ----------------------------
# Client Profile API
# ----------------------------
class ClientProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ClientProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        profile, _ = ClientProfile.objects.get_or_create(user=self.request.user)
        return profile

# ----------------------------
# Lawyer Profile API
# ----------------------------
class LawyerProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = LawyerProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        profile, _ = LawyerProfile.objects.get_or_create(user=self.request.user)
        return profile

# ----------------------------
# Change Password API
# ----------------------------
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

# ----------------------------
# List of Lawyers
# ----------------------------
class LawyerListView(generics.ListAPIView):
    queryset = LawyerProfile.objects.filter(status=LawyerProfile.Status.APPROVED)
    serializer_class = LawyerListSerializer
    permission_classes = [AllowAny]

# ----------------------------
# Password Reset Request
# ----------------------------
class PasswordResetRequestView(generics.GenericAPIView):
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.get(email=serializer.validated_data['email'])
        token_generator = PasswordResetTokenGenerator()
        token = token_generator.make_token(user)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

        reset_link = f"http://localhost:3000/reset-password/{uidb64}/{token}/"

        send_mail(
            "Password Reset Request",
            f"Click the link to reset your password: {reset_link}",
            "no-reply@alovakil.com",
            [user.email],
            fail_silently=False,
        )

        return Response({"detail": "Password reset link sent to email."}, status=status.HTTP_200_OK)

# ----------------------------
# Password Reset Confirm
# ----------------------------
class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password reset successful."}, status=status.HTTP_200_OK)