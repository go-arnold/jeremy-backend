from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
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
@extend_schema_view(
    create=extend_schema(
        examples=[
            OpenApiExample(
                "Podcast autonome (sans épisode)",
                value={
                    "title": "Débat du vendredi",
                    "description": "Un podcast unique, pas encore une série.",
                    "audio_file": "https://res.cloudinary.com/artdukivu/video/upload/v1721581234/podcasts/audio/debat.mp3",
                    "category": "talk",
                },
                request_only=True,
            ),
        ]
    ),
    partial_update=extend_schema(
        examples=[
            OpenApiExample("Mettre à jour la catégorie", value={"category": "culture"}, request_only=True),
        ]
    ),
)
class PodcastSeriesViewSet(UploadThrottleMixin, ModelViewSet):
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

    @extend_schema(
        examples=[
            OpenApiExample(
                "Catégories disponibles",
                value=[{"id": "talk", "label": "Talk"}, {"id": "culture", "label": "Culture"}],
                response_only=True,
            )
        ]
    )
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
@extend_schema_view(
    create=extend_schema(
        examples=[
            OpenApiExample(
                "Épisode avec invités mixtes (artiste + libre)",
                value={
                    "series": 4,
                    "title": "Épisode 12 — La scène urbaine à Goma",
                    "description": "Discussion avec des artistes locaux.",
                    "audio_file": "https://res.cloudinary.com/artdukivu/video/upload/v1721581234/podcasts/audio/ep12.mp3",
                    "episode_number": 12,
                    "season_number": 1,
                    "guests": [
                        {"name": "Aline Mwamba", "artist_id": 12},
                        {"name": "Invité surprise"},
                    ],
                    "published_at": "2026-08-01T18:00:00Z",
                },
                request_only=True,
            ),
        ]
    ),
    partial_update=extend_schema(
        examples=[
            OpenApiExample(
                "Mettre à jour les invités",
                value={"guests": [{"name": "Nouvel invité", "artist_id": None, "user_id": 8}]},
                request_only=True,
            ),
        ]
    ),
)
class PodcastEpisodeViewSet(UploadThrottleMixin, EngagementActionsMixin, ModelViewSet):
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
        guest_artist = self.request.query_params.get("guest_artist")
        if guest_artist and guest_artist.isdigit():
            qs = qs.filter(Q(guests__contains=[{"artist_id": int(guest_artist)}]))
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
        return Response({"detail": "Nombre d'écoutes mis à jour."})

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
