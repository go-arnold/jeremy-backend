from rest_framework import serializers

from .models import MusicRelease


class ReleaseListSerializer(serializers.ModelSerializer):
    cover_url = serializers.SerializerMethodField()
    artist_name = serializers.CharField(source="artist.name", read_only=True)
    artist_slug = serializers.CharField(source="artist.slug", read_only=True)

    class Meta:
        model = MusicRelease
        fields = [
            "id", "title", "slug", "cover_url", "release_date",
            "format", "is_featured", "is_premiere",
            "artist_name", "artist_slug",
        ]

    def get_cover_url(self, obj):
        return obj.cover.url if obj.cover else None


class ReleaseDetailSerializer(serializers.ModelSerializer):
    cover_url = serializers.SerializerMethodField()
    artist_name = serializers.CharField(source="artist.name", read_only=True)

    class Meta:
        model = MusicRelease
        fields = [
            "id", "title", "slug", "cover_url", "release_date",
            "format", "is_featured", "is_premiere", "streaming_links",
            "description", "preview_url", "artist_name",
        ]

    def get_cover_url(self, obj):
        return obj.cover.url if obj.cover else None


class ReleaseWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = MusicRelease
        fields = [
            "artist", "title", "slug", "cover", "release_date", "format",
            "is_featured", "is_premiere", "streaming_links", "description", "preview_url",
        ]
        extra_kwargs = {"slug": {"required": False}}
