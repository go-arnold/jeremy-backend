from cloudinary.models import CloudinaryField
from django.conf import settings
from django.db import models

from apps.engagement.models import Engageable
from apps.streaming.fields import LiveStreamFields


class RadioProgram(LiveStreamFields, Engageable):
    STATUS_LIVE = "live"
    STATUS_UPCOMING = "upcoming"
    STATUS_ENDED = "ended"
    STATUS_CHOICES = [
        (STATUS_LIVE, "Live"),
        (STATUS_UPCOMING, "Upcoming"),
        (STATUS_ENDED, "Ended"),
    ]

    DAY_CHOICES = [
        (i, day)
        for i, day in enumerate(
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        )
    ]

    # Distinct from `status == STATUS_ENDED` (just means "was live, isn't anymore") — this tracks
    # whether a replayable audio file was actually captured and uploaded.
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

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(blank=True)
    cover = CloudinaryField("cover", blank=True, null=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    day_of_week = models.PositiveSmallIntegerField(choices=DAY_CHOICES, default=0, db_index=True)
    presenter = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_UPCOMING, db_index=True)
    # Default URLField max_length (200) truncates/rejects real-world Cloudinary/CDN URLs with
    # long public_ids or transformation strings — widened as a safety margin.
    stream_url = models.URLField(max_length=500, blank=True)
    # Populated by apps.streaming.tasks.finalize_live_recording once a live broadcast's
    # recording has been uploaded — lets a past program be replayed as a normal VOD.
    audio_url = models.URLField(max_length=500, blank=True)
    recording_status = models.CharField(
        max_length=20, choices=RECORDING_STATUS_CHOICES, default=RECORDING_NONE
    )
    listener_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["day_of_week", "start_time"]
        indexes = [models.Index(fields=["status", "day_of_week"])]

    def __str__(self):
        return f"{self.title} ({self.get_day_of_week_display()} {self.start_time})"

    def save(self, *args, **kwargs):
        if not self.slug:
            from core.utils import make_slug

            self.slug = make_slug(self.title, RadioProgram)
        super().save(*args, **kwargs)


class RadioChat(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="radio_chats")
    message = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["-created_at"])]

    def __str__(self):
        return f"{self.user}: {self.message[:50]}"
