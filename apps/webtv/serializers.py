from rest_framework import serializers

from .models import WebTVVideo


class VideoListSerializer(serializers.ModelSerializer):
    thumbnail_url = serializers.SerializerMethodField()
    artist_names = serializers.SerializerMethodField()

    class Meta:
        model = WebTVVideo
        fields = [
            "id", "title", "slug", "thumbnail_url", "duration",
            "category", "is_premier", "is_live", "location",
            "artist_names", "view_count", "published_at",
        ]

    def get_thumbnail_url(self, obj):
        return obj.thumbnail.url if obj.thumbnail else None

    def get_artist_names(self, obj):
        return [a.name for a in obj.artists.all()]


class VideoDetailSerializer(serializers.ModelSerializer):
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = WebTVVideo
        fields = [
            "id", "title", "slug", "description", "thumbnail_url",
            "video_url", "duration", "category", "is_premier", "is_live",
            "location", "view_count", "published_at",
        ]

    def get_thumbnail_url(self, obj):
        return obj.thumbnail.url if obj.thumbnail else None


class VideoWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebTVVideo
        fields = [
            "title", "slug", "description", "thumbnail", "video_url",
            "duration", "category", "is_premier", "is_live", "location",
            "artists", "published_at",
        ]
        extra_kwargs = {"slug": {"required": False}}
