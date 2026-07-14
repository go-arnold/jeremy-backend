from rest_framework import serializers

from . import services
from .models import Badge, ConsumptionLog, UserBadge


class BadgeSerializer(serializers.ModelSerializer):
    icon_url = serializers.SerializerMethodField()

    class Meta:
        model = Badge
        fields = ["id", "slug", "name", "description", "icon_url", "threshold_seconds", "order"]

    def get_icon_url(self, obj):
        return obj.icon.url if obj.icon else None


class UserBadgeSerializer(serializers.ModelSerializer):
    badge = BadgeSerializer(read_only=True)

    class Meta:
        model = UserBadge
        fields = ["badge", "earned_at"]


class ConsumptionRecordSerializer(serializers.Serializer):
    content_type = serializers.ChoiceField(choices=ConsumptionLog.CONTENT_TYPE_CHOICES)
    object_id = serializers.IntegerField(min_value=1)
    seconds = serializers.IntegerField(min_value=1, max_value=3600)
    title = serializers.CharField(max_length=300, required=False, allow_blank=True)
    cover_url = serializers.URLField(required=False, allow_blank=True)

    def validate(self, attrs):
        if not services.content_object_exists(attrs["content_type"], attrs["object_id"]):
            raise serializers.ValidationError({"object_id": "Aucun contenu correspondant trouvé."})
        return attrs


class MediaRankingItemSerializer(serializers.Serializer):
    content_type = serializers.CharField()
    object_id = serializers.IntegerField()
    title = serializers.CharField()
    cover_url = serializers.CharField()
    total_seconds = serializers.IntegerField()
