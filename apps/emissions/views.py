from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.pagination import StandardPagination
from core.permissions import IsAdminOrReadOnly

from .models import Emission
from .serializers import EmissionDetailSerializer, EmissionListSerializer, EmissionWriteSerializer


class EmissionViewSet(ModelViewSet):
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = StandardPagination
    search_fields = ["title", "description"]
    ordering_fields = ["scheduled_at", "created_at"]
    lookup_field = "slug"

    def get_queryset(self):
        qs = Emission.objects.prefetch_related("hosts")
        emission_status = self.request.query_params.get("status")
        if emission_status:
            qs = qs.filter(status=emission_status)
        return qs.order_by("-scheduled_at")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return EmissionWriteSerializer
        if self.action == "retrieve":
            return EmissionDetailSerializer
        return EmissionListSerializer

    @method_decorator(cache_page(60))
    @action(detail=False, methods=["get"])
    def live(self, request):
        emission = Emission.objects.filter(status=Emission.STATUS_LIVE).first()
        if not emission:
            return Response({"detail": "No emission currently live."}, status=status.HTTP_404_NOT_FOUND)
        return Response(EmissionDetailSerializer(emission).data)
