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
from .models import PodcastEpisode, PodcastSeries
from .serializers import (
    EpisodeBulkCreateSerializer,
    EpisodeBulkUpdateSerializer,
    EpisodeDetailSerializer,
    EpisodeListSerializer,
    EpisodeWriteSerializer,
    PodcastSeriesListSerializer,
    PodcastSeriesWriteSerializer,
    SeriesBulkCreateSerializer,
    SeriesBulkUpdateSerializer,
)
from .tasks import async_increment_play


@extend_schema(tags=["Podcasts"])
class PodcastSeriesViewSet(ModelViewSet):
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = StandardPagination
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "episode_count"]
    lookup_field = "slug"

    def get_queryset(self):
        qs = PodcastSeries.objects.all()
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)
        is_featured = self.request.query_params.get("is_featured")
        if is_featured:
            qs = qs.filter(is_featured=is_featured.lower() == "true")
        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return PodcastSeriesWriteSerializer
        return PodcastSeriesListSerializer

    def perform_create(self, serializer):
        serializer.instance = services.create_series(dict(serializer.validated_data))

    def perform_update(self, serializer):
        serializer.instance = services.update_series(serializer.instance, dict(serializer.validated_data))

    def perform_destroy(self, instance):
        services.delete_series(instance)

    @method_decorator(cache_page(60 * 15))
    @action(detail=False, methods=["get"])
    def categories(self, request):
        choices = [{"id": k, "label": v} for k, v in PodcastSeries.CATEGORY_CHOICES]
        return Response(choices)

    @action(detail=True, methods=["get"])
    def episodes(self, request, slug=None):
        series = self.get_object()
        qs = series.episodes.order_by("-published_at")
        page = self.paginate_queryset(qs)
        return self.get_paginated_response(EpisodeListSerializer(page, many=True).data)

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def bulk_create(self, request):
        ser = SeriesBulkCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        created = services.bulk_create_series(ser.validated_data["items"])
        return Response(
            {"created": len(created), "items": PodcastSeriesListSerializer(created, many=True).data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def bulk_update(self, request):
        ser = SeriesBulkUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        count = services.bulk_update_series(ser.validated_data["items"])
        return Response({"updated": count})

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def bulk_delete(self, request):
        ser = BulkDeleteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        count = services.bulk_delete_series(ser.validated_data["ids"])
        return Response({"deleted": count})


@extend_schema(tags=["Podcasts"])
class PodcastEpisodeViewSet(ModelViewSet):
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = StandardPagination
    search_fields = ["title", "description"]
    lookup_field = "slug"

    def get_queryset(self):
        qs = PodcastEpisode.objects.select_related("series")
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(series__category=category)
        series_slug = self.request.query_params.get("series")
        if series_slug:
            qs = qs.filter(series__slug=series_slug)
        is_featured = self.request.query_params.get("is_featured")
        if is_featured:
            qs = qs.filter(is_featured=is_featured.lower() == "true")
        return qs.order_by("-published_at")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return EpisodeWriteSerializer
        if self.action == "retrieve":
            return EpisodeDetailSerializer
        return EpisodeListSerializer

    def perform_create(self, serializer):
        serializer.instance = services.create_episode(dict(serializer.validated_data))

    def perform_update(self, serializer):
        serializer.instance = services.update_episode(serializer.instance, dict(serializer.validated_data))

    def perform_destroy(self, instance):
        services.delete_episode(instance)

    @action(detail=True, methods=["post"])
    def play(self, request, slug=None):
        episode = self.get_object()
        async_increment_play.delay(episode.pk)
        return Response({"detail": "Play count updated."})

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def bulk_create(self, request):
        ser = EpisodeBulkCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        created = services.bulk_create_episodes(ser.validated_data["items"])
        return Response(
            {"created": len(created), "items": EpisodeListSerializer(created, many=True).data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def bulk_update(self, request):
        ser = EpisodeBulkUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        count = services.bulk_update_episodes(ser.validated_data["items"])
        return Response({"updated": count})

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def bulk_delete(self, request):
        ser = BulkDeleteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        count = services.bulk_delete_episodes(ser.validated_data["ids"])
        return Response({"deleted": count})
