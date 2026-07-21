from django.core.cache import cache
from django.db import transaction

from .models import Artist, ArtistPhoto, ArtistVideo, Release

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
        artist.genres.set(genres)
    cache.delete(FEATURED_KEY)
    return artist


@transaction.atomic
def update_artist(artist: Artist, validated_data: dict, genres=None) -> Artist:
    for attr, value in validated_data.items():
        if attr != "genres":
            setattr(artist, attr, value)
    artist.save()
    if genres is not None:
        artist.genres.set(genres)
    _invalidate_artist_cache(artist)
    return artist


def _invalidate_artist_cache(artist: Artist) -> None:
    cache.delete(f"artists:detail:{artist.slug}")
    cache.delete(FEATURED_KEY)


@transaction.atomic
def bulk_create_artists(items: list) -> list:
    from core.utils import gen_unique_slug

    used: set = set()
    genre_map = []
    objs = []
    for data in items:
        d = dict(data)
        genres = d.pop("genres", [])
        genre_map.append(genres)
        if not d.get("slug"):
            d["slug"] = gen_unique_slug(d["name"], Artist, used)
        objs.append(Artist(**d))
    created = Artist.objects.bulk_create(objs, batch_size=500)
    Through = Artist.genres.through
    m2m = [Through(artist=a, genre=g) for a, genres in zip(created, genre_map) for g in genres]
    if m2m:
        Through.objects.bulk_create(m2m, batch_size=500, ignore_conflicts=True)
    cache.delete(FEATURED_KEY)
    return created


@transaction.atomic
def bulk_update_artists(items: list) -> int:
    ids = [d["id"] for d in items]
    obj_map = {o.pk: o for o in Artist.objects.filter(pk__in=ids)}
    original_slugs = {pk: obj.slug for pk, obj in obj_map.items()}
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
        Artist.objects.bulk_update(to_update, list(fields), batch_size=500)
    for obj in to_update:
        cache.delete(f"artists:detail:{original_slugs[obj.pk]}")
        if obj.slug != original_slugs[obj.pk]:
            cache.delete(f"artists:detail:{obj.slug}")
    cache.delete(FEATURED_KEY)
    return len(to_update)


@transaction.atomic
def bulk_delete_artists(ids: list) -> int:
    slugs = list(Artist.objects.filter(pk__in=ids).values_list("slug", flat=True))
    deleted, _ = Artist.objects.filter(pk__in=ids).delete()
    for slug in slugs:
        cache.delete(f"artists:detail:{slug}")
    cache.delete(FEATURED_KEY)
    return deleted


def update_cached_counts(artist_id: int) -> None:
    try:
        artist = Artist.objects.get(pk=artist_id)
    except Artist.DoesNotExist:
        return
    artist.release_count = artist.releases.count()
    artist.video_count = artist.videos.count()
    artist.save(update_fields=["release_count", "video_count"])


@transaction.atomic
def create_release(artist: Artist, validated_data: dict) -> Release:
    # Unlike Artist/PodcastEpisode, Release has no save()-time slug auto-generation and no
    # blank/default — an unset slug would store as "" and collide on the unique constraint the
    # moment a second release (of any artist) was created through this endpoint.
    if not validated_data.get("slug"):
        from core.utils import make_slug

        validated_data["slug"] = make_slug(validated_data["title"], Release)
    release = Release.objects.create(artist=artist, **validated_data)
    update_cached_counts(artist.pk)
    _invalidate_artist_cache(artist)
    return release


@transaction.atomic
def update_release(release: Release, validated_data: dict) -> Release:
    for attr, value in validated_data.items():
        setattr(release, attr, value)
    release.save()
    _invalidate_artist_cache(release.artist)
    return release


@transaction.atomic
def delete_release(release: Release) -> None:
    artist = release.artist
    release.delete()
    update_cached_counts(artist.pk)
    _invalidate_artist_cache(artist)


@transaction.atomic
def create_video(artist: Artist, validated_data: dict) -> ArtistVideo:
    video = ArtistVideo.objects.create(artist=artist, **validated_data)
    update_cached_counts(artist.pk)
    _invalidate_artist_cache(artist)
    return video


@transaction.atomic
def update_video(video: ArtistVideo, validated_data: dict) -> ArtistVideo:
    for attr, value in validated_data.items():
        setattr(video, attr, value)
    video.save()
    _invalidate_artist_cache(video.artist)
    return video


@transaction.atomic
def delete_video(video: ArtistVideo) -> None:
    artist = video.artist
    video.delete()
    update_cached_counts(artist.pk)
    _invalidate_artist_cache(artist)


@transaction.atomic
def create_photo(artist: Artist, validated_data: dict) -> ArtistPhoto:
    photo = ArtistPhoto.objects.create(artist=artist, **validated_data)
    _invalidate_artist_cache(artist)
    return photo


@transaction.atomic
def update_photo(photo: ArtistPhoto, validated_data: dict) -> ArtistPhoto:
    for attr, value in validated_data.items():
        setattr(photo, attr, value)
    photo.save()
    _invalidate_artist_cache(photo.artist)
    return photo


@transaction.atomic
def delete_photo(photo: ArtistPhoto) -> None:
    artist = photo.artist
    photo.delete()
    _invalidate_artist_cache(artist)
