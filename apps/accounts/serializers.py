from dj_rest_auth.registration.serializers import RegisterSerializer as BaseRegisterSerializer
from dj_rest_auth.serializers import UserDetailsSerializer
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.media_uploads.fields import CloudinaryUrlField, resolve_cloudinary_url
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
    # `secure_url` here. `CloudinaryUrlField` verifies it's a real asset on our own account and
    # reduces it to a bare public_id before storage — a plain `URLField` used to accept (and
    # store) any string verbatim, including malformed/truncated pastes or http:// URLs, which
    # Cloudinary's SDK then echoed straight back to clients unmodified.
    avatar = CloudinaryUrlField(resource_type="image", write_only=True, required=False, allow_blank=True)
    cover_image = CloudinaryUrlField(resource_type="image", write_only=True, required=False, allow_blank=True)

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

    def get_cover_image_url(self, obj):
        return resolve_cloudinary_url(obj.cover_image, "image")

    def get_avatar_url(self, obj):
        return resolve_cloudinary_url(obj.avatar, "image")

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
        return resolve_cloudinary_url(obj.avatar, "image")

    def get_is_online(self, obj):
        return is_user_online(obj.id)


class UserAdminCreateSerializer(serializers.ModelSerializer):
    # write-only, deliberately separate from UserAdminSerializer (read shape) — admin creation
    # skips the self-signup email-verification flow entirely (RegisterSerializer/dj-rest-auth is
    # for that), an admin sets role/is_active directly instead.
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["email", "username", "password", "handle", "bio", "role", "is_active", "is_verified"]
        extra_kwargs = {
            "is_active": {"required": False},
            "is_verified": {"required": False},
            "handle": {"required": False},
            "bio": {"required": False},
        }

    def validate_password(self, value):
        validate_password(value)
        return value


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
