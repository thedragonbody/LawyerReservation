from django.urls import path
from .views import SendOTPView, VerifyOTPView, ToggleFavoriteLawyerView, DeviceListView, RevokeDeviceView

urlpatterns = [
    path("send-otp/", SendOTPView.as_view(), name="send-otp"),
    path("verify-otp/", VerifyOTPView.as_view(), name="verify-otp"),
    path("favorites/toggle/<int:lawyer_id>/", ToggleFavoriteLawyerView.as_view(), name="toggle-favorite"),
]