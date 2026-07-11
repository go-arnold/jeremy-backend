from django.views.decorators.cache import cache_page
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from . import services


@extend_schema(tags=["Home"])
@api_view(["GET"])
@permission_classes([AllowAny])
@cache_page(60 * 15)
def home_view(request):
    """Aggregated homepage payload — cached 15 minutes."""
    return Response(services.get_home_payload())
