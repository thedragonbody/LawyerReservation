from django.urls import path
from .views import (
    RegisterView,
    LoginView,
    LogoutView,
    RefreshTokenView,
    ChangePasswordView,
    ForgotPasswordView,   
    ResetPasswordView,    
    VerifyOTPView,
)

urlpatterns = [
    # ---------------- Auth ----------------
    path("signup/", RegisterView.as_view(), name="signup"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("token/refresh/", RefreshTokenView.as_view(), name="token_refresh"),
    path("verify-otp/", VerifyOTPView.as_view(), name="verify_otp"),

    # ---------------- Passwords ----------------
    path("change-password/", ChangePasswordView.as_view(), name="change_password"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot_password"),  
    path("reset-password/", ResetPasswordView.as_view(), name="reset_password"),

]