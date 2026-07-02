from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.pagination import StandardPagination
from core.permissions import IsAdminOrReadOnly
from core.serializers import BulkDeleteSerializer

from . import services
from .models import MusicRelease
from .serializers import (
    ReleaseBulkCreateSerializer,
    ReleaseBulkUpdateSerializer,
    ReleaseDetailSerializer,
    ReleaseListSerializer,
    ReleaseWriteSerializer,
)


@extend_schema(tags=["Releases"])
class ReleaseViewSet(ModelViewSet):
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = StandardPagination
    search_fields = ["title", "artist__name"]
    ordering_fields = ["release_date", "created_at"]
    lookup_field = "slug"

    def get_queryset(self):
        qs = MusicRelease.objects.select_related("artist")
        release_format = self.request.query_params.get("format")
        if release_format:
            qs = qs.filter(format=release_format)
        artist = self.request.query_params.get("artist")
        if artist:
            qs = qs.filter(artist__slug=artist)
        return qs.order_by("-release_date")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ReleaseWriteSerializer
        if self.action == "retrieve":
            return ReleaseDetailSerializer
        return ReleaseListSerializer

    def perform_create(self, serializer):
        serializer.instance = services.create_release(dict(serializer.validated_data))

    def perform_update(self, serializer):
        serializer.instance = services.update_release(serializer.instance, dict(serializer.validated_data))

    def perform_destroy(self, instance):
        services.delete_release(instance)

    @method_decorator(cache_page(60 * 30))
    @action(detail=False, methods=["get"])
    def featured(self, request):
        release = MusicRelease.objects.filter(is_featured=True).select_related("artist").first()
        if not release:
            return Response({"detail": "No featured release"}, status=status.HTTP_404_NOT_FOUND)
        return Response(ReleaseDetailSerializer(release).data)

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def bulk_create(self, request):
        ser = ReleaseBulkCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        created = services.bulk_create_releases(ser.validated_data["items"])
        return Response(
            {"created": len(created), "items": ReleaseListSerializer(created, many=True).data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def bulk_update(self, request):
        ser = ReleaseBulkUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        count = services.bulk_update_releases(ser.validated_data["items"])
        return Response({"updated": count})

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def bulk_delete(self, request):
        ser = BulkDeleteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        count = services.bulk_delete_releases(ser.validated_data["ids"])
        return Response({"deleted": count})

    @method_decorator(cache_page(60 * 60))
    @action(detail=False, methods=["get"])
    def calendar(self, request):
        from datetime import timedelta

        from django.utils import timezone

        today = timezone.now().date()
        end = today + timedelta(days=60)
        releases = (
            MusicRelease.objects.filter(release_date__gte=today, release_date__lte=end)
            .select_related("artist")
            .order_by("release_date")
        )
        return Response(ReleaseListSerializer(releases, many=True).data)
