from rest_framework import serializers

from apps.engagement.services import engagement_counts
from apps.media_uploads.fields import CloudinaryUrlField, resolve_cloudinary_url
from apps.media_uploads.validation import verify_cloudinary_asset

from .models import WebTVVideo


class VideoListSerializer(serializers.ModelSerializer):
    thumbnail_url = serializers.SerializerMethodField()
    artist_names = serializers.SerializerMethodField()

    class Meta:
        model = WebTVVideo
        fields = [
            "id",
            "title",
            "slug",
            "thumbnail_url",
            "duration",
            "category",
            "is_premier",
            "is_live",
            "broadcast_mode",
            "recording_status",
            "location",
            "artist_names",
            "view_count",
            "published_at",
        ]
        extra_kwargs = {"recording_status": {"read_only": True}}

    def get_thumbnail_url(self, obj):
        return resolve_cloudinary_url(obj.thumbnail, "image")

    def get_artist_names(self, obj):
        return [a.name for a in obj.artists.all()]


class VideoDetailSerializer(serializers.ModelSerializer):
    thumbnail_url = serializers.SerializerMethodField()
    artist_names = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = WebTVVideo
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "thumbnail_url",
            "video_url",
            "playback_hls_url",
            "duration",
            "category",
            "is_premier",
            "is_live",
            "broadcast_mode",
            "recording_status",
            "location",
            "artist_names",
            "view_count",
            "like_count",
            "comment_count",
            "published_at",
        ]
        extra_kwargs = {"recording_status": {"read_only": True}}

    def get_thumbnail_url(self, obj):
        return resolve_cloudinary_url(obj.thumbnail, "image")

    def get_artist_names(self, obj):
        return [a.name for a in obj.artists.all()]

    # Single-object endpoint (retrieve only) — safe to compute directly here, unlike a list
    # serializer where this would be an N+1 (see CommunityPostSerializer.get_comment_count for
    # the annotated pattern used there instead). Cached on `context` so the two fields share one
    # `engagement_counts()` call instead of running its 4 COUNT queries twice.
    def _counts(self, obj):
        cache = self.context.setdefault("_engagement_counts_cache", {})
        if obj.pk not in cache:
            cache[obj.pk] = engagement_counts(obj)
        return cache[obj.pk]

    def get_like_count(self, obj):
        return self._counts(obj)["like_count"]

    def get_comment_count(self, obj):
        return self._counts(obj)["comment_count"]


class VideoWriteSerializer(serializers.ModelSerializer):
    thumbnail = CloudinaryUrlField(resource_type="image", required=False, allow_blank=True)
    video_url = serializers.URLField(max_length=500, required=False, allow_blank=True)

    class Meta:
        model = WebTVVideo
        fields = [
            "title",
            "slug",
            "description",
            "thumbnail",
            "video_url",
            "duration",
            "category",
            "is_premier",
            "is_live",
            "broadcast_mode",
            "location",
            "artists",
            "published_at",
        ]
        extra_kwargs = {"slug": {"required": False}}

    def validate(self, attrs):
        # A "camera" broadcast has no file of its own (the live feed itself is what plays, via
        # playback_hls_url) — only "playout" (a pre-recorded file/URL) requires video_url.
        mode = attrs.get("broadcast_mode", getattr(self.instance, "broadcast_mode", WebTVVideo.MODE_PLAYOUT))
        if mode == WebTVVideo.MODE_PLAYOUT and not attrs.get(
            "video_url", getattr(self.instance, "video_url", "")
        ):
            raise serializers.ValidationError({"video_url": "Requis pour une vidéo en mode playout."})
        return attrs

    def validate_video_url(self, value):
        if value:
            verify_cloudinary_asset(value, "video")
        return value


class VideoBulkUpdateItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(min_value=1)
    title = serializers.CharField(max_length=300, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    video_url = serializers.URLField(max_length=500, required=False, allow_blank=True)
    duration = serializers.CharField(max_length=10, required=False, allow_blank=True)
    category = serializers.ChoiceField(choices=WebTVVideo.CATEGORY_CHOICES, required=False)
    is_premier = serializers.BooleanField(required=False)
    is_live = serializers.BooleanField(required=False)
    broadcast_mode = serializers.ChoiceField(choices=WebTVVideo.BROADCAST_MODE_CHOICES, required=False)
    location = serializers.CharField(max_length=100, required=False, allow_blank=True)
    published_at = serializers.DateTimeField(required=False)

    def validate_video_url(self, value):
        if value:
            verify_cloudinary_asset(value, "video")
        return value


class VideoBulkCreateSerializer(serializers.Serializer):
    items = VideoWriteSerializer(many=True, min_length=1, max_length=100)


class VideoBulkUpdateSerializer(serializers.Serializer):
    items = VideoBulkUpdateItemSerializer(many=True, min_length=1, max_length=100)
