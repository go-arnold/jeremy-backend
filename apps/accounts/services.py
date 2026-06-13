from django.contrib.auth import get_user_model
from django.db import transaction

from apps.artists.models import Artist

User = get_user_model()


def toggle_favorite_artist(user: User, artist: Artist) -> dict:
    """Add or remove an artist from user's favorites. Returns action taken."""
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
