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
