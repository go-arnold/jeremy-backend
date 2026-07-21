from cloudinary.models import CloudinaryField
from django.db import models


class HomeBanner(models.Model):
    """Singleton: the homepage's 'Banner photo + Textes' block, admin-editable."""

    image = CloudinaryField("image", blank=True, null=True)
    title = models.CharField(max_length=200, blank=True)
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
