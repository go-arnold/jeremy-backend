from rest_framework import serializers

from apps.media_uploads.fields import CloudinaryUrlField

from .models import RadioChat, RadioProgram


class RadioProgramSerializer(serializers.ModelSerializer):
    cover_url = serializers.SerializerMethodField()
    day_name = serializers.CharField(source="get_day_of_week_display", read_only=True)

    class Meta:
        model = RadioProgram
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "cover_url",
            "start_time",
            "end_time",
            "day_of_week",
            "day_name",
            "presenter",
            "status",
            "stream_url",
            "playback_hls_url",
            "listener_count",
        ]

    def get_cover_url(self, obj):
        return obj.cover.url if obj.cover else None


class RadioProgramWriteSerializer(serializers.ModelSerializer):
    cover = CloudinaryUrlField(resource_type="image", required=False, allow_blank=True)

    class Meta:
        model = RadioProgram
        fields = [
            "title",
            "slug",
            "description",
            "cover",
            "start_time",
            "end_time",
            "day_of_week",
            "presenter",
            "status",
            "stream_url",
        ]
        extra_kwargs = {"slug": {"required": False}}


class RadioProgramBulkUpdateItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(min_value=1)
    title = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    start_time = serializers.TimeField(required=False)
    end_time = serializers.TimeField(required=False)
    day_of_week = serializers.IntegerField(min_value=0, max_value=6, required=False)
    presenter = serializers.CharField(max_length=100, required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=RadioProgram.STATUS_CHOICES, required=False)
    stream_url = serializers.URLField(required=False, allow_blank=True)


class RadioProgramBulkCreateSerializer(serializers.Serializer):
    items = RadioProgramWriteSerializer(many=True, min_length=1, max_length=100)


class RadioProgramBulkUpdateSerializer(serializers.Serializer):
    items = RadioProgramBulkUpdateItemSerializer(many=True, min_length=1, max_length=100)


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
