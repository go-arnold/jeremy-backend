from django.core.cache import cache
from django.db import transaction

from apps.streaming import services as streaming_services

from .models import MusicLiveSession, MusicLiveSlot

CURRENT_KEY = "live_music:current"


@transaction.atomic
def create_session(validated_data: dict) -> MusicLiveSession:
    data = dict(validated_data)
    artists = data.pop("artists", [])
    session = MusicLiveSession.objects.create(**data)
    if artists:
        session.artists.set(artists)
    cache.delete(CURRENT_KEY)
    return session


@transaction.atomic
def update_session(session: MusicLiveSession, validated_data: dict) -> MusicLiveSession:
    data = dict(validated_data)
    artists = data.pop("artists", None)
    for attr, value in data.items():
        setattr(session, attr, value)
    session.save()
    if artists is not None:
        session.artists.set(artists)
    cache.delete(CURRENT_KEY)
    return session


@transaction.atomic
def delete_session(session: MusicLiveSession) -> None:
    cache.delete(CURRENT_KEY)
    session.delete()


@transaction.atomic
def start_live(session: MusicLiveSession) -> MusicLiveSession:
    fields = streaming_services.start_live_input(session.title, media_type="audio")
    for attr, value in fields.items():
        setattr(session, attr, value)
    session.status = MusicLiveSession.STATUS_LIVE
    session.save()
    cache.delete(CURRENT_KEY)
    return session


@transaction.atomic
def end_live(session: MusicLiveSession) -> MusicLiveSession:
    stream_key = session.stream_key
    streaming_services.stop_live_input(stream_key)
    session.status = MusicLiveSession.STATUS_ENDED
    session.stream_key = ""
    session.recording_status = MusicLiveSession.RECORDING_PENDING
    session.save()
    cache.delete(CURRENT_KEY)

    from apps.streaming.tasks import finalize_live_recording

    finalize_live_recording.delay(
        "live_music", "MusicLiveSession", session.pk, stream_key, url_field="audio_url"
    )

    return session


@transaction.atomic
def create_slot(validated_data: dict) -> MusicLiveSlot:
    return MusicLiveSlot.objects.create(**validated_data)


@transaction.atomic
def update_slot(slot: MusicLiveSlot, validated_data: dict) -> MusicLiveSlot:
    for attr, value in validated_data.items():
        setattr(slot, attr, value)
    slot.save()
    return slot


@transaction.atomic
def delete_slot(slot: MusicLiveSlot) -> None:
    slot.delete()
