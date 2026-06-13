from cloudinary.models import CloudinaryField
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_ADMIN = "admin"
    ROLE_EDITOR = "editor"
    ROLE_MODERATOR = "moderator"
    ROLE_VIEWER = "viewer"
    ROLE_CHOICES = [
        (ROLE_ADMIN, "Admin"),
        (ROLE_EDITOR, "Editor"),
        (ROLE_MODERATOR, "Moderator"),
        (ROLE_VIEWER, "Viewer"),
    ]

    email = models.EmailField(unique=True)
    avatar = CloudinaryField("avatar", blank=True, null=True)
    cover_image = CloudinaryField("cover_image", blank=True, null=True)
    bio = models.CharField(max_length=200, blank=True)
    handle = models.CharField(max_length=50, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_VIEWER)
    google_id = models.CharField(max_length=128, blank=True, db_index=True)
    is_verified = models.BooleanField(default=False)
    is_online = models.BooleanField(default=False)
    listen_count = models.PositiveIntegerField(default=0)
    favorite_artists = models.ManyToManyField(
        "artists.Artist", blank=True, related_name="favorited_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        db_table = "accounts_user"
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["role"]),
        ]

    def __str__(self):
        return self.email


class ListenHistory(models.Model):
    CONTENT_RADIO = "radio"
    CONTENT_PODCAST = "podcast"
    CONTENT_TYPE_CHOICES = [
        (CONTENT_RADIO, "Radio"),
        (CONTENT_PODCAST, "Podcast"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="history")
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES)
    content_id = models.PositiveIntegerField()
    title = models.CharField(max_length=300)
    subtitle = models.CharField(max_length=200, blank=True)
    cover_image = models.URLField(blank=True)
    progress_percent = models.PositiveSmallIntegerField(default=0)
    listened_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-listened_at"]
        indexes = [models.Index(fields=["user", "-listened_at"])]
