from rest_framework import serializers

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
            "scheduled_at",
            "duration_minutes",
            "viewer_count",
            "total_views",
        ]

    def get_cover_url(self, obj):
        return obj.cover.url if obj.cover else None


class EmissionDetailSerializer(serializers.ModelSerializer):
    cover_url = serializers.SerializerMethodField()
    host_names = serializers.SerializerMethodField()

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
            "status",
            "scheduled_at",
            "duration_minutes",
            "viewer_count",
            "total_views",
            "host_names",
            "created_at",
        ]

    def get_cover_url(self, obj):
        return obj.cover.url if obj.cover else None

    def get_host_names(self, obj):
        return [h.name for h in obj.hosts.all()]


class EmissionWriteSerializer(serializers.ModelSerializer):
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
