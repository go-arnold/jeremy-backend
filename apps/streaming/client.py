import requests
from django.conf import settings


def build_playback_url(stream_key: str) -> str:
    return f"{settings.MEDIAMTX_HLS_BASE_URL}/live/{stream_key}/index.m3u8"


def kick_publisher(stream_key: str) -> None:
    """Best-effort force-disconnect of an active publisher via MediaMTX's HTTP API. Never
    raises: there may be no active publisher (nothing to kick), or the API may be briefly
    unreachable — either way `end_live` must still succeed on our own DB state."""
    try:
        requests.post(f"{settings.MEDIAMTX_API_URL}/v3/paths/kick/live/{stream_key}", timeout=5)
    except requests.RequestException:
        pass


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
