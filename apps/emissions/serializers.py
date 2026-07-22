from rest_framework import serializers

from apps.engagement.services import engagement_counts
from apps.media_uploads.fields import CloudinaryUrlField, resolve_cloudinary_url

from .models import Emission


class EmissionListSerializer(serializers.ModelSerializer):
    cover_url = serializers.SerializerMethodField()

    class Meta:
        model = Emission
        fields = [
            "id",
            "title",
            "slug",
            "cover_url",
            "status",
            "recording_status",
            "scheduled_at",
            "duration_minutes",
            "viewer_count",
            "total_views",
        ]
        extra_kwargs = {"recording_status": {"read_only": True}}

    def get_cover_url(self, obj):
        return resolve_cloudinary_url(obj.cover, "image")


class EmissionDetailSerializer(serializers.ModelSerializer):
    cover_url = serializers.SerializerMethodField()
    host_names = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = Emission
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "cover_url",
            "stream_url",
            "playback_hls_url",
            "video_url",
            "status",
            "recording_status",
            "scheduled_at",
            "duration_minutes",
            "viewer_count",
            "total_views",
            "host_names",
            "like_count",
            "comment_count",
            "created_at",
        ]
        extra_kwargs = {"recording_status": {"read_only": True}, "video_url": {"read_only": True}}

    def get_cover_url(self, obj):
        return resolve_cloudinary_url(obj.cover, "image")

    def get_host_names(self, obj):
        return [h.name for h in obj.hosts.all()]

    # Single-object endpoint (retrieve/live only) — safe here, unlike EmissionListSerializer
    # where this would be an N+1 across every item on the page.
    def get_like_count(self, obj):
        return engagement_counts(obj)["like_count"]

    def get_comment_count(self, obj):
        return engagement_counts(obj)["comment_count"]


class EmissionWriteSerializer(serializers.ModelSerializer):
    cover = CloudinaryUrlField(resource_type="image", required=False, allow_blank=True)

    class Meta:
        model = Emission
        fields = [
            "title",
            "slug",
            "description",
            "cover",
            "stream_url",
            "status",
            "scheduled_at",
            "duration_minutes",
            "hosts",
        ]
        extra_kwargs = {"slug": {"required": False}}


class EmissionBulkUpdateItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(min_value=1)
    title = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    stream_url = serializers.URLField(required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=Emission.STATUS_CHOICES, required=False)
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True)
    duration_minutes = serializers.IntegerField(min_value=1, required=False)


class EmissionBulkCreateSerializer(serializers.Serializer):
    items = EmissionWriteSerializer(many=True, min_length=1, max_length=100)


class EmissionBulkUpdateSerializer(serializers.Serializer):
    items = EmissionBulkUpdateItemSerializer(many=True, min_length=1, max_length=100)
