import secrets

from django.utils import timezone

from . import client


def start_live_input(name: str, existing_key: str = "") -> dict:
    """Returns the LiveStreamFields values for a broadcast — reuses `existing_key` as-is if
    given (repeated go_live calls must not force the broadcaster to reconfigure OBS, and must
    not reset `live_started_at`), otherwise generates a fresh one.

    Unlike Cloudflare Stream, MediaMTX has no server-side "live input" object that can end up
    in a broken remote state — a path is just a name, valid the moment something (or nothing)
    publishes to it. There is nothing to fetch/validate here, only a key to keep or generate.
    """
    stream_key = existing_key or secrets.token_hex(16)
    fields = {
        "stream_key": stream_key,
        "playback_hls_url": client.build_playback_url(stream_key),
    }
    if not existing_key:
        fields["live_started_at"] = timezone.now()
    return fields


def stop_live_input(stream_key: str) -> None:
    if stream_key:
        client.kick_publisher(stream_key)
