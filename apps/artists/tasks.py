from celery import shared_task


@shared_task(queue="default")
def update_artist_counts(artist_id: int) -> None:
    from .services import update_cached_counts
    update_cached_counts(artist_id)


@shared_task(queue="default")
def warm_featured_cache() -> None:
    """Pre-warm the featured artists cache."""
    from .services import get_featured_artists
    from django.core.cache import cache
    cache.delete("artists:featured")
    get_featured_artists()
