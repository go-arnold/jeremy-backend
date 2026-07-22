from django.core.cache import cache
from django.db import transaction

from apps.streaming import services as streaming_services

from .models import WebTVVideo

PREMIERS_KEY = "webtv:premiers"


def get_premiers(limit: int = 5) -> list:
    # cache.delete(PREMIERS_KEY) below only invalidates something because this is the same key
    # used to populate it — @cache_page (used by the view previously) stores under its own
    # internal hashed key, unreachable via cache.delete(PREMIERS_KEY).
    cached = cache.get(PREMIERS_KEY)
    if cached is not None:
        return cached
    videos = list(WebTVVideo.objects.filter(is_premier=True).order_by("-published_at")[:limit])
    cache.set(PREMIERS_KEY, videos, 60 * 15)
    return videos


@transaction.atomic
def start_live(video: WebTVVideo) -> WebTVVideo:
    fields = streaming_services.start_live_input(video.title, media_type="video")
    for attr, value in fields.items():
        setattr(video, attr, value)
    video.is_live = True
    video.save()

    if video.broadcast_mode == WebTVVideo.MODE_PLAYOUT:
        # Server pushes the already-uploaded file into the same "live/<key>" path a real OBS
        # broadcast would use — the existing runOnReady transcode hook picks it up identically,
        # no separate code path needed downstream (chat/is_live/HLS all behave the same).
        from .tasks import run_playout_stream

        result = run_playout_stream.delay(video.pk, video.stream_key, video.video_url)
        WebTVVideo.objects.filter(pk=video.pk).update(playout_task_id=result.id)
        video.playout_task_id = result.id

    return video


@transaction.atomic
def end_live(video: WebTVVideo) -> WebTVVideo:
    was_camera_mode = video.broadcast_mode == WebTVVideo.MODE_CAMERA
    stream_key = video.stream_key

    if video.playout_task_id:
        from artdukivu.celery import app as celery_app

        celery_app.control.revoke(video.playout_task_id, terminate=True, signal="SIGTERM")
        video.playout_task_id = ""

    streaming_services.stop_live_input(stream_key)
    video.is_live = False
    video.stream_key = ""

    if was_camera_mode:
        # A playout broadcast is already a saved video — nothing to record. A real camera
        # broadcast just ended: capture what MediaMTX recorded and turn it into a normal VOD.
        video.recording_status = WebTVVideo.RECORDING_PENDING

    video.save()

    if was_camera_mode:
        from apps.streaming.tasks import finalize_live_recording

        finalize_live_recording.delay("webtv", "WebTVVideo", video.pk, stream_key)

    return video


@transaction.atomic
def create_video(validated_data: dict) -> WebTVVideo:
    data = dict(validated_data)
    artists = data.pop("artists", [])
    video = WebTVVideo.objects.create(**data)
    if artists:
        video.artists.set(artists)
    cache.delete(PREMIERS_KEY)
    return video


@transaction.atomic
def update_video(video: WebTVVideo, validated_data: dict) -> WebTVVideo:
    data = dict(validated_data)
    artists = data.pop("artists", None)
    for attr, value in data.items():
        setattr(video, attr, value)
    video.save()
    if artists is not None:
        video.artists.set(artists)
    cache.delete(PREMIERS_KEY)
    return video


@transaction.atomic
def delete_video(video: WebTVVideo) -> None:
    cache.delete(PREMIERS_KEY)
    video.delete()


@transaction.atomic
def bulk_create_videos(items: list) -> list:
    from core.utils import gen_unique_slug

    used: set = set()
    artist_map = []
    objs = []
    for data in items:
        d = dict(data)
        artists = d.pop("artists", [])
        artist_map.append(artists)
        if not d.get("slug"):
            d["slug"] = gen_unique_slug(d["title"], WebTVVideo, used)
        objs.append(WebTVVideo(**d))
    created = WebTVVideo.objects.bulk_create(objs, batch_size=500)
    Through = WebTVVideo.artists.through
    m2m = [Through(webtvvideo=v, artist=a) for v, artists in zip(created, artist_map) for a in artists]
    if m2m:
        Through.objects.bulk_create(m2m, batch_size=500, ignore_conflicts=True)
    cache.delete(PREMIERS_KEY)
    return created


@transaction.atomic
def bulk_update_videos(items: list) -> int:
    ids = [d["id"] for d in items]
    obj_map = {o.pk: o for o in WebTVVideo.objects.filter(pk__in=ids)}
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
        WebTVVideo.objects.bulk_update(to_update, list(fields), batch_size=500)
    cache.delete(PREMIERS_KEY)
    return len(to_update)


@transaction.atomic
def bulk_delete_videos(ids: list) -> int:
    deleted, _ = WebTVVideo.objects.filter(pk__in=ids).delete()
    cache.delete(PREMIERS_KEY)
    return deleted
