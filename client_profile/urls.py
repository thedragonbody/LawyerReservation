from django.urls import path
from .views import (
    DeviceListView,
    RevokeDeviceView,
    SendOTPView,
    ToggleFavoriteLawyerView,
    VerifyOTPView,
)

urlpatterns = [
    path("send-otp/", SendOTPView.as_view(), name="send-otp"),
    path("verify-otp/", VerifyOTPView.as_view(), name="verify-otp"),
    path("favorites/toggle/<int:lawyer_id>/", ToggleFavoriteLawyerView.as_view(), name="toggle-favorite"),
    path("devices/", DeviceListView.as_view(), name="device-list"),
    path("devices/<int:pk>/revoke/", RevokeDeviceView.as_view(), name="device-revoke"),
]
