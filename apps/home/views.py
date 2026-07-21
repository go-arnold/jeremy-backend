from django.views.decorators.cache import cache_page
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsAdminOrReadOnly

from . import services
from .models import HomeBanner
from .serializers import HomeBannerSerializer, HomeBannerWriteSerializer


@extend_schema(
    tags=["Home"],
    responses=OpenApiTypes.OBJECT,
    examples=[
        OpenApiExample(
            "Payload accueil",
            value={
                "banner": {
                    "image_url": None,
                    "title": "Bienvenue sur Art du Kivu",
                    "subtitle": "",
                    "cta_label": "",
                    "cta_url": "",
                },
                "a_la_une": {"artist_of_month": None, "featured_podcast": None, "featured_event": None},
                "hits_du_mois": [],
                "magazine": {"hero": None, "articles": []},
            },
            response_only=True,
        )
    ],
)
@api_view(["GET"])
@permission_classes([AllowAny])
@cache_page(60 * 15)
def home_view(request):
    """Aggregated homepage payload — cached 15 minutes."""
    return Response(services.get_home_payload())


@extend_schema(tags=["Home"])
class HomeBannerView(APIView):
    """Singleton homepage banner — configurable from the admin without a DB shell session
    (BACKEND-GAPS-COMPLET.md §5 "Bannière home")."""

    permission_classes = [IsAdminOrReadOnly]

    @extend_schema(responses=HomeBannerSerializer)
    def get(self, request):
        return Response(HomeBannerSerializer(HomeBanner.get_solo()).data)

    @extend_schema(request=HomeBannerWriteSerializer, responses=HomeBannerSerializer)
    def patch(self, request):
        banner = HomeBanner.get_solo()
        ser = HomeBannerWriteSerializer(banner, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        # `home_view`'s @cache_page key is an opaque per-URL hash, not a named key this can
        # selectively invalidate — an update here takes up to the full 15-minute TTL to appear
        # on GET /home/. This endpoint itself (GET /home/banner/) always reflects the change
        # immediately, since it isn't cached.
        return Response(HomeBannerSerializer(banner).data)
