from rest_framework import serializers

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
        return obj.cover.url if obj.cover else None


class ReleaseDetailSerializer(serializers.ModelSerializer):
    cover_url = serializers.SerializerMethodField()
    artist_name = serializers.CharField(source="artist.name", read_only=True)

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
        ]

    def get_cover_url(self, obj):
        return obj.cover.url if obj.cover else None


class ReleaseWriteSerializer(serializers.ModelSerializer):
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


class ReleaseBulkCreateSerializer(serializers.Serializer):
    items = ReleaseWriteSerializer(many=True, min_length=1, max_length=100)


class ReleaseBulkUpdateSerializer(serializers.Serializer):
    items = ReleaseBulkUpdateItemSerializer(many=True, min_length=1, max_length=100)
