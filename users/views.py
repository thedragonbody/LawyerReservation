from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, ClientProfile, LawyerProfile
from .serializers import (
    UserSerializer, ClientProfileSerializer, LawyerProfileSerializer,
    ChangePasswordSerializer, LogoutSerializer, LawyerListSerializer,
    CustomTokenObtainPairSerializer
)

# ================================
# Sign Up (ثبت نام با OTP)
# ================================
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        # TODO: ارسال OTP به شماره کاربر
        # مثال: send_otp(user.phone_number)
        return user


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
from rest_framework.pagination import PageNumberPagination

class LawyerListPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50

class LawyerListView(generics.ListAPIView):
    queryset = LawyerProfile.objects.filter(status=LawyerProfile.Status.APPROVED)
    serializer_class = LawyerListSerializer
    permission_classes = [AllowAny]
    pagination_class = LawyerListPagination