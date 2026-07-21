from rest_framework import serializers

from apps.engagement.services import engagement_counts
from apps.media_uploads.fields import CloudinaryUrlField, resolve_cloudinary_url
from apps.media_uploads.validation import verify_cloudinary_asset

from .models import MusicRelease


class ReleaseListSerializer(serializers.ModelSerializer):
    cover_url = serializers.SerializerMethodField()
    artist_name = serializers.CharField(source="artist.name", read_only=True)
    artist_slug = serializers.CharField(source="artist.slug", read_only=True)

    class Meta:
        model = MusicRelease
        fields = [
            "id",
            "title",
            "slug",
            "cover_url",
            "release_date",
            "format",
            "is_featured",
            "is_premiere",
            "artist_name",
            "artist_slug",
        ]

    def get_cover_url(self, obj):
        return resolve_cloudinary_url(obj.cover, "image")


class ReleaseDetailSerializer(serializers.ModelSerializer):
    cover_url = serializers.SerializerMethodField()
    artist_name = serializers.CharField(source="artist.name", read_only=True)
    like_count = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = MusicRelease
        fields = [
            "id",
            "title",
            "slug",
            "cover_url",
            "release_date",
            "format",
            "is_featured",
            "is_premiere",
            "streaming_links",
            "description",
            "preview_url",
            "artist_name",
            "like_count",
            "comment_count",
        ]

    def get_cover_url(self, obj):
        return resolve_cloudinary_url(obj.cover, "image")

    # Single-object endpoint (retrieve/featured only) — safe to compute directly here, unlike
    # ReleaseListSerializer where this would be an N+1 across every item on the page.
    def get_like_count(self, obj):
        return engagement_counts(obj)["like_count"]

    def get_comment_count(self, obj):
        return engagement_counts(obj)["comment_count"]


class ReleaseWriteSerializer(serializers.ModelSerializer):
    cover = CloudinaryUrlField(resource_type="image", required=False, allow_blank=True)

    class Meta:
        model = MusicRelease
        fields = [
            "artist",
            "title",
            "slug",
            "cover",
            "release_date",
            "format",
            "is_featured",
            "is_premiere",
            "streaming_links",
            "description",
            "preview_url",
        ]
        extra_kwargs = {"slug": {"required": False}}

    def validate_preview_url(self, value):
        if value:
            verify_cloudinary_asset(value, "video")
        return value


class ReleaseBulkUpdateItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(min_value=1)
    title = serializers.CharField(max_length=200, required=False)
    release_date = serializers.DateField(required=False)
    format = serializers.ChoiceField(choices=MusicRelease.FORMAT_CHOICES, required=False)
    is_featured = serializers.BooleanField(required=False)
    is_premiere = serializers.BooleanField(required=False)
    streaming_links = serializers.JSONField(required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    preview_url = serializers.URLField(required=False, allow_blank=True)

    def validate_preview_url(self, value):
        if value:
            verify_cloudinary_asset(value, "video")
        return value


class ReleaseBulkCreateSerializer(serializers.Serializer):
    items = ReleaseWriteSerializer(many=True, min_length=1, max_length=100)


class ReleaseBulkUpdateSerializer(serializers.Serializer):
    items = ReleaseBulkUpdateItemSerializer(many=True, min_length=1, max_length=100)
