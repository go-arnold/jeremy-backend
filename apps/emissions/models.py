from cloudinary.models import CloudinaryField
from django.db import models

from apps.engagement.models import Engageable
from apps.streaming.fields import CloudflareLiveFields


class Emission(CloudflareLiveFields, Engageable):
    STATUS_LIVE = "live"
    STATUS_SCHEDULED = "scheduled"
    STATUS_RECORDED = "recorded"
    STATUS_CHOICES = [
        (STATUS_LIVE, "Live"),
        (STATUS_SCHEDULED, "Programmé"),
        (STATUS_RECORDED, "Enregistré"),
    ]

    title = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(blank=True)
    cover = CloudinaryField("cover", blank=True, null=True)
    stream_url = models.URLField(blank=True)
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
