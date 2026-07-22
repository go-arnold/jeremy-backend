import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def build_playback_url(stream_key: str) -> str:
    # Served from "processed/live/<key>", not "live/<key>" — the raw ingest path is
    # transcode-input only (see mediamtx.yml's runOnReady ffmpeg hooks); viewers always get the
    # re-encoded, quality/bitrate-controlled copy ffmpeg republishes under "processed/".
    #
    # The extra "live/" segment is not a typo: MediaMTX's $MTX_PATH hook variable is the FULL
    # matched path ("live/<key>"), not just the captured key, and shell parameter expansion
    # (${MTX_PATH#live/}) to strip it turned out not to survive however MediaMTX actually invokes
    # runOnReady (confirmed live: the processed/ path stopped being created at all once that
    # expansion was introduced) — so the plain, proven-working `$MTX_PATH` substitution is used
    # in mediamtx.yml, and this URL matches the path it naturally produces instead of fighting it.
    return f"{settings.MEDIAMTX_HLS_BASE_URL}/processed/live/{stream_key}/index.m3u8"


def kick_publisher(stream_key: str) -> None:
    """Best-effort force-disconnect of an active publisher via MediaMTX's HTTP API. Never
    raises: there may be no active publisher (nothing to kick), or the API may be briefly
    unreachable — either way `end_live` must still succeed on our own DB state.

    Kicks both the raw ingest path and its ffmpeg-republished "processed/live/<key>" copy, so
    ending a broadcast fully tears down both instead of leaving the processed path registered
    after its source vanishes (a contributor to the "stale stream repeats" bug — see
    start_live_input)."""
    for path in (f"live/{stream_key}", f"processed/live/{stream_key}"):
        try:
            response = requests.post(f"{settings.MEDIAMTX_API_URL}/v3/paths/kick/{path}", timeout=5)
            # Confirmed live: MediaMTX's API rejected this with a 401 for weeks without a single
            # visible error anywhere, because nothing checked the response — the broadcaster kept
            # running for 9+ minutes past `end_live` while our own DB already said "not live".
            # Still never raises (this is best-effort — there may genuinely be no active
            # publisher, a 404 here is normal), just makes an actual failure visible in logs.
            if response.status_code >= 400 and response.status_code != 404:
                logger.warning(
                    "kick_publisher: MediaMTX rejected kick for path=%s status=%s body=%s",
                    path,
                    response.status_code,
                    response.text[:200],
                )
        except requests.RequestException:
            logger.warning("kick_publisher: request failed for path=%s", path)


def list_ready_stream_keys():
    """Stream keys currently actively being published to, per MediaMTX's own API.

    The official MediaMTX image is `FROM scratch` — no shell, no curl/wget — so it cannot run
    `runOnReady`/`runOnNotReady` shell hooks to push status changes to us. Polling this API from
    a Celery beat task instead needs nothing inside the MediaMTX container at all; it only
    depends on MediaMTX's own built-in HTTP API server, which every image (including scratch)
    serves natively.

    Returns None (not an empty set) if the API call itself failed, so callers can tell "nothing
    is live" apart from "couldn't check" — treating a transient MediaMTX/network hiccup as
    universal silence would flip every currently-live resource to ended.
    """
    try:
        response = requests.get(f"{settings.MEDIAMTX_API_URL}/v3/paths/list", timeout=5)
        response.raise_for_status()
    except requests.RequestException:
        return None
    items = response.json().get("items", [])
    return {
        item["name"].removeprefix("live/")
        for item in items
        if item.get("ready") and item.get("name", "").startswith("live/")
    }
