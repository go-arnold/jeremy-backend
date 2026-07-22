import signal
import subprocess

from celery import shared_task
from django.db.models import F


@shared_task(queue="default")
def async_increment_view(video_id: int) -> None:
    from .models import WebTVVideo

    WebTVVideo.objects.filter(pk=video_id).update(view_count=F("view_count") + 1)


# Generous ceiling for any realistic video duration — a safety net against a runaway process,
# not an expected normal duration. soft_time_limit fires first (lets the finally/cleanup below
# run via SIGTERM -> our handler), time_limit is the hard kill if that somehow doesn't work.
_PLAYOUT_TIME_LIMIT = 4 * 3600


@shared_task(queue="default", time_limit=_PLAYOUT_TIME_LIMIT, soft_time_limit=_PLAYOUT_TIME_LIMIT - 30)
def run_playout_stream(video_id: int, stream_key: str, video_url: str) -> None:
    """Pushes an already-uploaded video file into the live pipeline, so a "playout" broadcast
    (apps.webtv.models.WebTVVideo.MODE_PLAYOUT) appears exactly like a real OBS broadcast —
    same "live/<key>" ingest path, same runOnReady transcode hook, same HLS/chat/is_live
    behavior — without anyone needing to run OBS.

    Blocks for the whole video duration (a Celery worker slot is occupied the entire time — see
    the worker concurrency bump in docker-compose.yaml). Ends the broadcast automatically when
    the video finishes playing; `end_live()` revoking this task's id (SIGTERM, see the handler
    below) is what happens when an admin ends it manually instead.
    """
    # Always re-encode rather than -c copy: FLV/RTMP only carries H.264 video + AAC audio at
    # 44100/22050/11025 Hz — an uploaded file can be anything Cloudinary accepts (AV1/Opus webm,
    # HEVC, whatever), and stream-copying a codec FLV can't hold fails outright ("Conversion
    # failed!", confirmed live). Re-encoding here also means this never has to assume anything
    # about the source's format.
    process = subprocess.Popen(
        [
            "ffmpeg",
            "-re",
            "-i",
            video_url,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "44100",
            "-b:a",
            "128k",
            "-f",
            "flv",
            f"rtmp://mediamtx:1935/live/{stream_key}",
        ]
    )

    def _handle_terminate(signum, frame):
        # Default SIGTERM handling kills this process immediately without running any cleanup —
        # install our own so the ffmpeg child is actually terminated instead of orphaned when
        # end_live() revokes this task.
        process.terminate()
        raise SystemExit(0)

    previous_handler = signal.signal(signal.SIGTERM, _handle_terminate)
    try:
        process.wait()
    finally:
        signal.signal(signal.SIGTERM, previous_handler)
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()

    # Natural exit (video reached its end) — flip is_live back off automatically, same as a
    # manual end_live() would. If an admin already called end_live() (which revokes/terminates
    # this task), the video is already non-live by the time we'd get here — the extra guard on
    # is_live/stream_key below makes this a no-op in that case instead of a duplicate state flip.
    from . import services
    from .models import WebTVVideo

    video = WebTVVideo.objects.filter(pk=video_id, is_live=True, stream_key=stream_key).first()
    if video:
        services.end_live(video)
