from rest_framework import serializers

from .models import RadioChat, RadioProgram


class RadioProgramSerializer(serializers.ModelSerializer):
    cover_url = serializers.SerializerMethodField()
    day_name = serializers.CharField(source="get_day_of_week_display", read_only=True)

    class Meta:
        model = RadioProgram
        fields = [
            "id", "title", "slug", "description", "cover_url",
            "start_time", "end_time", "day_of_week", "day_name",
            "presenter", "status", "stream_url", "listener_count",
        ]

    def get_cover_url(self, obj):
        return obj.cover.url if obj.cover else None


class RadioProgramWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = RadioProgram
        fields = [
            "title", "slug", "description", "cover", "start_time", "end_time",
            "day_of_week", "presenter", "status", "stream_url",
        ]
        extra_kwargs = {"slug": {"required": False}}


class RadioChatSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = RadioChat
        fields = ["id", "username", "avatar_url", "message", "created_at"]
        read_only_fields = ["id", "username", "avatar_url", "created_at"]

    def get_avatar_url(self, obj):
        if hasattr(obj.user, "avatar") and obj.user.avatar:
            return obj.user.avatar.url
        return None
