from django.core.cache import cache
from django.db import transaction

from .models import Artist, ArtistPhoto, ArtistVideo, Genre, Release

CACHE_TTL = 60 * 30  # 30 min
FEATURED_KEY = "artists:featured"


def get_featured_artists(limit: int = 12):
    cached = cache.get(FEATURED_KEY)
    if cached is not None:
        return cached
    qs = (
        Artist.objects.filter(is_featured=True)
        .prefetch_related("genres")
        .only("id", "name", "slug", "city", "photo", "is_featured")[:limit]
    )
    result = list(qs)
    cache.set(FEATURED_KEY, result, CACHE_TTL)
    return result


@transaction.atomic
def create_artist(validated_data: dict, genres: list) -> Artist:
    artist = Artist(**{k: v for k, v in validated_data.items() if k != "genres"})
    artist.save()
    if genres:
        artist.genre_names.set(genres)
    return artist


@transaction.atomic
def update_artist(artist: Artist, validated_data: dict, genres=None) -> Artist:
    for attr, value in validated_data.items():
        if attr != "genres":
            setattr(artist, attr, value)
    artist.save()
    if genres is not None:
        artist.genre_names.set(genres)
    _invalidate_artist_cache(artist)
    return artist


def _invalidate_artist_cache(artist: Artist) -> None:
    cache.delete(f"artists:detail:{artist.slug}")
    cache.delete(FEATURED_KEY)


def update_cached_counts(artist_id: int) -> None:
    try:
        artist = Artist.objects.get(pk=artist_id)
    except Artist.DoesNotExist:
        return
    artist.release_count = artist.releases.count()
    artist.video_count = artist.videos.count()
    artist.save(update_fields=["release_count", "video_count"])
