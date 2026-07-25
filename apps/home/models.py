import operator
from functools import reduce

from cloudinary.models import CloudinaryField
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class HomeBanner(models.Model):
    """Singleton: the homepage's 'Banner photo + Textes' block, admin-editable."""

    image = CloudinaryField("image", blank=True, null=True)
    title = models.CharField(max_length=200, blank=True)
    # A word/phrase from `title` to render in an accent color on the frontend — the frontend
    # already reads this field (BACKEND-GAPS.md), it just didn't exist yet.
    title_highlight = models.CharField(max_length=200, blank=True)
    subtitle = models.CharField(max_length=300, blank=True)
    cta_label = models.CharField(max_length=100, blank=True)
    cta_url = models.URLField(max_length=500, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Home banner"
        verbose_name_plural = "Home banner"

    def __str__(self):
        return self.title or "Home banner"

    @classmethod
    def get_solo(cls) -> "HomeBanner":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


# (app_label, model) pairs eligible for the "Contenus à la Une" carousel below — kept as an
# explicit allowlist (rather than any ContentType) because apps/home/featured.py has a
# hand-written serialization adapter for exactly these 9 types and no others.
FEATURABLE_APP_MODELS = [
    ("artists", "artist"),
    ("emissions", "emission"),
    ("radio", "radioprogram"),
    ("webtv", "webtvvideo"),
    ("live_music", "musiclivesession"),
    ("events", "event"),
    ("releases", "musicrelease"),
    ("articles", "article"),
    ("podcasts", "podcastepisode"),
]

_FEATURABLE_CONTENT_TYPE_Q = reduce(
    operator.or_, (models.Q(app_label=app_label, model=model) for app_label, model in FEATURABLE_APP_MODELS)
)


class FeaturedContent(models.Model):
    """Admin-curated 'Contenus à la Une' carousel on the home page — an ordered, hand-picked
    list of items of any supported type (artist, émission, événement, sortie...), independent of
    each item's own `is_featured` flag (which drives that app's own separate featured slot, e.g.
    `a_la_une.artist_of_month`)."""

    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, limit_choices_to=_FEATURABLE_CONTENT_TYPE_Q
    )
    object_id = models.PositiveIntegerField(
        help_text="ID numérique de l'objet — visible dans son URL d'admin "
        "(ex. /admin/artists/artist/12/change/ → 12)."
    )
    content_object = GenericForeignKey("content_type", "object_id")
    order = models.PositiveIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "-created_at"]
        verbose_name = "Contenu à la une"
        verbose_name_plural = "Contenus à la une"

    def __str__(self):
        return f"{self.content_type} #{self.object_id}"
