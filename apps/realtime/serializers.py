from rest_framework import serializers

from .models import LiveChatMessage


class LiveChatMessageSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="author.username", read_only=True)
    handle = serializers.CharField(source="author.handle", read_only=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = LiveChatMessage
        fields = ["id", "username", "handle", "avatar_url", "message", "created_at"]
        read_only_fields = ["id", "username", "handle", "avatar_url", "created_at"]

    def get_avatar_url(self, obj):
        return obj.author.avatar.url if obj.author.avatar else None
