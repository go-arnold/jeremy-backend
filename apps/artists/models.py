from cloudinary.models import CloudinaryField
from django.db import models
from django.utils.text import slugify


class Genre(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Artist(models.Model):
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=220, unique=True, db_index=True)
    bio = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default="Congo (DRC)")
    photo = CloudinaryField("photo", blank=True, null=True)
    cover_image = CloudinaryField("cover_image", blank=True, null=True)
    genres = models.ManyToManyField(Genre, blank=True, related_name="artists")
    is_featured = models.BooleanField(default=False, db_index=True)
    social_links = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Cached counts — updated via Celery
    release_count = models.PositiveSmallIntegerField(default=0)
    video_count = models.PositiveSmallIntegerField(default=0)

    # Reverse from accounts.User.favorite_artists
    # (defined in User model via ManyToManyField)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["is_featured", "name"]),
            models.Index(fields=["city"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            from core.utils import make_slug

            self.slug = make_slug(self.name, Artist)
        super().save(*args, **kwargs)


class Release(models.Model):
    FORMAT_ALBUM = "album"
    FORMAT_SINGLE = "single"
    FORMAT_EP = "ep"
    FORMAT_CHOICES = [
        (FORMAT_ALBUM, "Album"),
        (FORMAT_SINGLE, "Single"),
        (FORMAT_EP, "EP"),
    ]

    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name="releases")
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    cover = CloudinaryField("cover", blank=True, null=True)
    release_date = models.DateField(db_index=True)
    format = models.CharField(max_length=20, choices=FORMAT_CHOICES, default=FORMAT_ALBUM)
    streaming_links = models.JSONField(default=dict, blank=True)
    description = models.TextField(blank=True)
    # Default URLField max_length (200) truncates/rejects real-world Cloudinary/CDN URLs with
    # long public_ids or transformation strings — widened as a safety margin.
    preview_url = models.URLField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-release_date"]
        indexes = [models.Index(fields=["artist", "-release_date"])]

    def __str__(self):
        return f"{self.artist.name} — {self.title}"


class ArtistVideo(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name="videos")
    title = models.CharField(max_length=200)
    thumbnail = CloudinaryField("thumbnail", blank=True, null=True)
    video_url = models.URLField(max_length=500)
    duration = models.CharField(max_length=10, blank=True)
    view_count = models.PositiveIntegerField(default=0)
    published_at = models.DateField(null=True, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "-published_at"]

    def __str__(self):
        return self.title


class ArtistPhoto(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name="gallery")
    image = CloudinaryField("image")
    caption = models.CharField(max_length=200, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.artist.name} photo #{self.order}"
