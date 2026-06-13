from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from .models import Article, ArticleLike, Comment


@transaction.atomic
def publish_article(article: Article) -> Article:
    article.status = Article.STATUS_PUBLISHED
    article.published_at = timezone.now()
    article.save(update_fields=["status", "published_at"])
    cache.delete(f"articles:detail:{article.slug}")
    return article


def toggle_like(article: Article, user) -> dict:
    like, created = ArticleLike.objects.get_or_create(article=article, user=user)
    if not created:
        like.delete()
        Article.objects.filter(pk=article.pk).update(like_count=Article.objects.get(pk=article.pk).likes.count())
        return {"action": "unliked", "like_count": article.likes.count()}
    Article.objects.filter(pk=article.pk).update(like_count=article.likes.count())
    return {"action": "liked", "like_count": article.likes.count()}


def increment_view_count(article_id: int) -> None:
    Article.objects.filter(pk=article_id).update(view_count=Article.view_count.field.model.objects.get(pk=article_id).view_count + 1)


@transaction.atomic
def add_comment(article: Article, author, content: str, parent_id=None) -> Comment:
    parent = None
    if parent_id:
        try:
            parent = Comment.objects.get(pk=parent_id, article=article)
        except Comment.DoesNotExist:
            pass
    return Comment.objects.create(article=article, author=author, content=content, parent=parent)
