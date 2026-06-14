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


class VideoBulkUpdateItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(min_value=1)
    title = serializers.CharField(max_length=300, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    video_url = serializers.URLField(required=False)
    duration = serializers.CharField(max_length=10, required=False, allow_blank=True)
    category = serializers.ChoiceField(choices=WebTVVideo.CATEGORY_CHOICES, required=False)
    is_premier = serializers.BooleanField(required=False)
    is_live = serializers.BooleanField(required=False)
    location = serializers.CharField(max_length=100, required=False, allow_blank=True)
    published_at = serializers.DateTimeField(required=False)


class VideoBulkCreateSerializer(serializers.Serializer):
    items = VideoWriteSerializer(many=True, min_length=1, max_length=100)


class VideoBulkUpdateSerializer(serializers.Serializer):
    items = VideoBulkUpdateItemSerializer(many=True, min_length=1, max_length=100)
