from django.db import models


class CloudflareLiveFields(models.Model):
    """Abstract mixin: Cloudflare Stream live-input state for a broadcasting model.

    `cf_rtmps_key` is the RTMPS stream key handed to the broadcaster (OBS etc.) —
    admin-only, must never be included in public-facing serializers.
    """

    cf_live_input_uid = models.CharField(max_length=64, blank=True)
    cf_rtmps_url = models.URLField(blank=True)
    cf_rtmps_key = models.CharField(max_length=128, blank=True)
    cf_playback_hls_url = models.URLField(blank=True)
    cf_playback_dash_url = models.URLField(blank=True)
    live_started_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True
