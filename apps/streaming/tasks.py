from celery import shared_task
from django.utils import timezone

# Grace period after go_live before the poll is allowed to flip status back to "not live". Without
# this, a broadcaster who takes a few seconds to actually start pushing (opening OBS, clicking
# "Start Streaming") would see their status flicker live -> ended -> live within the first tick.
GRACE_PERIOD_SECONDS = 45


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
