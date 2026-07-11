from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from .models import Comment, Like, SavedItem, Share


def is_currently_live(instance) -> bool:
    status = getattr(instance, "status", None)
    if status == "live":
        return True
    return bool(getattr(instance, "is_live", False))


@transaction.atomic
def toggle_like(instance, user) -> tuple[bool, int]:
    # Locking the target row serializes concurrent toggle calls on the same content item so
    # they can't both read the pre-toggle state before either commits (which previously could
    # let two overlapping requests interleave unpredictably). This does not — and can't, without
    # changing the API from a blind toggle to explicit like/unlike — prevent two genuinely
    # duplicate toggle requests (double-click, client retry) from canceling each other out;
    # that's an inherent property of a toggle endpoint, not a race condition per se.
    type(instance).objects.select_for_update().get(pk=instance.pk)
    content_type = ContentType.objects.get_for_model(instance)
    like, created = Like.objects.get_or_create(content_type=content_type, object_id=instance.pk, user=user)
    if not created:
        like.delete()
    count = Like.objects.filter(content_type=content_type, object_id=instance.pk).count()
    return created, count


def add_comment(instance, author, content: str, parent_id: int | None = None) -> Comment:
    content_type = ContentType.objects.get_for_model(instance)
    parent = None
    if parent_id:
        parent = Comment.objects.filter(
            pk=parent_id, content_type=content_type, object_id=instance.pk
        ).first()
    return Comment.objects.create(
        content_type=content_type,
        object_id=instance.pk,
        author=author,
        content=content,
        parent=parent,
    )


def delete_comment(instance, comment_id: int, user):
    """Soft-deletes a comment if `user` is its author or staff.

    Returns None if no such comment exists for this instance, False if the requester isn't
    allowed to delete it, True on success.
    """
    content_type = ContentType.objects.get_for_model(instance)
    comment = Comment.objects.filter(pk=comment_id, content_type=content_type, object_id=instance.pk).first()
    if not comment:
        return None
    if comment.author_id != user.id and not user.is_staff:
        return False
    comment.is_deleted = True
    comment.save(update_fields=["is_deleted"])
    return True


def list_comments(instance):
    content_type = ContentType.objects.get_for_model(instance)
    return (
        Comment.objects.filter(content_type=content_type, object_id=instance.pk, is_deleted=False)
        .select_related("author")
        .order_by("-created_at")
    )


def record_share(instance, user=None) -> int:
    content_type = ContentType.objects.get_for_model(instance)
    Share.objects.create(
        content_type=content_type,
        object_id=instance.pk,
        user=user if user and user.is_authenticated else None,
    )
    return Share.objects.filter(content_type=content_type, object_id=instance.pk).count()


class LiveContentNotSavableError(Exception):
    pass


@transaction.atomic
def toggle_save(instance, user) -> bool:
    if is_currently_live(instance):
        raise LiveContentNotSavableError("Le contenu en direct ne peut pas être enregistré pour plus tard.")
    # See toggle_like's comment above — same rationale for locking the target row.
    type(instance).objects.select_for_update().get(pk=instance.pk)
    content_type = ContentType.objects.get_for_model(instance)
    saved, created = SavedItem.objects.get_or_create(
        content_type=content_type, object_id=instance.pk, user=user
    )
    if not created:
        saved.delete()
    return created


def engagement_counts(instance) -> dict:
    content_type = ContentType.objects.get_for_model(instance)
    filters = {"content_type": content_type, "object_id": instance.pk}
    return {
        "like_count": Like.objects.filter(**filters).count(),
        "comment_count": Comment.objects.filter(**filters, is_deleted=False).count(),
        "share_count": Share.objects.filter(**filters).count(),
        "save_count": SavedItem.objects.filter(**filters).count(),
    }


def user_has_liked(instance, user) -> bool:
    if not user or not user.is_authenticated:
        return False
    content_type = ContentType.objects.get_for_model(instance)
    return Like.objects.filter(content_type=content_type, object_id=instance.pk, user=user).exists()


def user_has_saved(instance, user) -> bool:
    if not user or not user.is_authenticated:
        return False
    content_type = ContentType.objects.get_for_model(instance)
    return SavedItem.objects.filter(content_type=content_type, object_id=instance.pk, user=user).exists()
