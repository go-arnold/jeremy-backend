from cloudinary.models import CloudinaryField
from django.db import models

from apps.engagement.models import Engageable
from apps.streaming.fields import CloudflareLiveFields


class WebTVVideo(CloudflareLiveFields, Engageable):
    CATEGORY_FREESTYLES = "freestyles"
    CATEGORY_STUDIO = "studio_sessions"
    CATEGORY_DOCS = "docs"
    CATEGORY_INTERVIEWS = "interviews"
    CATEGORY_PREMIERS = "premiers"
    CATEGORY_CONCERTS = "concerts"
    CATEGORY_CHOICES = [
        (CATEGORY_FREESTYLES, "Freestyles"),
        (CATEGORY_STUDIO, "Studio Sessions"),
        (CATEGORY_DOCS, "Documentaires"),
        (CATEGORY_INTERVIEWS, "Interviews"),
        (CATEGORY_PREMIERS, "Premières"),
        (CATEGORY_CONCERTS, "Concerts"),
    ]

    title = models.CharField(max_length=300, db_index=True)
    slug = models.SlugField(max_length=320, unique=True)
    description = models.TextField(blank=True)
    thumbnail = CloudinaryField("thumbnail", blank=True, null=True)
    video_url = models.URLField()
    duration = models.CharField(max_length=10, blank=True)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, db_index=True)
    is_premier = models.BooleanField(default=False, db_index=True)
    is_live = models.BooleanField(default=False)
    location = models.CharField(max_length=100, blank=True)
    artists = models.ManyToManyField("artists.Artist", blank=True, related_name="webtv_videos")
    view_count = models.PositiveIntegerField(default=0)
    published_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-published_at"]
        indexes = [
            models.Index(fields=["category", "-published_at"]),
            models.Index(fields=["is_premier", "-published_at"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            from core.utils import make_slug

            self.slug = make_slug(self.title, WebTVVideo)
        super().save(*args, **kwargs)
