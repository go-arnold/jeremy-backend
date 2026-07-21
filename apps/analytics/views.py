from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .serializers import DashboardStatsSerializer


@extend_schema(
    tags=["Analytics"],
    responses=DashboardStatsSerializer,
    examples=[
        OpenApiExample(
            "Statistiques du tableau de bord",
            value={
                "counts": {"artists": 128, "articles": 340, "events": 24, "podcast_episodes": 512},
                "totals": {"article_views": 98234, "webtv_views": 45210, "podcast_plays": 61234},
                "top_articles": [{"title": "La scène musicale de Goma en 2026", "view_count": 4210}],
                "top_webtv_videos": [{"title": "Freestyle #12", "view_count": 3820}],
                "top_podcast_episodes": [{"title": "Épisode 12", "play_count": 2110}],
            },
            response_only=True,
        )
    ],
)
class DashboardStatsView(APIView):
    """Site-wide aggregate stats. Cached 10 minutes — not real-time."""

    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        return Response(services.get_dashboard_stats())
