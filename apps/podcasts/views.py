from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.pagination import StandardPagination
from core.permissions import IsAdminOrReadOnly

from .models import PodcastEpisode, PodcastSeries
from .serializers import (
    EpisodeDetailSerializer,
    EpisodeListSerializer,
    EpisodeWriteSerializer,
    PodcastSeriesListSerializer,
    PodcastSeriesWriteSerializer,
)
from .tasks import async_increment_play


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

    @action(detail=True, methods=["post"])
    def play(self, request, slug=None):
        episode = self.get_object()
        async_increment_play.delay(episode.pk)
        return Response({"detail": "Play count updated."})
