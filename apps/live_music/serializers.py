from rest_framework import serializers

from apps.realtime import presence

from .models import MusicLiveSession, MusicLiveSlot


class MusicLiveSessionSerializer(serializers.ModelSerializer):
    artist_names = serializers.SerializerMethodField()
    online_followers = serializers.SerializerMethodField()

    class Meta:
        model = MusicLiveSession
        fields = [
            "id",
            "title",
            "slug",
            "artist_names",
            "status",
            "cf_playback_hls_url",
            "cf_playback_dash_url",
            "online_followers",
            "live_started_at",
            "created_at",
        ]

    def get_artist_names(self, obj):
        return [a.name for a in obj.artists.all()]

    def get_online_followers(self, obj):
        return presence.count("live_music", str(obj.pk))


class MusicLiveSessionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = MusicLiveSession
        fields = ["title", "slug", "artists", "status"]
        extra_kwargs = {"slug": {"required": False}}


class MusicLiveSlotSerializer(serializers.ModelSerializer):
    artist_name = serializers.CharField(source="artist.name", read_only=True)
    day_name = serializers.CharField(source="get_day_of_week_display", read_only=True)

    class Meta:
        model = MusicLiveSlot
        fields = [
            "id",
            "title",
            "artist_name",
            "day_of_week",
            "day_name",
            "start_time",
            "end_time",
            "duration_minutes",
        ]


class MusicLiveSlotWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = MusicLiveSlot
        fields = ["title", "artist", "day_of_week", "start_time", "end_time", "duration_minutes"]
