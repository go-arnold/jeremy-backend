from rest_framework import serializers

from .models import Emission


class EmissionListSerializer(serializers.ModelSerializer):
    cover_url = serializers.SerializerMethodField()

    class Meta:
        model = Emission
        fields = [
            "id", "title", "slug", "cover_url", "status",
            "scheduled_at", "duration_minutes", "viewer_count", "total_views",
        ]

    def get_cover_url(self, obj):
        return obj.cover.url if obj.cover else None


class EmissionDetailSerializer(serializers.ModelSerializer):
    cover_url = serializers.SerializerMethodField()
    host_names = serializers.SerializerMethodField()

    class Meta:
        model = Emission
        fields = [
            "id", "title", "slug", "description", "cover_url", "stream_url",
            "status", "scheduled_at", "duration_minutes",
            "viewer_count", "total_views", "host_names", "created_at",
        ]

    def get_cover_url(self, obj):
        return obj.cover.url if obj.cover else None

    def get_host_names(self, obj):
        return [h.name for h in obj.hosts.all()]


class EmissionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Emission
        fields = [
            "title", "slug", "description", "cover", "stream_url",
            "status", "scheduled_at", "duration_minutes", "hosts",
        ]
        extra_kwargs = {"slug": {"required": False}}
