from rest_framework import serializers

from .models import Artist, ArtistPhoto, ArtistVideo, Genre, Release


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ["id", "name", "slug"]


class ReleaseSerializer(serializers.ModelSerializer):
    cover_url = serializers.SerializerMethodField()

    class Meta:
        model = Release
        fields = [
            "id", "title", "slug", "cover_url",
            "release_date", "format", "streaming_links",
            "description", "preview_url",
        ]

    def get_cover_url(self, obj):
        return obj.cover.url if obj.cover else None


class ArtistVideoSerializer(serializers.ModelSerializer):
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = ArtistVideo
        fields = ["id", "title", "thumbnail_url", "video_url", "duration", "view_count", "published_at"]

    def get_thumbnail_url(self, obj):
        return obj.thumbnail.url if obj.thumbnail else None


class ArtistPhotoSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ArtistPhoto
        fields = ["id", "image_url", "caption", "order"]

    def get_image_url(self, obj):
        return obj.image.url if obj.image else None


class ArtistListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list endpoints."""
    photo_url = serializers.SerializerMethodField()
    # genres annotated as array of names from view
    genre_names = serializers.SerializerMethodField()

    class Meta:
        model = Artist
        fields = [
            "id", "name", "slug", "city", "photo_url",
            "is_featured", "genre_names",
        ]

    def get_photo_url(self, obj):
        return obj.photo.url if obj.photo else None

    def get_genre_names(self, obj):
        # Avoid N+1 by using prefetch_related in the viewset
        return [g.name for g in obj.genres.all()]


class ArtistDetailSerializer(serializers.ModelSerializer):
    photo_url = serializers.SerializerMethodField()
    cover_url = serializers.SerializerMethodField()
    genres = GenreSerializer(many=True)
    releases = ReleaseSerializer(many=True, read_only=True)
    videos = ArtistVideoSerializer(many=True, read_only=True)
    gallery = ArtistPhotoSerializer(many=True, read_only=True)

    class Meta:
        model = Artist
        fields = [
            "id", "name", "slug", "bio", "city", "country",
            "photo_url", "cover_url", "genres", "is_featured",
            "social_links", "release_count", "video_count",
            "releases", "videos", "gallery", "created_at",
        ]

    def get_photo_url(self, obj):
        return obj.photo.url if obj.photo else None

    def get_cover_url(self, obj):
        return obj.cover_image.url if obj.cover_image else None


class ArtistWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artist
        fields = [
            "name", "slug", "bio", "city", "country",
            "photo", "cover_image", "genres", "is_featured", "social_links",
        ]
        extra_kwargs = {"slug": {"required": False}}


class ArtistBulkUpdateItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(min_value=1)
    name = serializers.CharField(max_length=200, required=False)
    bio = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    country = serializers.CharField(max_length=100, required=False)
    is_featured = serializers.BooleanField(required=False)
    social_links = serializers.JSONField(required=False)


class ArtistBulkCreateSerializer(serializers.Serializer):
    items = ArtistWriteSerializer(many=True, min_length=1, max_length=100)


class ArtistBulkUpdateSerializer(serializers.Serializer):
    items = ArtistBulkUpdateItemSerializer(many=True, min_length=1, max_length=100)
