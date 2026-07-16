from cloudinary.models import CloudinaryField
from django.db import models

from apps.engagement.models import Engageable
from apps.streaming.fields import LiveStreamFields

DAY_CHOICES = [
    (i, day)
    for i, day in enumerate(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
]


class MusicLiveSession(LiveStreamFields, Engageable):
    """The 'Son en direct' — an independent live-music broadcast (not tied to Radio/Emissions)."""

    STATUS_LIVE = "live"
    STATUS_SCHEDULED = "scheduled"
    STATUS_ENDED = "ended"
    STATUS_CHOICES = [
        (STATUS_LIVE, "Live"),
        (STATUS_SCHEDULED, "Programmé"),
        (STATUS_ENDED, "Terminé"),
    ]

    title = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=220, unique=True)
    cover = CloudinaryField("cover", blank=True, null=True)
    artists = models.ManyToManyField("artists.Artist", blank=True, related_name="live_music_sessions")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SCHEDULED, db_index=True)
    scheduled_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "-created_at"])]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            from core.utils import make_slug

            self.slug = make_slug(self.title, MusicLiveSession)
        super().save(*args, **kwargs)


class MusicLiveSlot(models.Model):
    """'Programmes' — the grille (per-day schedule) of sons à suivre."""

    title = models.CharField(max_length=200)
    cover = CloudinaryField("cover", blank=True, null=True)
    artist = models.ForeignKey(
        "artists.Artist", on_delete=models.SET_NULL, null=True, blank=True, related_name="live_music_slots"
    )
    day_of_week = models.PositiveSmallIntegerField(choices=DAY_CHOICES, default=0, db_index=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    duration_minutes = models.PositiveSmallIntegerField(default=30)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["day_of_week", "start_time"]
        indexes = [models.Index(fields=["day_of_week", "start_time"])]

    def __str__(self):
        return f"{self.title} ({self.get_day_of_week_display()} {self.start_time})"
