from django.contrib.contenttypes.models import ContentType
from django.db.models import Count
from django.utils import timezone

from apps.articles.models import Article
from apps.articles.serializers import ArticleListSerializer
from apps.artists.models import Artist
from apps.artists.serializers import ArtistListSerializer
from apps.emissions.models import Emission
from apps.engagement.models import Like, SavedItem, Share
from apps.events.models import Event
from apps.events.serializers import EventListSerializer
from apps.live_music.models import MusicLiveSession
from apps.podcasts.models import PodcastEpisode
from apps.podcasts.serializers import EpisodeListSerializer
from apps.radio.models import RadioProgram
from apps.releases.models import MusicRelease
from apps.releases.serializers import ReleaseListSerializer
from apps.webtv.models import WebTVVideo

from .featured import serialize_featured_content
from .models import FeaturedContent, HomeBanner
from .serializers import HomeBannerSerializer

# Weighted so a share (more intentional) counts more than a passive like/save.
ENGAGEMENT_WEIGHTS = {Like: 1, Share: 2, SavedItem: 1}

_MONTH_NAMES_FR = {
    1: "Janvier",
    2: "Février",
    3: "Mars",
    4: "Avril",
    5: "Mai",
    6: "Juin",
    7: "Juillet",
    8: "Août",
    9: "Septembre",
    10: "Octobre",
    11: "Novembre",
    12: "Décembre",
}


def _monthly_engagement_scores(content_type) -> dict:
    now = timezone.now()
    scores: dict = {}
    for model, weight in ENGAGEMENT_WEIGHTS.items():
        rows = (
            model.objects.filter(
                content_type=content_type, created_at__year=now.year, created_at__month=now.month
            )
            .values("object_id")
            .annotate(n=Count("id"))
        )
        for row in rows:
            scores[row["object_id"]] = scores.get(row["object_id"], 0) + row["n"] * weight
    return scores


def hits_du_mois(limit: int = 10) -> list:
    content_type = ContentType.objects.get_for_model(MusicRelease)
    scores = _monthly_engagement_scores(content_type)
    if scores:
        top_ids = sorted(scores, key=scores.get, reverse=True)[:limit]
        releases = {r.pk: r for r in MusicRelease.objects.filter(pk__in=top_ids).select_related("artist")}
        return [releases[i] for i in top_ids if i in releases]
    # No engagement recorded yet this month — fall back to featured/most recent
    # so the section isn't permanently empty before users start interacting.
    return list(
        MusicRelease.objects.select_related("artist").order_by("-is_featured", "-release_date")[:limit]
    )


def hits_du_mois_period() -> str:
    now = timezone.localtime(timezone.now())
    return f"{_MONTH_NAMES_FR[now.month]} {now.year}"


def _live_count() -> int:
    return (
        WebTVVideo.objects.filter(is_live=True).count()
        + Emission.objects.filter(status=Emission.STATUS_LIVE).count()
        + RadioProgram.objects.filter(status=RadioProgram.STATUS_LIVE).count()
        + MusicLiveSession.objects.filter(status=MusicLiveSession.STATUS_LIVE).count()
    )


def contenus_a_la_une() -> list:
    items = []
    for fc in FeaturedContent.objects.select_related("content_type").order_by("order", "-created_at"):
        obj = fc.content_object
        if obj is None:
            continue  # underlying object was deleted — skip rather than error
        serialized = serialize_featured_content(obj)
        if serialized is not None:
            items.append(serialized)
    return items


def current_poll() -> dict | None:
    from apps.community.models import Poll
    from apps.community.serializers import PollSerializer

    poll = Poll.objects.filter(is_active=True).prefetch_related("options").order_by("-created_at").first()
    if poll is None:
        return None
    # No `request` in context on purpose: this payload is shared across everyone for 15 minutes
    # (@cache_page on home_view) — a per-user has_voted/selected_option_id here would leak
    # whoever's request happened to populate the cache to every other visitor. PollSerializer
    # safely defaults both to False/None without a request in context. The frontend should call
    # the dedicated (uncached) poll endpoint using this poll's `id` for the real per-user status.
    return PollSerializer(poll).data


def quelques_blogs(limit: int = 6) -> list:
    return list(
        Article.objects.filter(article_type=Article.TYPE_BLOG, status=Article.STATUS_PUBLISHED).order_by(
            "-published_at"
        )[:limit]
    )


def get_home_payload() -> dict:
    banner = HomeBanner.get_solo()

    artist_of_month = Artist.objects.filter(is_featured=True).prefetch_related("genres").first()
    featured_podcast = (
        PodcastEpisode.objects.filter(is_featured=True)
        .select_related("series")
        .order_by("-published_at")
        .first()
    )
    featured_event = Event.objects.filter(is_featured=True).order_by("-date").first()

    magazine_qs = Article.objects.filter(article_type=Article.TYPE_MAGAZINE, status=Article.STATUS_PUBLISHED)
    magazine_hero = magazine_qs.filter(is_featured=True).order_by("-published_at").first()
    magazine_rest = magazine_qs.exclude(pk=magazine_hero.pk if magazine_hero else None).order_by(
        "-published_at"
    )[:6]

    return {
        "banner": HomeBannerSerializer(banner).data,
        "stats": {
            "total_artists": Artist.objects.count(),
            "live_count": _live_count(),
        },
        "a_la_une": {
            "artist_of_month": ArtistListSerializer(artist_of_month).data if artist_of_month else None,
            "featured_podcast": EpisodeListSerializer(featured_podcast).data if featured_podcast else None,
            "featured_event": EventListSerializer(featured_event).data if featured_event else None,
        },
        "contenus_a_la_une": contenus_a_la_une(),
        "hits_du_mois": ReleaseListSerializer(hits_du_mois(), many=True).data,
        "hits_du_mois_period": hits_du_mois_period(),
        "sondage_actif": current_poll(),
        "magazine": {
            "hero": ArticleListSerializer(magazine_hero).data if magazine_hero else None,
            "articles": ArticleListSerializer(magazine_rest, many=True).data,
        },
        "blogs": ArticleListSerializer(quelques_blogs(), many=True).data,
    }
