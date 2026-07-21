from django.contrib.auth import get_user_model
from django.db import transaction

from apps.artists.models import Artist

User = get_user_model()


def toggle_favorite_artist(user: User, artist: Artist) -> dict:
    favorites = user.favorite_artists
    if favorites.filter(pk=artist.pk).exists():
        favorites.remove(artist)
        return {"action": "removed", "artist_id": artist.id}
    favorites.add(artist)
    return {"action": "added", "artist_id": artist.id}


def get_user_favorites(user: User):
    return user.favorite_artists.only("id", "name", "slug", "photo").order_by("name")


@transaction.atomic
def update_user_profile(user: User, validated_data: dict) -> User:
    for attr, value in validated_data.items():
        setattr(user, attr, value)
    user.save(update_fields=list(validated_data.keys()) + ["updated_at"])
    return user


@transaction.atomic
def create_user_admin(validated_data: dict) -> User:
    password = validated_data.pop("password")
    # Admin-created accounts skip the self-signup email-verification flow entirely, so default
    # to already-verified unless the admin explicitly says otherwise.
    validated_data.setdefault("is_verified", True)
    user = User(**validated_data)
    user.set_password(password)
    user.save()
    return user


@transaction.atomic
def bulk_update_users(items: list) -> int:
    ids = [d["id"] for d in items]
    obj_map = {o.pk: o for o in User.objects.filter(pk__in=ids)}
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
        User.objects.bulk_update(to_update, list(fields), batch_size=500)
    return len(to_update)


@transaction.atomic
def bulk_delete_users(ids: list) -> int:
    deleted, _ = User.objects.filter(pk__in=ids).delete()
    return deleted
