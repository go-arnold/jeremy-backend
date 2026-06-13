from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    return Response({"status": "ok"})


urlpatterns = [
    path("django-admin/", admin.site.urls),

    # Health
    path("api/v1/health/", health_check),

    # API docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("api/schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),

    # Auth
    path("api/v1/auth/", include("apps.accounts.urls")),

    # Resources
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
