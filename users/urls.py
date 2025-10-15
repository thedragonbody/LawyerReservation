from django.urls import path
from .views import (
    RegisterView,
    LoginView,
    LogoutView,
    RefreshTokenView,
    ClientProfileView,
    LawyerProfileView,
    ChangePasswordView,
    LawyerListView,
)

urlpatterns = [
    # ---------------- Auth ----------------
    path("signup/", RegisterView.as_view(), name="signup"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("token/refresh/", RefreshTokenView.as_view(), name="token_refresh"),

    # ---------------- Profiles ----------------
    path("client-profile/", ClientProfileView.as_view(), name="client_profile"),
    path("lawyer-profile/", LawyerProfileView.as_view(), name="lawyer_profile"),

    # ---------------- Change Password ----------------
    path("change-password/", ChangePasswordView.as_view(), name="change_password"),

    # ---------------- List of Lawyers ----------------
    path("lawyers/", LawyerListView.as_view(), name="lawyer_list"),
]