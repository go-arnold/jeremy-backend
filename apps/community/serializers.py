from rest_framework import serializers

from .models import Challenge, CommunityPost, Poll, PollOption


class CommunityPostSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.username", read_only=True)
    author_avatar = serializers.SerializerMethodField()

    class Meta:
        model = CommunityPost
        fields = [
            "id", "author_name", "author_avatar", "content", "media",
            "post_type", "like_count", "comment_count", "created_at",
        ]
        read_only_fields = ["id", "author_name", "like_count", "comment_count", "created_at"]

    def get_author_avatar(self, obj):
        if hasattr(obj.author, "avatar") and obj.author.avatar:
            return obj.author.avatar.url
        return None


class CommunityPostWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommunityPost
        fields = ["content", "media", "post_type"]

    def validate_media(self, value):
        if len(value) > 10:
            raise serializers.ValidationError("Maximum 10 media items per post.")
        return value


class ChallengeSerializer(serializers.ModelSerializer):
    cover_url = serializers.SerializerMethodField()

    class Meta:
        model = Challenge
        fields = [
            "id", "title", "slug", "description", "cover_url",
            "prize", "deadline", "participant_count", "is_active",
        ]

    def get_cover_url(self, obj):
        return obj.cover.url if obj.cover else None


class PollOptionSerializer(serializers.ModelSerializer):
    percentage = serializers.ReadOnlyField()

    class Meta:
        model = PollOption
        fields = ["id", "text", "vote_count", "percentage"]


class PollSerializer(serializers.ModelSerializer):
    options = PollOptionSerializer(many=True, read_only=True)

    class Meta:
        model = Poll
        fields = ["id", "question", "vote_count", "options", "expires_at", "is_active", "created_at"]
