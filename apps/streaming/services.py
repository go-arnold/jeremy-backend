from django.utils import timezone

from . import client


def start_live_input(name: str) -> dict:
    """Creates a Cloudflare Stream live input and returns the CloudflareLiveFields values."""
    result = client.create_live_input(name)
    hls_url, dash_url = client.build_playback_urls(result["uid"])
    rtmps = result.get("rtmps", {})
    return {
        "cf_live_input_uid": result["uid"],
        "cf_rtmps_url": rtmps.get("url", ""),
        "cf_rtmps_key": rtmps.get("streamKey", ""),
        "cf_playback_hls_url": hls_url,
        "cf_playback_dash_url": dash_url,
        "live_started_at": timezone.now(),
    }


def stop_live_input(uid: str) -> None:
    if uid:
        client.delete_live_input(uid)
