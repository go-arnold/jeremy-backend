from rest_framework import serializers

from .models import PodcastEpisode, PodcastSeries


class PodcastSeriesListSerializer(serializers.ModelSerializer):
    cover_url = serializers.SerializerMethodField()

    class Meta:
        model = PodcastSeries
        fields = ["id", "title", "slug", "description", "cover_url", "category", "is_featured", "episode_count"]

    def get_cover_url(self, obj):
        return obj.cover.url if obj.cover else None


class EpisodeListSerializer(serializers.ModelSerializer):
    cover_url = serializers.SerializerMethodField()
    series_title = serializers.CharField(source="series.title", read_only=True)
    series_slug = serializers.CharField(source="series.slug", read_only=True)

    class Meta:
        model = PodcastEpisode
        fields = [
            "id", "title", "slug", "description", "cover_url",
            "duration", "episode_number", "season_number",
            "play_count", "is_featured", "published_at",
            "series_title", "series_slug",
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
            "id", "title", "slug", "description", "cover_url",
            "audio_url", "duration", "episode_number", "season_number",
            "guests", "play_count", "is_featured", "published_at",
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
            "series", "title", "slug", "description", "cover",
            "audio_file", "audio_url", "duration", "episode_number",
            "season_number", "guests", "is_featured", "published_at",
        ]
        extra_kwargs = {"slug": {"required": False}}


class PodcastSeriesWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PodcastSeries
        fields = ["title", "slug", "description", "cover", "category", "is_featured"]
        extra_kwargs = {"slug": {"required": False}}
