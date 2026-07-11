from collections import Counter

from django.core.cache import cache
from django.db import transaction
from django.db.models import Case, F, IntegerField, Value, When

from .models import MusicRelease

FEATURED_KEY = "releases:featured"
CALENDAR_KEY = "releases:calendar"


@transaction.atomic
def create_release(validated_data: dict) -> MusicRelease:
    release = MusicRelease.objects.create(**validated_data)
    from apps.artists.models import Artist

    Artist.objects.filter(pk=release.artist_id).update(release_count=F("release_count") + 1)
    _invalidate()
    return release


@transaction.atomic
def update_release(release: MusicRelease, validated_data: dict) -> MusicRelease:
    for attr, value in validated_data.items():
        setattr(release, attr, value)
    release.save()
    _invalidate()
    return release


@transaction.atomic
def delete_release(release: MusicRelease) -> None:
    artist_id = release.artist_id
    _invalidate()
    release.delete()
    from apps.artists.models import Artist

    Artist.objects.filter(pk=artist_id).update(release_count=F("release_count") - 1)


@transaction.atomic
def bulk_create_releases(items: list) -> list:
    from apps.artists.models import Artist
    from core.utils import gen_unique_slug

    used: set = set()
    objs = []
    for data in items:
        d = dict(data)
        if not d.get("slug"):
            artist_pk = d["artist"].pk
            d["slug"] = gen_unique_slug(f"{artist_pk}-{d['title']}", MusicRelease, used)
        objs.append(MusicRelease(**d))
    created = MusicRelease.objects.bulk_create(objs, batch_size=500)
    counts = Counter(r.artist_id for r in created)
    if counts:
        Artist.objects.filter(pk__in=counts.keys()).update(
            release_count=F("release_count")
            + Case(
                *[When(pk=aid, then=Value(cnt)) for aid, cnt in counts.items()],
                output_field=IntegerField(),
            )
        )
    _invalidate()
    return created


@transaction.atomic
def bulk_update_releases(items: list) -> int:
    ids = [d["id"] for d in items]
    obj_map = {o.pk: o for o in MusicRelease.objects.filter(pk__in=ids)}
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
        MusicRelease.objects.bulk_update(to_update, list(fields), batch_size=500)
    _invalidate()
    return len(to_update)


@transaction.atomic
def bulk_delete_releases(ids: list) -> int:
    from apps.artists.models import Artist

    counts = Counter(MusicRelease.objects.filter(pk__in=ids).values_list("artist_id", flat=True))
    deleted, _ = MusicRelease.objects.filter(pk__in=ids).delete()
    if counts:
        Artist.objects.filter(pk__in=counts.keys()).update(
            release_count=F("release_count")
            - Case(
                *[When(pk=aid, then=Value(cnt)) for aid, cnt in counts.items()],
                output_field=IntegerField(),
            )
        )
    _invalidate()
    return deleted


def get_featured_release():
    # cache.delete(FEATURED_KEY) in _invalidate() only actually invalidates something because
    # this key is set here too — @cache_page (used by the view previously) stores under its own
    # internal hashed key, which cache.delete(FEATURED_KEY) can never reach.
    cached = cache.get(FEATURED_KEY)
    if cached is not None:
        return cached
    release = MusicRelease.objects.filter(is_featured=True).select_related("artist").first()
    if release is not None:
        cache.set(FEATURED_KEY, release, 60 * 30)
    return release


def get_upcoming_releases(days: int = 60) -> list:
    cached = cache.get(CALENDAR_KEY)
    if cached is not None:
        return cached
    from datetime import timedelta

    from django.utils import timezone

    today = timezone.now().date()
    end = today + timedelta(days=days)
    releases = list(
        MusicRelease.objects.filter(release_date__gte=today, release_date__lte=end)
        .select_related("artist")
        .order_by("release_date")
    )
    cache.set(CALENDAR_KEY, releases, 60 * 60)
    return releases


def _invalidate() -> None:
    cache.delete(FEATURED_KEY)
    cache.delete(CALENDAR_KEY)
