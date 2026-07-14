from django.apps import apps as django_apps
from django.db.models import Sum

from .models import Badge, ConsumptionLog, UserBadge

# Where to look up the real object behind a heartbeat's (content_type, object_id) pair, so a
# client can't fabricate consumption for content that doesn't exist.
CONTENT_MODEL_MAP = {
    ConsumptionLog.CONTENT_RADIO: ("radio", "RadioProgram"),
    ConsumptionLog.CONTENT_PODCAST: ("podcasts", "PodcastEpisode"),
    ConsumptionLog.CONTENT_WEBTV: ("webtv", "WebTVVideo"),
    ConsumptionLog.CONTENT_LIVE_MUSIC: ("live_music", "MusicLiveSession"),
    ConsumptionLog.CONTENT_RELEASE: ("releases", "MusicRelease"),
}


def content_object_exists(content_type: str, object_id: int) -> bool:
    app_label, model_name = CONTENT_MODEL_MAP[content_type]
    model = django_apps.get_model(app_label, model_name)
    return model.objects.filter(pk=object_id).exists()


def record_consumption(
    user, content_type: str, object_id: int, seconds: int, title: str = "", cover_url: str = ""
):
    """Logs a chunk of real listening/watching time and awards any newly-qualifying badges.

    Returns the list of newly-earned Badge instances (empty if none) so the caller can surface
    a "you unlocked X!" notification.
    """
    ConsumptionLog.objects.create(
        user=user,
        content_type=content_type,
        object_id=object_id,
        seconds=seconds,
        title=title,
        cover_url=cover_url,
    )
    return check_and_award_badges(user)


def get_total_seconds(user) -> int:
    return ConsumptionLog.objects.filter(user=user).aggregate(total=Sum("seconds"))["total"] or 0


def check_and_award_badges(user) -> list:
    total = get_total_seconds(user)
    already_earned_ids = set(UserBadge.objects.filter(user=user).values_list("badge_id", flat=True))
    qualifying = Badge.objects.filter(
        is_active=True,
        criteria_type=Badge.CRITERIA_LISTENING_SECONDS,
        threshold_seconds__lte=total,
    ).exclude(pk__in=already_earned_ids)

    newly_earned = []
    for badge in qualifying:
        _, created = UserBadge.objects.get_or_create(user=user, badge=badge)
        if created:
            newly_earned.append(badge)
    return newly_earned


def award_default_badges(user) -> None:
    """Called once at signup — badges with threshold_seconds=0 apply to everyone immediately,
    not just the next time they log listening activity."""
    check_and_award_badges(user)


# How many of the user's most recent heartbeat rows to scan when building the ranking — bounds
# the query to a single, fixed-cost fetch instead of one extra query per distinct content item.
MEDIA_RANKING_SCAN_LIMIT = 2000


def get_media_ranking(user, limit: int = 20) -> list:
    """Top content by cumulative seconds consumed, most-consumed first — the 'médias suivis
    (classée)' section of the profile.

    Single query: scans the user's most recent heartbeats (newest first) and aggregates in
    Python, so the first row seen for a given (content_type, object_id) is also its most
    recent — giving the same "latest title/cover" semantics as before, without a per-row
    lookup query.
    """
    logs = (
        ConsumptionLog.objects.filter(user=user)
        .order_by("-created_at")
        .values("content_type", "object_id", "title", "cover_url", "seconds")[:MEDIA_RANKING_SCAN_LIMIT]
    )
    aggregated = {}
    for log in logs:
        key = (log["content_type"], log["object_id"])
        entry = aggregated.get(key)
        if entry is None:
            aggregated[key] = entry = {
                "content_type": log["content_type"],
                "object_id": log["object_id"],
                "title": log["title"],
                "cover_url": log["cover_url"],
                "total_seconds": 0,
            }
        entry["total_seconds"] += log["seconds"]

    ranked = sorted(aggregated.values(), key=lambda entry: entry["total_seconds"], reverse=True)
    return ranked[:limit]
