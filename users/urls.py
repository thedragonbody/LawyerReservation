from django.urls import path
from .views import SendLoginOTPView, VerifyLoginOTPView, ResendOTPView, DeviceListView, RevokeDeviceView, SecurityCheckView, BlacklistCleanupView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path("send-login-otp/", SendLoginOTPView.as_view(), name="send-login-otp"),
    path("verify-login-otp/", VerifyLoginOTPView.as_view(), name="verify-login-otp"),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path("otp/resend/", ResendOTPView.as_view(), name="otp-resend"),
    path("devices/", DeviceListView.as_view(), name="devices-list"),
    path("devices/<int:device_id>/revoke/", RevokeDeviceView.as_view(), name="device-revoke"),
    path("security/check/", SecurityCheckView.as_view(), name="security-check"),
    path("blacklist/cleanup/", BlacklistCleanupView.as_view(), name="blacklist-cleanup"),
]
