from django.utils import timezone

from . import client


def start_live_input(name: str, existing_uid: str = "") -> dict:
    """Creates a Cloudflare Stream live input and returns the CloudflareLiveFields values.

    Pass `existing_uid` (the resource's current cf_live_input_uid, if any) to make repeated
    go_live calls idempotent — without this, a double-click or client retry creates a second
    live input while the first keeps running and being billed with no remaining DB reference.
    """
    if existing_uid:
        stop_live_input(existing_uid)
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
