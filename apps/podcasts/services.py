from collections import Counter

from django.db import transaction
from django.db.models import Case, F, IntegerField, Value, When

from .models import PodcastEpisode, PodcastSeries


@transaction.atomic
def create_series(validated_data: dict) -> PodcastSeries:
    return PodcastSeries.objects.create(**validated_data)


@transaction.atomic
def update_series(series: PodcastSeries, validated_data: dict) -> PodcastSeries:
    for attr, value in validated_data.items():
        setattr(series, attr, value)
    series.save()
    return series


@transaction.atomic
def delete_series(series: PodcastSeries) -> None:
    series.delete()


@transaction.atomic
def bulk_create_series(items: list) -> list:
    from core.utils import gen_unique_slug

    used: set = set()
    objs = []
    for data in items:
        d = dict(data)
        if not d.get("slug"):
            d["slug"] = gen_unique_slug(d["title"], PodcastSeries, used)
        objs.append(PodcastSeries(**d))
    return PodcastSeries.objects.bulk_create(objs, batch_size=500)


@transaction.atomic
def bulk_update_series(items: list) -> int:
    ids = [d["id"] for d in items]
    obj_map = {o.pk: o for o in PodcastSeries.objects.filter(pk__in=ids)}
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
        PodcastSeries.objects.bulk_update(to_update, list(fields), batch_size=500)
    return len(to_update)


@transaction.atomic
def bulk_delete_series(ids: list) -> int:
    deleted, _ = PodcastSeries.objects.filter(pk__in=ids).delete()
    return deleted


@transaction.atomic
def create_episode(validated_data: dict) -> PodcastEpisode:
    episode = PodcastEpisode.objects.create(**validated_data)
    PodcastSeries.objects.filter(pk=episode.series_id).update(episode_count=F("episode_count") + 1)
    return episode


@transaction.atomic
def update_episode(episode: PodcastEpisode, validated_data: dict) -> PodcastEpisode:
    for attr, value in validated_data.items():
        setattr(episode, attr, value)
    episode.save()
    return episode


@transaction.atomic
def delete_episode(episode: PodcastEpisode) -> None:
    series_id = episode.series_id
    episode.delete()
    PodcastSeries.objects.filter(pk=series_id).update(episode_count=F("episode_count") - 1)


@transaction.atomic
def bulk_create_episodes(items: list) -> list:
    from core.utils import gen_unique_slug

    used: set = set()
    objs = []
    for data in items:
        d = dict(data)
        if not d.get("slug"):
            d["slug"] = gen_unique_slug(d["title"], PodcastEpisode, used)
        objs.append(PodcastEpisode(**d))
    created = PodcastEpisode.objects.bulk_create(objs, batch_size=500)
    counts = Counter(e.series_id for e in created)
    if counts:
        PodcastSeries.objects.filter(pk__in=counts.keys()).update(
            episode_count=F("episode_count")
            + Case(
                *[When(pk=sid, then=Value(cnt)) for sid, cnt in counts.items()],
                output_field=IntegerField(),
            )
        )
    return created


@transaction.atomic
def bulk_update_episodes(items: list) -> int:
    ids = [d["id"] for d in items]
    obj_map = {o.pk: o for o in PodcastEpisode.objects.filter(pk__in=ids)}
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
        PodcastEpisode.objects.bulk_update(to_update, list(fields), batch_size=500)
    return len(to_update)


@transaction.atomic
def bulk_delete_episodes(ids: list) -> int:
    counts = Counter(PodcastEpisode.objects.filter(pk__in=ids).values_list("series_id", flat=True))
    deleted, _ = PodcastEpisode.objects.filter(pk__in=ids).delete()
    if counts:
        PodcastSeries.objects.filter(pk__in=counts.keys()).update(
            episode_count=F("episode_count")
            - Case(
                *[When(pk=sid, then=Value(cnt)) for sid, cnt in counts.items()],
                output_field=IntegerField(),
            )
        )
    return deleted
