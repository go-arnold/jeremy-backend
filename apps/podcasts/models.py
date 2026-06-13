from cloudinary.models import CloudinaryField
from django.db import models
from django.utils.text import slugify


class PodcastSeries(models.Model):
    CATEGORY_CHOICES = [
        ("talk", "Talk"),
        ("culture", "Culture"),
        ("musique", "Musique"),
        ("societe", "Société"),
        ("jeunesse", "Jeunesse"),
        ("sport", "Sport"),
    ]

    title = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(blank=True)
    cover = CloudinaryField("cover", blank=True, null=True)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    episode_count = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "podcast series"
        indexes = [models.Index(fields=["category", "is_featured"])]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class PodcastEpisode(models.Model):
    series = models.ForeignKey(PodcastSeries, on_delete=models.CASCADE, related_name="episodes")
    title = models.CharField(max_length=300, db_index=True)
    slug = models.SlugField(max_length=320, unique=True)
    description = models.TextField(blank=True)
    cover = CloudinaryField("cover", blank=True, null=True)
    audio_file = CloudinaryField("audio_file", resource_type="raw", blank=True, null=True)
    audio_url = models.URLField(blank=True)
    duration = models.CharField(max_length=10, blank=True)
    episode_number = models.PositiveSmallIntegerField(default=1)
    season_number = models.PositiveSmallIntegerField(default=1)
    guests = models.JSONField(default=list, blank=True)
    play_count = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False, db_index=True)
    published_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-published_at"]
        indexes = [
            models.Index(fields=["series", "-published_at"]),
            models.Index(fields=["is_featured", "-published_at"]),
        ]

    def __str__(self):
        return f"{self.series.title} — S{self.season_number}E{self.episode_number}: {self.title}"

    def save(self, *args, **kwargs):
        if not self.slug:
            from core.utils import make_slug
            self.slug = make_slug(self.title, PodcastEpisode)
        super().save(*args, **kwargs)
