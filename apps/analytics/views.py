from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .serializers import DashboardStatsSerializer


@extend_schema(tags=["Analytics"], responses=DashboardStatsSerializer)
class DashboardStatsView(APIView):
    """Site-wide aggregate stats. Cached 10 minutes — not real-time."""

    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        return Response(services.get_dashboard_stats())
