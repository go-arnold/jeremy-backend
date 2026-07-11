from rest_framework import serializers

from .models import Comment


class CommentSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="author.username", read_only=True)
    handle = serializers.CharField(source="author.handle", read_only=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ["id", "username", "handle", "avatar_url", "content", "parent", "created_at"]
        read_only_fields = ["id", "username", "handle", "avatar_url", "created_at"]

    def get_avatar_url(self, obj):
        return obj.author.avatar.url if obj.author.avatar else None


class CommentCreateSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=1000)
    parent = serializers.IntegerField(required=False, allow_null=True, min_value=1)
