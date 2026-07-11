from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Sum

from apps.articles.models import Article
from apps.artists.models import Artist
from apps.community.models import Challenge, CommunityPost, Poll
from apps.events.models import Event, EventRegistration
from apps.podcasts.models import PodcastEpisode, PodcastSeries
from apps.radio.models import RadioProgram
from apps.releases.models import MusicRelease
from apps.webtv.models import WebTVVideo

User = get_user_model()

CACHE_KEY = "analytics:dashboard"
CACHE_TTL = 60 * 10


def _total(queryset, field: str) -> int:
    return queryset.aggregate(total=Sum(field))["total"] or 0


def get_dashboard_stats() -> dict:
    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return cached

    stats = {
        "counts": {
            "artists": Artist.objects.count(),
            "articles": Article.objects.count(),
            "events": Event.objects.count(),
            "event_registrations": EventRegistration.objects.count(),
            "podcast_series": PodcastSeries.objects.count(),
            "podcast_episodes": PodcastEpisode.objects.count(),
            "radio_programs": RadioProgram.objects.count(),
            "webtv_videos": WebTVVideo.objects.count(),
            "releases": MusicRelease.objects.count(),
            "community_posts": CommunityPost.objects.count(),
            "challenges": Challenge.objects.count(),
            "polls": Poll.objects.count(),
            "users": User.objects.count(),
        },
        "totals": {
            "article_views": _total(Article.objects, "view_count"),
            "article_likes": _total(Article.objects, "like_count"),
            "webtv_views": _total(WebTVVideo.objects, "view_count"),
            "podcast_plays": _total(PodcastEpisode.objects, "play_count"),
            "post_likes": _total(CommunityPost.objects, "like_count"),
        },
        "top_articles": list(
            Article.objects.order_by("-view_count").values("id", "title", "slug", "view_count")[:5]
        ),
        "top_webtv_videos": list(
            WebTVVideo.objects.order_by("-view_count").values("id", "title", "slug", "view_count")[:5]
        ),
        "top_podcast_episodes": list(
            PodcastEpisode.objects.order_by("-play_count").values("id", "title", "slug", "play_count")[:5]
        ),
    }
    cache.set(CACHE_KEY, stats, CACHE_TTL)
    return stats
