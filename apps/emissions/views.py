from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.engagement.mixins import EngagementActionsMixin
from core.pagination import StandardPagination
from core.permissions import IsAdminOrReadOnly
from core.serializers import BulkDeleteSerializer
from core.throttling import UploadThrottleMixin

from . import services
from .models import Emission
from .serializers import (
    EmissionBulkCreateSerializer,
    EmissionBulkUpdateSerializer,
    EmissionDetailSerializer,
    EmissionListSerializer,
    EmissionWriteSerializer,
)


@extend_schema(tags=["Emissions"])
class EmissionViewSet(UploadThrottleMixin, EngagementActionsMixin, ModelViewSet):
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = StandardPagination
    search_fields = ["title", "description"]
    ordering_fields = ["scheduled_at", "created_at"]
    lookup_field = "slug"
    # No `enable_save = False` here — services.toggle_save already blocks saving
    # while status == "live"; a past (recorded) emission remains saveable.

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

    def perform_create(self, serializer):
        serializer.instance = services.create_emission(dict(serializer.validated_data))

    def perform_update(self, serializer):
        serializer.instance = services.update_emission(serializer.instance, dict(serializer.validated_data))

    def perform_destroy(self, instance):
        services.delete_emission(instance)

    @action(detail=False, methods=["get"])
    def live(self, request):
        emission = services.get_live_emission()
        if not emission:
            return Response(
                {"detail": "Aucune émission en direct actuellement."}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(EmissionDetailSerializer(emission).data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def go_live(self, request, slug=None):
        emission = services.start_live(self.get_object())
        return Response(
            {
                "status": emission.status,
                "cf_rtmps_url": emission.cf_rtmps_url,
                "cf_rtmps_key": emission.cf_rtmps_key,
                "cf_playback_hls_url": emission.cf_playback_hls_url,
            }
        )

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def end_live(self, request, slug=None):
        emission = services.end_live(self.get_object())
        return Response({"status": emission.status})

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def bulk_create(self, request):
        ser = EmissionBulkCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        created = services.bulk_create_emissions(ser.validated_data["items"])
        return Response(
            {"created": len(created), "items": EmissionListSerializer(created, many=True).data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def bulk_update(self, request):
        ser = EmissionBulkUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        count = services.bulk_update_emissions(ser.validated_data["items"])
        return Response({"updated": count})

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def bulk_delete(self, request):
        ser = BulkDeleteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        count = services.bulk_delete_emissions(ser.validated_data["ids"])
        return Response({"deleted": count})
