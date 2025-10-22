from django.urls import path
from .views import SendLoginOTPView, VerifyLoginOTPView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path("send-login-otp/", SendLoginOTPView.as_view(), name="send-login-otp"),
    path("verify-login-otp/", VerifyLoginOTPView.as_view(), name="verify-login-otp"),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
