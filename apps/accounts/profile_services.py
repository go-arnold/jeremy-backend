from apps.articles.models import ArticleLike
from apps.articles.models import Comment as ArticleComment
from apps.community.models import PostLike
from apps.engagement.models import Comment as EngagementComment
from apps.engagement.models import Like as EngagementLike
from apps.engagement.models import SavedItem

ACTIVITY_MAX_ITEMS = 50

_CONTENT_RESOLVERS = {
    "webtvvideo": lambda o: (o.title, o.thumbnail.url if o.thumbnail else "", "webtv"),
    "podcastepisode": lambda o: (o.title, o.cover.url if o.cover else "", "podcast"),
    "musicrelease": lambda o: (o.title, o.cover.url if o.cover else "", "release"),
    "communitypost": lambda o: (
        o.title or o.content[:60],
        (o.media[0]["url"] if o.media else ""),
        "community",
    ),
    "article": lambda o: (o.title, o.featured_image.url if o.featured_image else "", "article"),
}


def _resolve_target(obj) -> dict:
    if obj is None:
        return {"kind": "unknown", "id": None, "slug": None, "title": "", "cover_url": ""}
    resolver = _CONTENT_RESOLVERS.get(type(obj).__name__.lower())
    if not resolver:
        return {
            "kind": type(obj).__name__.lower(),
            "id": obj.pk,
            "slug": getattr(obj, "slug", None),
            "title": str(obj),
            "cover_url": "",
        }
    title, cover_url, kind = resolver(obj)
    return {
        "kind": kind,
        "id": obj.pk,
        "slug": getattr(obj, "slug", None),
        "title": title,
        "cover_url": cover_url or "",
    }


def get_saved_items(user, limit: int = ACTIVITY_MAX_ITEMS) -> list:
    """The 'signets' section of the profile — every non-live piece of content the user has
    bookmarked to consume later, across all content types, newest first."""
    saved = (
        SavedItem.objects.filter(user=user).prefetch_related("content_object").order_by("-created_at")[:limit]
    )
    return [{"saved_at": item.created_at, **_resolve_target(item.content_object)} for item in saved]


def _entry(action: str, created_at, target_obj, excerpt: str = "") -> dict:
    entry = {"action": action, "created_at": created_at, "target": _resolve_target(target_obj)}
    if excerpt:
        entry["excerpt"] = excerpt
    return entry


def get_activity_feed(user, limit: int = ACTIVITY_MAX_ITEMS) -> list:
    """The 'commentaires écrits' audit-log section — every like/comment the user has made,
    across both the generic engagement system and the bespoke Article comment system, newest
    first.

    No source can contribute more than `limit` entries to the final result, so each of the 5
    per-source queries is capped at `limit` too — a source can never need more than that to
    fill its share of the top-`limit` merged list. Because entries are newest-first, this
    naturally shows only the last 24h when the user has been very active (the top `limit`
    entries all fall inside that window) and reaches further back when they haven't — no
    explicit time window needed, and no discontinuity at an arbitrary "enough recent activity"
    threshold.
    """
    entries = []
    for like in (
        EngagementLike.objects.filter(user=user)
        .prefetch_related("content_object")
        .order_by("-created_at")[:limit]
    ):
        entries.append(_entry("like", like.created_at, like.content_object))
    for comment in (
        EngagementComment.objects.filter(author=user, is_deleted=False)
        .prefetch_related("content_object")
        .order_by("-created_at")[:limit]
    ):
        entries.append(_entry("comment", comment.created_at, comment.content_object, comment.content[:140]))
    for like in (
        ArticleLike.objects.filter(user=user).select_related("article").order_by("-created_at")[:limit]
    ):
        entries.append(_entry("like", like.created_at, like.article))
    for comment in (
        ArticleComment.objects.filter(author=user).select_related("article").order_by("-created_at")[:limit]
    ):
        entries.append(_entry("comment", comment.created_at, comment.article, comment.content[:140]))
    for like in PostLike.objects.filter(user=user).select_related("post").order_by("-created_at")[:limit]:
        entries.append(_entry("like", like.created_at, like.post))

    entries.sort(key=lambda e: e["created_at"], reverse=True)
    return entries[:limit]
