from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from drf_spectacular.utils import extend_schema
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.accounts.views import EmailConfirmRedirectView


@extend_schema(tags=["System"])
@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    return Response({"status": "ok"})


urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("api/v1/health/", health_check),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("api/schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/v1/auth/", include("apps.accounts.urls")),
    # These patterns shadow allauth's built-in HTML views (included below via
    # `accounts/`) and instead redirect browsers to the decoupled frontend.
    # They must appear BEFORE `path("accounts/", include("allauth.urls"))`.
    re_path(
        r"^accounts/confirm-email/(?P<key>[-:\w]+)/$",
        EmailConfirmRedirectView.as_view(),
        name="account_confirm_email",
    ),
    re_path(
        r"^accounts/password/reset/key/(?P<uidb36>[0-9A-Za-z_\-]+)-(?P<key>.+)/$",
        RedirectView.as_view(
            url=settings.FRONTEND_URL + "/password-reset-confirm/%(uidb36)s/%(key)s/",
            permanent=False,
        ),
        name="account_reset_password_from_key",
    ),
    # Safety net for any code that still reverses this name with uidb64/token kwargs.
    re_path(
        r"^password-reset-confirm/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,40})/$",
        RedirectView.as_view(
            url=settings.FRONTEND_URL + "/password-reset-confirm/%(uidb64)s/%(token)s/",
            permanent=False,
        ),
        name="password_reset_confirm",
    ),
    path("accounts/", include("allauth.urls")),
    path("api/v1/artists/", include("apps.artists.urls")),
    path("api/v1/articles/", include("apps.articles.urls")),
    path("api/v1/events/", include("apps.events.urls")),
    path("api/v1/podcasts/", include("apps.podcasts.urls")),
    path("api/v1/radio/", include("apps.radio.urls")),
    path("api/v1/webtv/", include("apps.webtv.urls")),
    path("api/v1/community/", include("apps.community.urls")),
    path("api/v1/releases/", include("apps.releases.urls")),
    path("api/v1/emissions/", include("apps.emissions.urls")),
    path("api/v1/users/", include("apps.accounts.user_urls")),
    path("api/v1/home/", include("apps.artists.home_urls")),
]
