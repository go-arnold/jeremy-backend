from django.core.cache import cache
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import Article, ArticleLike, Comment


@transaction.atomic
def create_article(validated_data: dict, author) -> Article:
    data = dict(validated_data)
    tags = data.pop("tags", [])
    article = Article.objects.create(author=author, **data)
    if tags:
        article.tags.set(tags)
    return article


@transaction.atomic
def update_article(article: Article, validated_data: dict) -> Article:
    data = dict(validated_data)
    tags = data.pop("tags", None)
    for attr, value in data.items():
        setattr(article, attr, value)
    article.save()
    if tags is not None:
        article.tags.set(tags)
    cache.delete(f"articles:detail:{article.slug}")
    return article


@transaction.atomic
def delete_article(article: Article) -> None:
    cache.delete(f"articles:detail:{article.slug}")
    article.delete()


@transaction.atomic
def publish_article(article: Article) -> Article:
    article.status = Article.STATUS_PUBLISHED
    article.published_at = timezone.now()
    article.save(update_fields=["status", "published_at"])
    cache.delete(f"articles:detail:{article.slug}")
    return article


@transaction.atomic
def toggle_like(article: Article, user) -> dict:
    like, created = ArticleLike.objects.get_or_create(article=article, user=user)
    if not created:
        like.delete()
        Article.objects.filter(pk=article.pk).update(like_count=F("like_count") - 1)
        return {"action": "unliked"}
    Article.objects.filter(pk=article.pk).update(like_count=F("like_count") + 1)
    return {"action": "liked"}


@transaction.atomic
def bulk_create_articles(items: list, author) -> list:
    from core.utils import gen_unique_slug

    used: set = set()
    tag_map = []
    objs = []
    for data in items:
        d = dict(data)
        tags = d.pop("tags", [])
        tag_map.append(tags)
        if not d.get("slug"):
            d["slug"] = gen_unique_slug(d["title"], Article, used)
        objs.append(Article(author=author, **d))
    created = Article.objects.bulk_create(objs, batch_size=500)
    Through = Article.tags.through
    m2m = [Through(article=a, tag=t) for a, tags in zip(created, tag_map) for t in tags]
    if m2m:
        Through.objects.bulk_create(m2m, batch_size=500, ignore_conflicts=True)
    return created


@transaction.atomic
def bulk_update_articles(items: list) -> int:
    ids = [d["id"] for d in items]
    obj_map = {o.pk: o for o in Article.objects.filter(pk__in=ids)}
    fields: set = set()
    to_update = []
    for data in items:
        obj = obj_map.get(data["id"])
        if not obj:
            continue
        for k, v in data.items():
            if k != "id":
                setattr(obj, k, v)
                fields.add(k)
        to_update.append(obj)
    if to_update and fields:
        Article.objects.bulk_update(to_update, list(fields), batch_size=500)
    return len(to_update)


@transaction.atomic
def bulk_delete_articles(ids: list) -> int:
    deleted, _ = Article.objects.filter(pk__in=ids).delete()
    return deleted


def increment_view_count(article_id: int) -> None:
    Article.objects.filter(pk=article_id).update(view_count=F("view_count") + 1)


@transaction.atomic
def add_comment(article: Article, author, content: str, parent_id=None) -> Comment:
    parent = None
    if parent_id:
        try:
            parent = Comment.objects.get(pk=parent_id, article=article)
        except Comment.DoesNotExist:
            pass
    return Comment.objects.create(article=article, author=author, content=content, parent=parent)
