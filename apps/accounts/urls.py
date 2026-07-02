from django.urls import path

from .views import (
    GoogleLoginView,
    MeView,
    TaggedLoginView,
    TaggedLogoutView,
    TaggedPasswordResetConfirmView,
    TaggedPasswordResetView,
    TaggedRegisterView,
    TaggedTokenRefreshView,
    TaggedVerifyEmailView,
)

urlpatterns = [
    path("register/", TaggedRegisterView.as_view(), name="auth_register"),
    path("login/", TaggedLoginView.as_view(), name="auth_login"),
    path("logout/", TaggedLogoutView.as_view(), name="auth_logout"),
    path("token/refresh/", TaggedTokenRefreshView.as_view(), name="token_refresh"),
    path("google/", GoogleLoginView.as_view(), name="auth_google_login"),
    path("verify-email/", TaggedVerifyEmailView.as_view(), name="auth_verify_email"),
    path("password/reset/", TaggedPasswordResetView.as_view(), name="auth_password_reset"),
    # Renamed from "password_reset_confirm" to avoid shadowing the global
    # safety-net URL defined in root urls.py with the same name.
    path(
        "password/reset/confirm/",
        TaggedPasswordResetConfirmView.as_view(),
        name="auth_password_reset_confirm",
    ),
    path("me/", MeView.as_view(), name="auth_me"),
]
