from cloudinary.models import CloudinaryField
from django.conf import settings
from django.db import models


class Badge(models.Model):
    """A badge definition — thresholds are data, not code, so they can be tuned from the
    admin without a deploy (the reported example tiers — a few hours, then more — are seeded
    as a starting point, not hardcoded constants)."""

    CRITERIA_LISTENING_SECONDS = "listening_seconds"
    CRITERIA_CHOICES = [
        (CRITERIA_LISTENING_SECONDS, "Temps de consommation cumulé (secondes)"),
    ]

    slug = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = CloudinaryField("icon", blank=True, null=True)
    criteria_type = models.CharField(
        max_length=30, choices=CRITERIA_CHOICES, default=CRITERIA_LISTENING_SECONDS
    )
    # 0 = awarded to every user regardless of activity (the "default" badge).
    threshold_seconds = models.PositiveIntegerField(default=0)
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["order", "threshold_seconds"]

    def __str__(self):
        return self.name


class UserBadge(models.Model):
    """Permanent record — badges are never revoked once earned."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="badges")
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name="awarded_to")
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "badge")
        ordering = ["-earned_at"]

    def __str__(self):
        return f"{self.user} — {self.badge}"


class ConsumptionLog(models.Model):
    """One increment of real listening/watching time, reported by the frontend player via a
    periodic heartbeat while content is actively playing. Cumulative sums across this table
    are what badge thresholds and the 'médias suivis (classée)' ranking are computed from."""

    CONTENT_RADIO = "radio"
    CONTENT_PODCAST = "podcast"
    CONTENT_WEBTV = "webtv"
    CONTENT_LIVE_MUSIC = "live_music"
    CONTENT_RELEASE = "release"
    CONTENT_TYPE_CHOICES = [
        (CONTENT_RADIO, "Radio"),
        (CONTENT_PODCAST, "Podcast"),
        (CONTENT_WEBTV, "Web TV"),
        (CONTENT_LIVE_MUSIC, "Live Music"),
        (CONTENT_RELEASE, "Release"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="consumption_logs"
    )
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES, db_index=True)
    object_id = models.PositiveIntegerField()
    # Denormalized so the ranking endpoint doesn't need to resolve 5 different models per row.
    title = models.CharField(max_length=300, blank=True)
    cover_url = models.URLField(blank=True)
    seconds = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["user", "content_type", "object_id"]),
        ]

    def __str__(self):
        return f"{self.user} — {self.content_type}#{self.object_id} (+{self.seconds}s)"
