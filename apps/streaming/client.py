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
