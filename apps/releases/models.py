from cloudinary.models import CloudinaryField
from django.db import models

from apps.engagement.models import Engageable


class MusicRelease(Engageable):
    FORMAT_ALBUM = "album"
    FORMAT_SINGLE = "single"
    FORMAT_CLIP = "clip"
    FORMAT_DOC = "documentaire"
    FORMAT_EXPO = "expo"
    FORMAT_CHOICES = [
        (FORMAT_ALBUM, "Album"),
        (FORMAT_SINGLE, "Single"),
        (FORMAT_CLIP, "Clip"),
        (FORMAT_DOC, "Documentaire"),
        (FORMAT_EXPO, "Exposition"),
    ]

    artist = models.ForeignKey("artists.Artist", on_delete=models.CASCADE, related_name="music_releases")
    title = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=220, unique=True)
    cover = CloudinaryField("cover", blank=True, null=True)
    release_date = models.DateField(db_index=True)
    format = models.CharField(max_length=20, choices=FORMAT_CHOICES, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    is_premiere = models.BooleanField(default=False)
    streaming_links = models.JSONField(default=dict, blank=True)
    description = models.TextField(blank=True)
    # Default URLField max_length (200) truncates/rejects real-world Cloudinary/CDN URLs with
    # long public_ids or transformation strings — widened as a safety margin.
    preview_url = models.URLField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-release_date"]
        indexes = [
            models.Index(fields=["-release_date", "format"]),
            models.Index(fields=["is_featured"]),
            models.Index(fields=["artist", "-release_date"]),
        ]

    def __str__(self):
        return f"{self.artist.name} — {self.title}"

    def save(self, *args, **kwargs):
        if not self.slug:
            from core.utils import make_slug

            self.slug = make_slug(f"{self.artist_id}-{self.title}", MusicRelease)
        super().save(*args, **kwargs)
