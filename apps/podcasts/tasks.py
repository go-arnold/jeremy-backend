from celery import shared_task
from django.db.models import F


@shared_task(queue="default")
def async_increment_play(episode_id: int) -> None:
    from .models import PodcastEpisode

    PodcastEpisode.objects.filter(pk=episode_id).update(play_count=F("play_count") + 1)


@shared_task(queue="default")
def publish_scheduled_episodes() -> None:
    """Same pattern as apps.articles.tasks.publish_scheduled_articles: a draft episode with a
    past-due published_at flips to published automatically."""
    from django.utils import timezone

    from .models import PodcastEpisode

    PodcastEpisode.objects.filter(
        status=PodcastEpisode.STATUS_DRAFT, published_at__lte=timezone.now()
    ).update(status=PodcastEpisode.STATUS_PUBLISHED)


@shared_task(queue="default")
def update_series_episode_counts() -> None:
    from django.db.models import Count

    from .models import PodcastSeries

    series_list = PodcastSeries.objects.annotate(ep_count=Count("episodes"))
    updates = []
    for s in series_list:
        s.episode_count = s.ep_count
        updates.append(s)
    PodcastSeries.objects.bulk_update(updates, ["episode_count"])
