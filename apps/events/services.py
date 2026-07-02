from django.core.cache import cache
from django.db import transaction

from .models import Event, EventRegistration

FEATURED_KEY = "events:featured"
CITIES_KEY = "events:cities"


@transaction.atomic
def create_event(validated_data: dict) -> Event:
    data = dict(validated_data)
    artists = data.pop("artists", [])
    event = Event.objects.create(**data)
    if artists:
        event.artists.set(artists)
    _invalidate()
    return event


@transaction.atomic
def update_event(event: Event, validated_data: dict) -> Event:
    data = dict(validated_data)
    artists = data.pop("artists", None)
    for attr, value in data.items():
        setattr(event, attr, value)
    event.save()
    if artists is not None:
        event.artists.set(artists)
    _invalidate()
    return event


@transaction.atomic
def delete_event(event: Event) -> None:
    _invalidate()
    event.delete()


@transaction.atomic
def register_for_event(event: Event, user) -> dict:
    if event.max_capacity and event.current_registrations >= event.max_capacity:
        return {"error": "full"}
    _, created = EventRegistration.objects.get_or_create(event=event, user=user)
    if not created:
        return {"error": "already_registered"}
    Event.objects.filter(pk=event.pk).update(current_registrations=event.current_registrations + 1)
    return {"ok": True}


@transaction.atomic
def bulk_create_events(items: list) -> list:
    from core.utils import gen_unique_slug

    used: set = set()
    artist_map = []
    objs = []
    for data in items:
        d = dict(data)
        artists = d.pop("artists", [])
        artist_map.append(artists)
        if not d.get("slug"):
            d["slug"] = gen_unique_slug(d["title"], Event, used)
        objs.append(Event(**d))
    created = Event.objects.bulk_create(objs, batch_size=500)
    Through = Event.artists.through
    m2m = [Through(event=ev, artist=a) for ev, artists in zip(created, artist_map) for a in artists]
    if m2m:
        Through.objects.bulk_create(m2m, batch_size=500, ignore_conflicts=True)
    _invalidate()
    return created


@transaction.atomic
def bulk_update_events(items: list) -> int:
    ids = [d["id"] for d in items]
    obj_map = {o.pk: o for o in Event.objects.filter(pk__in=ids)}
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
        Event.objects.bulk_update(to_update, list(fields), batch_size=500)
    _invalidate()
    return len(to_update)


@transaction.atomic
def bulk_delete_events(ids: list) -> int:
    deleted, _ = Event.objects.filter(pk__in=ids).delete()
    _invalidate()
    return deleted


def _invalidate() -> None:
    cache.delete(FEATURED_KEY)
    cache.delete(CITIES_KEY)
