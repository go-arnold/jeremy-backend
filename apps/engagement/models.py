from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Like(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="engagement_likes"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("content_type", "object_id", "user")
        indexes = [models.Index(fields=["content_type", "object_id"])]


class Comment(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="engagement_comments"
    )
    content = models.TextField(max_length=1000)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies"
    )
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["content_type", "object_id", "-created_at"])]

    def __str__(self):
        return f"{self.author} on {self.content_type}#{self.object_id}"


class Share(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="engagement_shares",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["content_type", "object_id"])]


class SavedItem(models.Model):
    """A user's 'listen/watch later' playlist entry — never used for live content."""

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_items")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("content_type", "object_id", "user")
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]


class Engageable(models.Model):
    """Abstract mixin for any model that can be liked/commented/shared/saved.

    Without these GenericRelation fields, Django has no way to know that a Like/Comment/Share/
    SavedItem row is "related" to a given instance beyond the raw content_type/object_id pair —
    deleting the instance would leave those rows permanently orphaned instead of cascading.
    `related_query_name="+"` disables the reverse name (e.g. `Like.objects.filter(webtvvideo=...)`)
    since every consumer of this mixin would otherwise need a distinct name; engagement lookups
    always go through content_type/object_id in apps.engagement.services instead.
    """

    engagement_likes = GenericRelation(Like, related_query_name="+")
    engagement_comments = GenericRelation(Comment, related_query_name="+")
    engagement_shares = GenericRelation(Share, related_query_name="+")
    engagement_saves = GenericRelation(SavedItem, related_query_name="+")

    class Meta:
        abstract = True
