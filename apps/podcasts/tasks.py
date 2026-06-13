from celery import shared_task


@shared_task(queue="default")
def async_increment_play(episode_id: int) -> None:
    from .models import PodcastEpisode
    PodcastEpisode.objects.filter(pk=episode_id).update(
        play_count=PodcastEpisode.objects.values_list("play_count", flat=True).get(pk=episode_id) + 1
    )


@shared_task(queue="default")
def update_series_episode_counts() -> None:
    from .models import PodcastSeries
    from django.db.models import Count
    series_list = PodcastSeries.objects.annotate(ep_count=Count("episodes"))
    updates = []
    for s in series_list:
        s.episode_count = s.ep_count
        updates.append(s)
    PodcastSeries.objects.bulk_update(updates, ["episode_count"])
