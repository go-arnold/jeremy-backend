from dj_rest_auth.registration.serializers import RegisterSerializer as BaseRegisterSerializer
from dj_rest_auth.serializers import UserDetailsSerializer
from rest_framework import serializers

from apps.realtime.presence import is_user_online

from .models import ListenHistory, User


class RegisterSerializer(BaseRegisterSerializer):
    username = serializers.CharField(required=False, allow_blank=True)

    def validate_username(self, value):
        return value or self.validated_data.get("email", "").split("@")[0]

    def custom_signup(self, request, user):
        pass

    def get_cleaned_data(self):
        data = super().get_cleaned_data()
        data["username"] = self.validated_data.get("username", "")
        return data


class UserSerializer(UserDetailsSerializer):
    avatar_url = serializers.SerializerMethodField()
    cover_image_url = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()
    # Write-only counterparts: the frontend uploads the file to Cloudinary directly (via the
    # signed upload-signature flow, same as community media) and PATCHes the resulting
    # `secure_url` here — CloudinaryField accepts a plain URL string assignment directly and
    # derives its own delivery URL from it, no server-side file upload involved.
    avatar = serializers.URLField(write_only=True, required=False, allow_blank=True)
    cover_image = serializers.URLField(write_only=True, required=False, allow_blank=True)

    class Meta(UserDetailsSerializer.Meta):
        model = User
        fields = [
            "id",
            "email",
            "username",
            "handle",
            "bio",
            "role",
            "is_verified",
            "is_online",
            "listen_count",
            "avatar_url",
            "cover_image_url",
            "avatar",
            "cover_image",
            "created_at",
        ]
        read_only_fields = ["id", "email", "role", "is_verified", "listen_count", "created_at"]

    # Right after this serializer's own `update()` writes a plain URL string into `avatar`/
    # `cover_image`, the in-memory instance still holds that raw string (CloudinaryField only
    # normalizes it into a `CloudinaryResource` — with a `.url` property — once reloaded from
    # the DB), so `to_representation` immediately after a PATCH sees a plain `str` here, not a
    # `CloudinaryResource`. Handled defensively rather than forcing a `refresh_from_db()` on
    # every read.
    def get_cover_image_url(self, obj):
        if not obj.cover_image:
            return None
        return obj.cover_image.url if hasattr(obj.cover_image, "url") else str(obj.cover_image)

    def get_avatar_url(self, obj):
        if not obj.avatar:
            return None
        return obj.avatar.url if hasattr(obj.avatar, "url") else str(obj.avatar)

    def get_is_online(self, obj):
        """Computed live from WebSocket presence (apps.realtime.presence), not stored — true as
        long as the user has at least one active connection to any live room (chat/direct)."""
        return is_user_online(obj.id)


class UserAdminSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "handle",
            "bio",
            "role",
            "is_active",
            "is_verified",
            "is_online",
            "listen_count",
            "avatar_url",
            "created_at",
        ]
        read_only_fields = ["id", "listen_count", "created_at"]

    def get_avatar_url(self, obj):
        return obj.avatar.url if obj.avatar else None

    def get_is_online(self, obj):
        return is_user_online(obj.id)


class ListenHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ListenHistory
        fields = [
            "id",
            "content_type",
            "content_id",
            "title",
            "subtitle",
            "cover_image",
            "progress_percent",
            "listened_at",
        ]
        read_only_fields = ["listened_at"]


class ProfileTargetSerializer(serializers.Serializer):
    kind = serializers.CharField()
    id = serializers.IntegerField(allow_null=True)
    slug = serializers.CharField(allow_null=True, allow_blank=True)
    title = serializers.CharField(allow_blank=True)
    cover_url = serializers.CharField(allow_blank=True)


class SavedItemSerializer(ProfileTargetSerializer):
    saved_at = serializers.DateTimeField()


class ActivityEntrySerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["like", "comment"])
    created_at = serializers.DateTimeField()
    excerpt = serializers.CharField(required=False, allow_blank=True)
    target = ProfileTargetSerializer()


class UserBulkUpdateItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(min_value=1)
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES, required=False)
    is_active = serializers.BooleanField(required=False)
    is_verified = serializers.BooleanField(required=False)
    is_staff = serializers.BooleanField(required=False)


class UserBulkUpdateSerializer(serializers.Serializer):
    items = UserBulkUpdateItemSerializer(many=True, min_length=1, max_length=100)


class BulkUpdateResultSerializer(serializers.Serializer):
    updated = serializers.IntegerField()


class BulkDeleteResultSerializer(serializers.Serializer):
    deleted = serializers.IntegerField()


class FavoriteToggleSerializer(serializers.Serializer):
    artist_id = serializers.IntegerField(min_value=1)


class FavoriteActionResponseSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["added", "removed"])
    artist_id = serializers.IntegerField()
