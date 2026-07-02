from cloudinary.models import CloudinaryField
from django.conf import settings
from django.db import models


class RadioProgram(models.Model):
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

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(blank=True)
    cover = CloudinaryField("cover", blank=True, null=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    day_of_week = models.PositiveSmallIntegerField(choices=DAY_CHOICES, default=0, db_index=True)
    presenter = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_UPCOMING, db_index=True)
    stream_url = models.URLField(blank=True)
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
