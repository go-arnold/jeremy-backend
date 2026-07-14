from rest_framework import serializers

from apps.engagement.services import engagement_counts
from apps.media_uploads.validation import validate_media_items

from .models import Challenge, CommunityPost, Poll, PollOption


class CommunityPostSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.username", read_only=True)
    author_avatar = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = CommunityPost
        fields = [
            "id",
            "author_name",
            "author_avatar",
            "title",
            "content",
            "media",
            "post_type",
            "like_count",
            "comment_count",
            "created_at",
        ]
        read_only_fields = ["id", "author_name", "like_count", "comment_count", "created_at"]

    def get_author_avatar(self, obj):
        if hasattr(obj.author, "avatar") and obj.author.avatar:
            return obj.author.avatar.url
        return None

    def get_comment_count(self, obj):
        # Present whenever `obj` came from CommunityPostViewSet.get_queryset() (list/retrieve),
        # which annotates it in a single query. Falls back to the 4-query helper only for
        # instances built outside that queryset (e.g. the fresh object returned by
        # submit_talent), where the annotation doesn't exist yet.
        annotated = getattr(obj, "live_comment_count", None)
        if annotated is not None:
            return annotated
        return engagement_counts(obj)["comment_count"]


class CommunityPostWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommunityPost
        fields = ["content", "media", "post_type"]

    def validate_media(self, value):
        if len(value) > 10:
            raise serializers.ValidationError("Maximum 10 médias par publication.")
        validate_media_items(value)
        return value


class TalentSubmissionSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    media = serializers.ListField(child=serializers.JSONField(), min_length=1, max_length=10)

    def validate_media(self, value):
        allowed = {"song", "video", "image"}
        for item in value:
            if not isinstance(item, dict) or item.get("type") not in allowed:
                raise serializers.ValidationError(
                    "Chaque média doit être une image, une chanson ou une vidéo "
                    "(type: 'image' | 'song' | 'video')."
                )
        validate_media_items(value)
        return value


class ChallengeSerializer(serializers.ModelSerializer):
    cover_url = serializers.SerializerMethodField()

    class Meta:
        model = Challenge
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "cover_url",
            "prize",
            "deadline",
            "participant_count",
            "is_active",
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


class ChallengeWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Challenge
        fields = ["title", "slug", "description", "cover", "prize", "deadline", "is_active"]
        extra_kwargs = {"slug": {"required": False}}


class ChallengeBulkUpdateItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(min_value=1)
    title = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    prize = serializers.CharField(max_length=100, required=False, allow_blank=True)
    deadline = serializers.DateTimeField(required=False)
    is_active = serializers.BooleanField(required=False)


class ChallengeBulkCreateSerializer(serializers.Serializer):
    items = ChallengeWriteSerializer(many=True, min_length=1, max_length=100)


class ChallengeBulkUpdateSerializer(serializers.Serializer):
    items = ChallengeBulkUpdateItemSerializer(many=True, min_length=1, max_length=100)


class _PollOptionInputSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=200)


class PollWriteSerializer(serializers.ModelSerializer):
    options = _PollOptionInputSerializer(many=True, write_only=True, required=False)

    class Meta:
        model = Poll
        fields = ["question", "expires_at", "is_active", "options"]

    def validate_options(self, value):
        if len(value) < 2:
            raise serializers.ValidationError("Un sondage doit avoir au moins 2 options.")
        if len(value) > 20:
            raise serializers.ValidationError("Un sondage ne peut pas avoir plus de 20 options.")
        return value
