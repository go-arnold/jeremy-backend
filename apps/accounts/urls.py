from dj_rest_auth.registration.views import RegisterView
from dj_rest_auth.views import LoginView, LogoutView, PasswordResetConfirmView, PasswordResetView
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import GoogleLoginView, MeView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth_register"),
    path("login/", LoginView.as_view(), name="auth_login"),
    path("logout/", LogoutView.as_view(), name="auth_logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("google/", GoogleLoginView.as_view(), name="google_login"),
    path("password/reset/", PasswordResetView.as_view(), name="password_reset"),
    path("password/reset/confirm/", PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("me/", MeView.as_view(), name="auth_me"),
]
