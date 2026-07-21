from django.core.cache import cache
from django.shortcuts import get_object_or_404
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
from .filters import ArtistFilter
from .models import Artist, ArtistPhoto, ArtistVideo, Genre, Release
from .serializers import (
    ArtistBulkCreateSerializer,
    ArtistBulkUpdateSerializer,
    ArtistDetailSerializer,
    ArtistListSerializer,
    ArtistPhotoSerializer,
    ArtistPhotoWriteSerializer,
    ArtistVideoSerializer,
    ArtistVideoWriteSerializer,
    ArtistWriteSerializer,
    GenreSerializer,
    ReleaseSerializer,
    ReleaseWriteSerializer,
)


@extend_schema(tags=["Artists"])
@extend_schema_view(
    create=extend_schema(
        examples=[
            OpenApiExample(
                "Nouvel artiste avec genres",
                value={
                    "name": "Aline Mwamba",
                    "bio": "Chanteuse et compositrice originaire de Goma.",
                    "city": "Goma",
                    "country": "Congo (DRC)",
                    "photo": "https://res.cloudinary.com/artdukivu/image/upload/v1721581234/artists/photos/aline.jpg",
                    "genres": [1, 2],
                    "is_featured": False,
                },
                request_only=True,
            )
        ]
    ),
    partial_update=extend_schema(
        examples=[OpenApiExample("Changer les genres", value={"genres": [1, 3]}, request_only=True)]
    ),
)
class ArtistViewSet(UploadThrottleMixin, EngagementActionsMixin, ModelViewSet):
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

    @extend_schema(
        methods=["POST"],
        examples=[
            OpenApiExample(
                "Nouvelle sortie",
                value={
                    "title": "Nouvel Album",
                    "cover": "https://res.cloudinary.com/artdukivu/image/upload/v1721581234/releases/covers/album.jpg",
                    "release_date": "2026-09-01",
                    "format": "album",
                    "streaming_links": {"spotify": "https://open.spotify.com/album/xyz"},
                },
                request_only=True,
            )
        ],
    )
    @action(detail=True, methods=["get", "post"])
    def releases(self, request, slug=None):
        artist = self.get_object()
        if request.method == "POST":
            ser = ReleaseWriteSerializer(data=request.data)
            ser.is_valid(raise_exception=True)
            release = services.create_release(artist, ser.validated_data)
            return Response(ReleaseSerializer(release).data, status=status.HTTP_201_CREATED)
        qs = artist.releases.select_related("artist").order_by("-release_date")
        return Response(ReleaseSerializer(qs, many=True).data)

    @extend_schema(
        methods=["PATCH"],
        examples=[
            OpenApiExample(
                "Corriger le titre", value={"title": "Nouvel Album (Édition Deluxe)"}, request_only=True
            )
        ],
    )
    @action(detail=True, methods=["patch", "delete"], url_path=r"releases/(?P<release_id>\d+)")
    def release_detail(self, request, slug=None, release_id=None):
        artist = self.get_object()
        release = get_object_or_404(Release, pk=release_id, artist=artist)
        if request.method == "DELETE":
            services.delete_release(release)
            return Response(status=status.HTTP_204_NO_CONTENT)
        ser = ReleaseWriteSerializer(release, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        updated = services.update_release(release, ser.validated_data)
        return Response(ReleaseSerializer(updated).data)

    @extend_schema(
        methods=["POST"],
        examples=[
            OpenApiExample(
                "Nouvelle vidéo",
                value={
                    "title": "Clip officiel — Nouvel Album",
                    "thumbnail": "https://res.cloudinary.com/artdukivu/image/upload/v1721581234/artists/videos/thumb.jpg",
                    "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "duration": "3:45",
                },
                request_only=True,
            )
        ],
    )
    @action(detail=True, methods=["get", "post"])
    def videos(self, request, slug=None):
        artist = self.get_object()
        if request.method == "POST":
            ser = ArtistVideoWriteSerializer(data=request.data)
            ser.is_valid(raise_exception=True)
            video = services.create_video(artist, ser.validated_data)
            return Response(ArtistVideoSerializer(video).data, status=status.HTTP_201_CREATED)
        qs = artist.videos.order_by("order", "-published_at")
        return Response(ArtistVideoSerializer(qs, many=True).data)

    @extend_schema(
        methods=["PATCH"],
        examples=[OpenApiExample("Corriger la durée", value={"duration": "4:02"}, request_only=True)],
    )
    @action(detail=True, methods=["patch", "delete"], url_path=r"videos/(?P<video_id>\d+)")
    def video_detail(self, request, slug=None, video_id=None):
        artist = self.get_object()
        video = get_object_or_404(ArtistVideo, pk=video_id, artist=artist)
        if request.method == "DELETE":
            services.delete_video(video)
            return Response(status=status.HTTP_204_NO_CONTENT)
        ser = ArtistVideoWriteSerializer(video, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        updated = services.update_video(video, ser.validated_data)
        return Response(ArtistVideoSerializer(updated).data)

    @extend_schema(
        methods=["POST"],
        examples=[
            OpenApiExample(
                "Nouvelle photo",
                value={
                    "image": "https://res.cloudinary.com/artdukivu/image/upload/v1721581234/artists/gallery/photo1.jpg",
                    "caption": "En studio, juillet 2026",
                    "order": 1,
                },
                request_only=True,
            )
        ],
    )
    @action(detail=True, methods=["get", "post"])
    def gallery(self, request, slug=None):
        artist = self.get_object()
        if request.method == "POST":
            ser = ArtistPhotoWriteSerializer(data=request.data)
            ser.is_valid(raise_exception=True)
            photo = services.create_photo(artist, ser.validated_data)
            return Response(ArtistPhotoSerializer(photo).data, status=status.HTTP_201_CREATED)
        qs = artist.gallery.order_by("order")
        return Response(ArtistPhotoSerializer(qs, many=True).data)

    @extend_schema(
        methods=["PATCH"],
        examples=[
            OpenApiExample(
                "Corriger la légende", value={"caption": "Backstage, concert de Goma"}, request_only=True
            )
        ],
    )
    @action(detail=True, methods=["patch", "delete"], url_path=r"gallery/(?P<photo_id>\d+)")
    def gallery_detail(self, request, slug=None, photo_id=None):
        artist = self.get_object()
        photo = get_object_or_404(ArtistPhoto, pk=photo_id, artist=artist)
        if request.method == "DELETE":
            services.delete_photo(photo)
            return Response(status=status.HTTP_204_NO_CONTENT)
        ser = ArtistPhotoWriteSerializer(photo, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        updated = services.update_photo(photo, ser.validated_data)
        return Response(ArtistPhotoSerializer(updated).data)

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
