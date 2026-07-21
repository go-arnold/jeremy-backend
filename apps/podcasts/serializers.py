from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.artists.models import Artist
from apps.engagement.services import engagement_counts
from apps.media_uploads.fields import CloudinaryUrlField, resolve_cloudinary_url
from apps.media_uploads.validation import verify_cloudinary_asset

from .models import PodcastEpisode, PodcastSeries

User = get_user_model()


class GuestSerializer(serializers.Serializer):
    """A podcast guest: always has a display `name` ("jina") regardless of whether they're
    linked to an existing Artist, an existing User, or neither (pure freeform mention)."""

    name = serializers.CharField(max_length=150)
    artist_id = serializers.PrimaryKeyRelatedField(
        source="artist", queryset=Artist.objects.all(), required=False, allow_null=True
    )
    user_id = serializers.PrimaryKeyRelatedField(
        source="user", queryset=User.objects.all(), required=False, allow_null=True
    )

    def validate(self, attrs):
        if attrs.get("artist") and attrs.get("user"):
            raise serializers.ValidationError(
                "Un invité est soit un artiste, soit un utilisateur, pas les deux."
            )
        return attrs

    def to_internal_value(self, data):
        attrs = super().to_internal_value(data)
        artist = attrs.pop("artist", None)
        user = attrs.pop("user", None)
        return {
            "name": attrs["name"],
            "artist_id": artist.pk if artist else None,
            "user_id": user.pk if user else None,
        }

    def to_representation(self, instance):
        # `guests` was an unvalidated free-form JSONField before this serializer existed, so
        # rows written before this change can hold a bare string (or anything else) instead of
        # the {name, artist_id, user_id} dict shape `to_internal_value` now produces — the
        # frontend's own parser already defends against exactly this. Without this fallback,
        # any pre-existing episode with a plain-string guest 500s the whole list/detail endpoint.
        if isinstance(instance, str):
            return {"name": instance, "artist_id": None, "user_id": None}
        if not isinstance(instance, dict):
            return {"name": "", "artist_id": None, "user_id": None}
        return {
            "name": instance.get("name", ""),
            "artist_id": instance.get("artist_id"),
            "user_id": instance.get("user_id"),
        }


class PodcastSeriesListSerializer(serializers.ModelSerializer):
    cover_url = serializers.SerializerMethodField()
    audio_url = serializers.SerializerMethodField()

    class Meta:
        model = PodcastSeries
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "cover_url",
            "audio_url",
            "duration",
            "category",
            "is_series",
            "is_featured",
            "episode_count",
        ]

    def get_cover_url(self, obj):
        return resolve_cloudinary_url(obj.cover, "image")

    def get_audio_url(self, obj):
        # audio_file's actual Cloudinary asset lives under resource_type "video" (Cloudinary's
        # own convention for audio — see media_uploads.services UPLOAD_CONTEXTS["podcast_audio"]),
        # not the CloudinaryField's own declared "raw" (admin-upload-widget metadata only).
        resolved = resolve_cloudinary_url(obj.audio_file, "video")
        return resolved or (obj.audio_url or None)


class EpisodeListSerializer(serializers.ModelSerializer):
    cover_url = serializers.SerializerMethodField()
    # Avoids an extra per-episode GET /podcasts/episodes/{slug}/ just to get a playable URL
    # (BACKEND-GAPS-COMPLET.md's "la liste ne renvoie pas audio_url" N+1 note).
    audio_url = serializers.SerializerMethodField()
    series_title = serializers.CharField(source="series.title", read_only=True)
    series_slug = serializers.CharField(source="series.slug", read_only=True)
    guests = GuestSerializer(many=True, read_only=True)

    class Meta:
        model = PodcastEpisode
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "cover_url",
            "audio_url",
            "duration",
            "episode_number",
            "season_number",
            "play_count",
            "is_featured",
            "published_at",
            "series_title",
            "series_slug",
            "guests",
        ]

    def get_cover_url(self, obj):
        return resolve_cloudinary_url(obj.cover, "image")

    def get_audio_url(self, obj):
        # audio_file's actual Cloudinary asset lives under resource_type "video" (Cloudinary's
        # own convention for audio — see media_uploads.services UPLOAD_CONTEXTS["podcast_audio"]),
        # not the CloudinaryField's own declared "raw" (admin-upload-widget metadata only).
        resolved = resolve_cloudinary_url(obj.audio_file, "video")
        return resolved or (obj.audio_url or None)


class EpisodeDetailSerializer(serializers.ModelSerializer):
    cover_url = serializers.SerializerMethodField()
    audio_url = serializers.SerializerMethodField()
    series = PodcastSeriesListSerializer(read_only=True)
    guests = GuestSerializer(many=True, read_only=True)
    like_count = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = PodcastEpisode
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "cover_url",
            "audio_url",
            "duration",
            "episode_number",
            "season_number",
            "guests",
            "transcript",
            "play_count",
            "is_featured",
            "published_at",
            "series",
            "like_count",
            "comment_count",
        ]

    def get_cover_url(self, obj):
        return resolve_cloudinary_url(obj.cover, "image")

    # Single-object endpoint (retrieve only) — see WebTV's VideoDetailSerializer for the same
    # pattern/rationale (cached per-request so both fields share one engagement_counts() call).
    def _counts(self, obj):
        cache = self.context.setdefault("_engagement_counts_cache", {})
        if obj.pk not in cache:
            cache[obj.pk] = engagement_counts(obj)
        return cache[obj.pk]

    def get_like_count(self, obj):
        return self._counts(obj)["like_count"]

    def get_comment_count(self, obj):
        return self._counts(obj)["comment_count"]

    def get_audio_url(self, obj):
        # audio_file's actual Cloudinary asset lives under resource_type "video" (Cloudinary's
        # own convention for audio — see media_uploads.services UPLOAD_CONTEXTS["podcast_audio"]),
        # not the CloudinaryField's own declared "raw" (admin-upload-widget metadata only).
        resolved = resolve_cloudinary_url(obj.audio_file, "video")
        return resolved or (obj.audio_url or None)


class EpisodeWriteSerializer(serializers.ModelSerializer):
    cover = CloudinaryUrlField(resource_type="image", required=False, allow_blank=True)
    audio_file = CloudinaryUrlField(resource_type="video", required=False, allow_blank=True)
    guests = GuestSerializer(many=True, required=False)

    class Meta:
        model = PodcastEpisode
        fields = [
            "series",
            "title",
            "slug",
            "description",
            "cover",
            "audio_file",
            "audio_url",
            "duration",
            "episode_number",
            "season_number",
            "guests",
            "transcript",
            "is_featured",
            "published_at",
        ]
        extra_kwargs = {"slug": {"required": False}}

    def validate_audio_url(self, value):
        if value:
            verify_cloudinary_asset(value, "video")
        return value


class PodcastSeriesWriteSerializer(serializers.ModelSerializer):
    cover = CloudinaryUrlField(resource_type="image", required=False, allow_blank=True)
    audio_file = CloudinaryUrlField(resource_type="video", required=False, allow_blank=True)

    class Meta:
        model = PodcastSeries
        fields = [
            "title",
            "slug",
            "description",
            "cover",
            "audio_file",
            "audio_url",
            "duration",
            "category",
            "is_featured",
        ]
        extra_kwargs = {"slug": {"required": False}}

    def validate_audio_url(self, value):
        if value:
            verify_cloudinary_asset(value, "video")
        return value


class SeriesBulkUpdateItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(min_value=1)
    title = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    category = serializers.ChoiceField(choices=PodcastSeries.CATEGORY_CHOICES, required=False)
    is_featured = serializers.BooleanField(required=False)


class SeriesBulkCreateSerializer(serializers.Serializer):
    items = PodcastSeriesWriteSerializer(many=True, min_length=1, max_length=100)


class SeriesBulkUpdateSerializer(serializers.Serializer):
    items = SeriesBulkUpdateItemSerializer(many=True, min_length=1, max_length=100)


class EpisodeBulkUpdateItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(min_value=1)
    title = serializers.CharField(max_length=300, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    duration = serializers.CharField(max_length=10, required=False, allow_blank=True)
    episode_number = serializers.IntegerField(min_value=1, required=False)
    season_number = serializers.IntegerField(min_value=1, required=False)
    guests = GuestSerializer(many=True, required=False)
    is_featured = serializers.BooleanField(required=False)
    published_at = serializers.DateTimeField(required=False)


class EpisodeBulkCreateSerializer(serializers.Serializer):
    items = EpisodeWriteSerializer(many=True, min_length=1, max_length=100)


class EpisodeBulkUpdateSerializer(serializers.Serializer):
    items = EpisodeBulkUpdateItemSerializer(many=True, min_length=1, max_length=100)
