from cloudinary.models import CloudinaryField
from django.db import models

from apps.engagement.models import Engageable
from apps.streaming.fields import LiveStreamFields


class Emission(LiveStreamFields, Engageable):
    STATUS_LIVE = "live"
    STATUS_SCHEDULED = "scheduled"
    STATUS_RECORDED = "recorded"
    STATUS_CHOICES = [
        (STATUS_LIVE, "Live"),
        (STATUS_SCHEDULED, "Programmé"),
        (STATUS_RECORDED, "Enregistré"),
    ]

    # Distinct from `status == STATUS_RECORDED` (which just means "was live, isn't anymore") —
    # this tracks whether a replayable video file was actually captured and uploaded.
    RECORDING_NONE = "none"
    RECORDING_PENDING = "pending"
    RECORDING_READY = "ready"
    RECORDING_FAILED = "failed"
    RECORDING_STATUS_CHOICES = [
        (RECORDING_NONE, "Aucun"),
        (RECORDING_PENDING, "En cours de traitement"),
        (RECORDING_READY, "Disponible"),
        (RECORDING_FAILED, "Échec"),
    ]

    title = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(blank=True)
    cover = CloudinaryField("cover", blank=True, null=True)
    # Default URLField max_length (200) truncates/rejects real-world Cloudinary/CDN URLs with
    # long public_ids or transformation strings — widened as a safety margin.
    stream_url = models.URLField(max_length=500, blank=True)
    # Populated by apps.streaming.tasks.finalize_live_recording once a live broadcast's
    # recording has been uploaded — lets a past emission be replayed as a normal VOD.
    video_url = models.URLField(max_length=500, blank=True)
    recording_status = models.CharField(
        max_length=20, choices=RECORDING_STATUS_CHOICES, default=RECORDING_NONE
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SCHEDULED, db_index=True)
    scheduled_at = models.DateTimeField(null=True, blank=True, db_index=True)
    duration_minutes = models.PositiveSmallIntegerField(default=60)
    viewer_count = models.PositiveIntegerField(default=0)
    total_views = models.PositiveIntegerField(default=0)
    hosts = models.ManyToManyField("artists.Artist", blank=True, related_name="emissions")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-scheduled_at"]
        indexes = [
            models.Index(fields=["status", "-scheduled_at"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            from core.utils import make_slug

            self.slug = make_slug(self.title, Emission)
        super().save(*args, **kwargs)
