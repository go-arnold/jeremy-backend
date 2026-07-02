from django.core.cache import cache
from django.shortcuts import get_object_or_404
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
from .filters import ArtistFilter
from .models import Artist, Genre
from .serializers import (
    ArtistBulkCreateSerializer,
    ArtistBulkUpdateSerializer,
    ArtistDetailSerializer,
    ArtistListSerializer,
    ArtistPhotoSerializer,
    ArtistVideoSerializer,
    ArtistWriteSerializer,
    GenreSerializer,
    ReleaseSerializer,
)


@extend_schema(tags=["Artists"])
class ArtistViewSet(ModelViewSet):
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = StandardPagination
    filterset_class = ArtistFilter
    search_fields = ["name", "city", "bio"]
    ordering_fields = ["name", "created_at"]
    lookup_field = "slug"

    def get_queryset(self):
        return (
            Artist.objects.prefetch_related("genres")
            .only("id", "name", "slug", "city", "photo", "is_featured", "created_at")
            .order_by("name")
        )

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ArtistWriteSerializer
        if self.action == "retrieve":
            return ArtistDetailSerializer
        return ArtistListSerializer

    def retrieve(self, request, *args, **kwargs):
        slug = kwargs.get("slug")
        cache_key = f"artists:detail:{slug}"
        data = cache.get(cache_key)
        if data is None:
            # IsAdminOrReadOnly grants GET unconditionally and has no
            # has_object_permission override, so get_object() would only add
            # a redundant permission-check query here — go straight to the
            # prefetching query and 404 if the slug doesn't exist.
            qs = Artist.objects.prefetch_related("genres", "releases", "videos", "gallery")
            instance = get_object_or_404(qs, slug=slug)
            data = ArtistDetailSerializer(instance).data
            cache.set(cache_key, data, 60 * 15)
        return Response(data)

    def perform_create(self, serializer):
        genres = serializer.validated_data.pop("genres", [])
        artist = services.create_artist(serializer.validated_data, genres)
        serializer.instance = artist

    def perform_update(self, serializer):
        genres = serializer.validated_data.pop("genres", None)
        services.update_artist(serializer.instance, serializer.validated_data, genres)

    @method_decorator(cache_page(60 * 15))
    @action(detail=False, methods=["get"])
    def genres(self, request):
        genres = Genre.objects.all()
        return Response(GenreSerializer(genres, many=True).data)

    @action(detail=True, methods=["get"])
    def releases(self, request, slug=None):
        artist = self.get_object()
        qs = artist.releases.select_related("artist").order_by("-release_date")
        return Response(ReleaseSerializer(qs, many=True).data)

    @action(detail=True, methods=["get"])
    def videos(self, request, slug=None):
        artist = self.get_object()
        qs = artist.videos.order_by("order", "-published_at")
        return Response(ArtistVideoSerializer(qs, many=True).data)

    @action(detail=True, methods=["get"])
    def gallery(self, request, slug=None):
        artist = self.get_object()
        qs = artist.gallery.order_by("order")
        return Response(ArtistPhotoSerializer(qs, many=True).data)

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def bulk_create(self, request):
        ser = ArtistBulkCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        created = services.bulk_create_artists(ser.validated_data["items"])
        return Response(
            {"created": len(created), "items": ArtistListSerializer(created, many=True).data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def bulk_update(self, request):
        ser = ArtistBulkUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        count = services.bulk_update_artists(ser.validated_data["items"])
        return Response({"updated": count})

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def bulk_delete(self, request):
        ser = BulkDeleteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        count = services.bulk_delete_artists(ser.validated_data["ids"])
        return Response({"deleted": count})
