from django.urls import path
from .views import SendOTPView, VerifyOTPView, ToggleFavoriteLawyerView, DeviceListView, RevokeDeviceView

urlpatterns = [
    path("send-otp/", SendOTPView.as_view(), name="send-otp"),
    path("verify-otp/", VerifyOTPView.as_view(), name="verify-otp"),
    path("favorites/toggle/<int:lawyer_id>/", ToggleFavoriteLawyerView.as_view(), name="toggle-favorite"),
    path("devices/", DeviceListView.as_view(), name="devices-list"),
    path("devices/<int:device_id>/revoke/", RevokeDeviceView.as_view(), name="device-revoke"),
]