import secrets

from django.utils import timezone

from . import client


def start_live_input(name: str, media_type: str) -> dict:
    """Returns the LiveStreamFields values for a broadcast — always generates a fresh
    `stream_key`, never reuses one across `go_live` calls. Reusing keys let a MediaMTX path
    registration survive an unclean previous session (browser closed, `end_live` never called)
    and bleed into the next one, reading as a "repeat of the recent stream"; a fresh key every
    time guarantees no stale state can carry over.

    `media_type` ("audio" or "video") is baked into the key itself so MediaMTX's path regexes
    (mediamtx.yml) can route each stream through the right ffmpeg transcode — audio-only
    broadcasts (Radio/Emissions/LiveMusic) strip video and compress for mobile data, video
    broadcasts (WebTV) get a controlled bitrate/resolution ceiling instead of a raw passthrough.

    Unlike Cloudflare Stream, MediaMTX has no server-side "live input" object that can end up
    in a broken remote state — a path is just a name, valid the moment something (or nothing)
    publishes to it. There is nothing to fetch/validate here, only a key to generate.
    """
    stream_key = f"{media_type}_{secrets.token_hex(16)}"
    return {
        "stream_key": stream_key,
        "playback_hls_url": client.build_playback_url(stream_key),
        "live_started_at": timezone.now(),
    }


def stop_live_input(stream_key: str) -> None:
    if stream_key:
        client.kick_publisher(stream_key)
