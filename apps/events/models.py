from cloudinary.models import CloudinaryField
from django.conf import settings
from django.db import models
from django.utils.text import slugify


class City(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    country = models.CharField(max_length=100, default="Congo (DRC)")

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "cities"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Event(models.Model):
    CATEGORY_CONCERT = "concert"
    CATEGORY_FESTIVAL = "festival"
    CATEGORY_EXPOSITION = "exposition"
    CATEGORY_CONFERENCE = "conference"
    CATEGORY_SPECTACLE = "spectacle"
    CATEGORY_CHOICES = [
        (CATEGORY_CONCERT, "Concert"),
        (CATEGORY_FESTIVAL, "Festival"),
        (CATEGORY_EXPOSITION, "Exposition"),
        (CATEGORY_CONFERENCE, "Conférence"),
        (CATEGORY_SPECTACLE, "Spectacle"),
    ]

    STATUS_UPCOMING = "upcoming"
    STATUS_LIVE = "live"
    STATUS_PAST = "past"
    STATUS_CHOICES = [
        (STATUS_UPCOMING, "À venir"),
        (STATUS_LIVE, "En cours"),
        (STATUS_PAST, "Passé"),
    ]

    title = models.CharField(max_length=300, db_index=True)
    slug = models.SlugField(max_length=320, unique=True)
    description = models.TextField()
    image = CloudinaryField("image", blank=True, null=True)
    date = models.DateTimeField(db_index=True)
    end_date = models.DateTimeField(null=True, blank=True)
    venue_name = models.CharField(max_length=200)
    venue_address = models.CharField(max_length=300, blank=True)
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, related_name="events")
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_UPCOMING, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    ticket_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ticket_link = models.URLField(blank=True)
    max_capacity = models.PositiveIntegerField(null=True, blank=True)
    current_registrations = models.PositiveIntegerField(default=0)
    artists = models.ManyToManyField("artists.Artist", blank=True, related_name="events")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date"]
        indexes = [
            models.Index(fields=["status", "date"]),
            models.Index(fields=["city", "status"]),
            models.Index(fields=["is_featured", "status"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            from core.utils import make_slug
            self.slug = make_slug(self.title, Event)
        super().save(*args, **kwargs)


class EventScheduleItem(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="schedule")
    time = models.TimeField()
    title = models.CharField(max_length=200)
    artist = models.ForeignKey(
        "artists.Artist", null=True, blank=True, on_delete=models.SET_NULL
    )
    duration_minutes = models.PositiveSmallIntegerField(default=30)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "time"]

    def __str__(self):
        return f"{self.event.title} — {self.title} @ {self.time}"


class EventRegistration(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="registrations")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("event", "user")
