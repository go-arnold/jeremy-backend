from dj_rest_auth.registration.views import RegisterView, VerifyEmailView
from dj_rest_auth.views import LoginView, LogoutView, PasswordResetConfirmView, PasswordResetView
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import GoogleLoginView, MeView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth_register"),
    path("login/", LoginView.as_view(), name="auth_login"),
    path("logout/", LogoutView.as_view(), name="auth_logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("google/", GoogleLoginView.as_view(), name="auth_google_login"),

    # Email verification: frontend POSTs {"key": "..."} here after the user
    # clicks the link that lands on /verify-email?key=... in the SPA.
    path("verify-email/", VerifyEmailView.as_view(), name="auth_verify_email"),

    # Password reset (two-step API)
    path("password/reset/", PasswordResetView.as_view(), name="auth_password_reset"),
    # Renamed from "password_reset_confirm" to avoid shadowing the global
    # safety-net URL defined in root urls.py with the same name.
    path(
        "password/reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="auth_password_reset_confirm",
    ),

    path("me/", MeView.as_view(), name="auth_me"),
]
