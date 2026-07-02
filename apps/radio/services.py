from django.core.cache import cache
from django.db import transaction

from .models import RadioProgram

CURRENT_KEY = "radio:current"


@transaction.atomic
def create_program(validated_data: dict) -> RadioProgram:
    program = RadioProgram.objects.create(**validated_data)
    cache.delete(CURRENT_KEY)
    return program


@transaction.atomic
def update_program(program: RadioProgram, validated_data: dict) -> RadioProgram:
    for attr, value in validated_data.items():
        setattr(program, attr, value)
    program.save()
    cache.delete(CURRENT_KEY)
    return program


@transaction.atomic
def delete_program(program: RadioProgram) -> None:
    cache.delete(CURRENT_KEY)
    program.delete()


@transaction.atomic
def bulk_create_programs(items: list) -> list:
    from core.utils import gen_unique_slug

    used: set = set()
    objs = []
    for data in items:
        d = dict(data)
        if not d.get("slug"):
            d["slug"] = gen_unique_slug(d["title"], RadioProgram, used)
        objs.append(RadioProgram(**d))
    created = RadioProgram.objects.bulk_create(objs, batch_size=500)
    cache.delete(CURRENT_KEY)
    return created


@transaction.atomic
def bulk_update_programs(items: list) -> int:
    ids = [d["id"] for d in items]
    obj_map = {o.pk: o for o in RadioProgram.objects.filter(pk__in=ids)}
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
        RadioProgram.objects.bulk_update(to_update, list(fields), batch_size=500)
    cache.delete(CURRENT_KEY)
    return len(to_update)


@transaction.atomic
def bulk_delete_programs(ids: list) -> int:
    deleted, _ = RadioProgram.objects.filter(pk__in=ids).delete()
    cache.delete(CURRENT_KEY)
    return deleted
