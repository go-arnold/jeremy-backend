import glob
import logging
import os

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

# Grace period after go_live before the poll is allowed to flip status back to "not live". Without
# this, a broadcaster who takes a few seconds to actually start pushing (opening OBS, clicking
# "Start Streaming") would see their status flicker live -> ended -> live within the first tick.
GRACE_PERIOD_SECONDS = 45

# Matches docs/*/mediamtx.yml's recordPath ("/recordings/%path/...") for the
# "~^processed/live/(.+)$" pattern — %path resolves to "processed/live/<stream_key>".
RECORDINGS_ROOT = "/recordings/processed/live"


@shared_task(queue="default")
def sync_live_status() -> None:
    """Reconciles each broadcasting model's live status against MediaMTX's own view of which
    stream_keys are actually being published to right now.

    Replaces a push-based webhook (MediaMTX's official image has no shell to run
    runOnReady/runOnNotReady hooks — see apps.streaming.client.list_ready_stream_keys) with a
    short-interval poll — see CELERY_BEAT_SCHEDULE (`sync-live-status`, every 15s).
    """
    from . import client

    ready_keys = client.list_ready_stream_keys()
    if ready_keys is None:
        return  # MediaMTX API unreachable this tick — try again next tick, don't guess.

    from apps.emissions.models import Emission
    from apps.live_music.models import MusicLiveSession
    from apps.radio.models import RadioProgram
    from apps.webtv.models import WebTVVideo

    cutoff = timezone.now() - timezone.timedelta(seconds=GRACE_PERIOD_SECONDS)

    status_models = [
        (Emission, Emission.STATUS_LIVE, Emission.STATUS_RECORDED),
        (RadioProgram, RadioProgram.STATUS_LIVE, RadioProgram.STATUS_ENDED),
        (MusicLiveSession, MusicLiveSession.STATUS_LIVE, MusicLiveSession.STATUS_ENDED),
    ]
    for model, live_value, ended_value in status_models:
        for obj in model.objects.exclude(stream_key="").only("pk", "stream_key", "status", "live_started_at"):
            is_ready = obj.stream_key in ready_keys
            if is_ready and obj.status != live_value:
                obj.status = live_value
                obj.save(update_fields=["status"])
            elif (
                not is_ready
                and obj.status == live_value
                and obj.live_started_at is not None
                and obj.live_started_at < cutoff
            ):
                obj.status = ended_value
                obj.save(update_fields=["status"])

    for video in WebTVVideo.objects.exclude(stream_key="").only(
        "pk", "stream_key", "is_live", "live_started_at"
    ):
        is_ready = video.stream_key in ready_keys
        if is_ready and not video.is_live:
            video.is_live = True
            video.save(update_fields=["is_live"])
        elif (
            not is_ready
            and video.is_live
            and video.live_started_at is not None
            and video.live_started_at < cutoff
        ):
            video.is_live = False
            video.save(update_fields=["is_live"])


@shared_task(queue="default", bind=True, max_retries=1, default_retry_delay=15)
def finalize_live_recording(
    self,
    app_label: str,
    model_name: str,
    object_id: int,
    stream_key: str,
    url_field: str = "video_url",
) -> None:
    """Uploads the MediaMTX recording of a just-ended live broadcast to Cloudinary and turns the
    row that was live into a normal playable VOD (sets `<url_field>` + `recording_status`).

    `url_field` differs per app because each model already had its own naming before this task
    existed: `video_url` for Web TV/Emissions, `audio_url` for Radio/Live Music.

    Triggered from `end_live()` for Web TV (camera mode only) and Emissions/Radio/Live Music
    (always, since those have no playout concept) — a playout broadcast is already a saved video,
    nothing to record for that case. Relies entirely on docs/*/mediamtx.yml's `record` config on
    the "processed/live/" path pattern to have actually produced the file this reads; there is no
    other producer of `/recordings/...`.
    """
    import cloudinary.uploader
    from django.apps import apps as django_apps

    model = django_apps.get_model(app_label, model_name)
    obj = model.objects.filter(pk=object_id).first()
    if obj is None:
        return  # deleted before we got to finalize it — nothing to do

    pattern = os.path.join(RECORDINGS_ROOT, stream_key, "*.mp4")
    matches = sorted(glob.glob(pattern))
    if not matches:
        # A fresh recording always has at least one open/flushed segment within a few seconds of
        # the stream ending — one retry covers MediaMTX not having flushed it to disk yet. If it's
        # still missing after that, recording never actually started (nothing left to wait for).
        if self.request.retries < self.max_retries:
            raise self.retry()
        logger.error("finalize_live_recording: no recording file for stream_key=%s", stream_key)
        obj.recording_status = model.RECORDING_FAILED
        obj.save(update_fields=["recording_status"])
        return

    path = matches[-1]
    try:
        result = cloudinary.uploader.upload_large(
            path, resource_type="video", folder=f"{app_label}/recordings"
        )
    except Exception:
        logger.exception("finalize_live_recording: Cloudinary upload failed for %s", path)
        obj.recording_status = model.RECORDING_FAILED
        obj.save(update_fields=["recording_status"])
        return

    setattr(obj, url_field, result["secure_url"])
    obj.recording_status = model.RECORDING_READY
    obj.save(update_fields=[url_field, "recording_status"])

    try:
        os.remove(path)
    except OSError:
        logger.warning("finalize_live_recording: could not delete local file %s", path)
