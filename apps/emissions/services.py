from django.core.cache import cache
from django.db import transaction

from apps.streaming import services as streaming_services

from .models import Emission

LIVE_KEY = "emissions:live"


def get_live_emission():
    # cache.delete(LIVE_KEY) calls throughout this file only invalidate something because this
    # is the same key used to populate it — @cache_page (used by the view previously) stores
    # under its own internal hashed key, unreachable via cache.delete(LIVE_KEY). The short TTL
    # here also self-heals the case where apps.emissions.tasks.update_emission_statuses flips a
    # status via a bulk .update() that bypasses this cache entirely.
    cached = cache.get(LIVE_KEY)
    if cached is not None:
        return cached
    emission = Emission.objects.filter(status=Emission.STATUS_LIVE).first()
    if emission is not None:
        cache.set(LIVE_KEY, emission, 60)
    return emission


@transaction.atomic
def start_live(emission: Emission) -> Emission:
    fields = streaming_services.start_live_input(emission.title, media_type="audio")
    for attr, value in fields.items():
        setattr(emission, attr, value)
    emission.status = Emission.STATUS_LIVE
    emission.save()
    cache.delete(LIVE_KEY)
    return emission


@transaction.atomic
def end_live(emission: Emission) -> Emission:
    stream_key = emission.stream_key
    streaming_services.stop_live_input(stream_key)
    emission.status = Emission.STATUS_RECORDED
    emission.stream_key = ""
    # Emissions have no playout/camera distinction (see WebTVVideo) — every emission broadcast
    # is a real live feed, so it's always recorded, unconditionally.
    emission.recording_status = Emission.RECORDING_PENDING
    emission.save()
    cache.delete(LIVE_KEY)

    from apps.streaming.tasks import finalize_live_recording

    finalize_live_recording.delay("emissions", "Emission", emission.pk, stream_key)

    return emission


@transaction.atomic
def create_emission(validated_data: dict) -> Emission:
    data = dict(validated_data)
    hosts = data.pop("hosts", [])
    emission = Emission.objects.create(**data)
    if hosts:
        emission.hosts.set(hosts)
    cache.delete(LIVE_KEY)
    return emission


@transaction.atomic
def update_emission(emission: Emission, validated_data: dict) -> Emission:
    data = dict(validated_data)
    hosts = data.pop("hosts", None)
    for attr, value in data.items():
        setattr(emission, attr, value)
    emission.save()
    if hosts is not None:
        emission.hosts.set(hosts)
    cache.delete(LIVE_KEY)
    return emission


@transaction.atomic
def delete_emission(emission: Emission) -> None:
    cache.delete(LIVE_KEY)
    emission.delete()


@transaction.atomic
def bulk_create_emissions(items: list) -> list:
    from core.utils import gen_unique_slug

    used: set = set()
    host_map = []
    objs = []
    for data in items:
        d = dict(data)
        hosts = d.pop("hosts", [])
        host_map.append(hosts)
        if not d.get("slug"):
            d["slug"] = gen_unique_slug(d["title"], Emission, used)
        objs.append(Emission(**d))
    created = Emission.objects.bulk_create(objs, batch_size=500)
    Through = Emission.hosts.through
    m2m = [Through(emission=em, artist=h) for em, hosts in zip(created, host_map) for h in hosts]
    if m2m:
        Through.objects.bulk_create(m2m, batch_size=500, ignore_conflicts=True)
    cache.delete(LIVE_KEY)
    return created


@transaction.atomic
def bulk_update_emissions(items: list) -> int:
    ids = [d["id"] for d in items]
    obj_map = {o.pk: o for o in Emission.objects.filter(pk__in=ids)}
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
        Emission.objects.bulk_update(to_update, list(fields), batch_size=500)
    cache.delete(LIVE_KEY)
    return len(to_update)


@transaction.atomic
def bulk_delete_emissions(ids: list) -> int:
    deleted, _ = Emission.objects.filter(pk__in=ids).delete()
    cache.delete(LIVE_KEY)
    return deleted
