from dj_rest_auth.registration.serializers import RegisterSerializer as BaseRegisterSerializer
from dj_rest_auth.serializers import UserDetailsSerializer
from rest_framework import serializers

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

    class Meta(UserDetailsSerializer.Meta):
        model = User
        fields = [
            "id", "email", "username", "handle", "bio",
            "role", "is_verified", "is_online",
            "listen_count", "avatar_url", "created_at",
        ]
        read_only_fields = ["id", "email", "role", "is_verified", "listen_count", "created_at"]

    def get_avatar_url(self, obj):
        if obj.avatar:
            return obj.avatar.url
        return None


class UserPublicSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "handle", "bio", "is_online", "avatar_url"]

    def get_avatar_url(self, obj):
        return obj.avatar.url if obj.avatar else None


class UserAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id", "email", "username", "handle", "bio", "role",
            "is_active", "is_verified", "listen_count", "created_at",
        ]
        read_only_fields = ["id", "listen_count", "created_at"]


class ListenHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ListenHistory
        fields = [
            "id", "content_type", "content_id", "title",
            "subtitle", "cover_image", "progress_percent", "listened_at",
        ]
        read_only_fields = ["listened_at"]
