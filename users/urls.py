from django.urls import path
from .views import (
    RegisterView, LoginView, RefreshTokenView, LogoutView,
    ClientProfileView, LawyerProfileView, ChangePasswordView,
    LawyerListView, PasswordResetRequestView, PasswordResetConfirmView,
    VerifyEmailView
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="users-register"),
    path("verify-email/", VerifyEmailView.as_view(), name="users-verify-email"),
    path("login/", LoginView.as_view(), name="users-login"),
    path("token/refresh/", RefreshTokenView.as_view(), name="token-refresh"),
    path("logout/", LogoutView.as_view(), name="users-logout"),
    path("profile/client/", ClientProfileView.as_view(), name="users-client-profile"),
    path("profile/lawyer/", LawyerProfileView.as_view(), name="users-lawyer-profile"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("lawyers/", LawyerListView.as_view(), name="users-lawyers"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="users-password-reset"),
    path("password-reset-confirm/", PasswordResetConfirmView.as_view(), name="users-password-reset-confirm"),
]