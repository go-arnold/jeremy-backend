from rest_framework import serializers

from apps.media_uploads.validation import verify_cloudinary_asset

from .models import PodcastEpisode, PodcastSeries


class PodcastSeriesListSerializer(serializers.ModelSerializer):
    cover_url = serializers.SerializerMethodField()

    class Meta:
        model = PodcastSeries
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "cover_url",
            "category",
            "is_featured",
            "episode_count",
        ]

    def get_cover_url(self, obj):
        return obj.cover.url if obj.cover else None


class EpisodeListSerializer(serializers.ModelSerializer):
    cover_url = serializers.SerializerMethodField()
    series_title = serializers.CharField(source="series.title", read_only=True)
    series_slug = serializers.CharField(source="series.slug", read_only=True)

    class Meta:
        model = PodcastEpisode
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "cover_url",
            "duration",
            "episode_number",
            "season_number",
            "play_count",
            "is_featured",
            "published_at",
            "series_title",
            "series_slug",
        ]

    def get_cover_url(self, obj):
        return obj.cover.url if obj.cover else None


class EpisodeDetailSerializer(serializers.ModelSerializer):
    cover_url = serializers.SerializerMethodField()
    audio_url = serializers.SerializerMethodField()
    series = PodcastSeriesListSerializer(read_only=True)

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
            "play_count",
            "is_featured",
            "published_at",
            "series",
        ]

    def get_cover_url(self, obj):
        return obj.cover.url if obj.cover else None

    def get_audio_url(self, obj):
        if obj.audio_file:
            return obj.audio_file.url
        return obj.audio_url or None


class EpisodeWriteSerializer(serializers.ModelSerializer):
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
            "is_featured",
            "published_at",
        ]
        extra_kwargs = {"slug": {"required": False}}

    def validate_audio_url(self, value):
        if value:
            verify_cloudinary_asset(value, "video")
        return value


class PodcastSeriesWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PodcastSeries
        fields = ["title", "slug", "description", "cover", "category", "is_featured"]
        extra_kwargs = {"slug": {"required": False}}


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
    guests = serializers.JSONField(required=False)
    is_featured = serializers.BooleanField(required=False)
    published_at = serializers.DateTimeField(required=False)


class EpisodeBulkCreateSerializer(serializers.Serializer):
    items = EpisodeWriteSerializer(many=True, min_length=1, max_length=100)


class EpisodeBulkUpdateSerializer(serializers.Serializer):
    items = EpisodeBulkUpdateItemSerializer(many=True, min_length=1, max_length=100)
