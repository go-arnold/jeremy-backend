from django.db import models


class LiveStreamFields(models.Model):
    """Abstract mixin: self-hosted MediaMTX live-stream state for a broadcasting model.

    `stream_key` doubles as both the RTMP path name and the broadcaster's secret (OBS "Stream
    key" field) — admin-only, must never be included in public-facing serializers. The RTMP
    server URL itself is a constant (`settings.MEDIAMTX_RTMP_SERVER_URL`), not stored per-row.
    """

    stream_key = models.CharField(max_length=64, blank=True, db_index=True)
    playback_hls_url = models.URLField(blank=True)
    live_started_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True
