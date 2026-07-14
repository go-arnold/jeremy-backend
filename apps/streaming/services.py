from django.utils import timezone

from . import client


def start_live_input(name: str, existing_uid: str = "") -> dict:
    """Creates a Cloudflare Stream live input and returns the CloudflareLiveFields values.

    Pass `existing_uid` (the resource's current cf_live_input_uid, if any) to make repeated
    go_live calls idempotent. If that live input still exists on Cloudflare, its existing
    credentials are reused as-is — calling go_live again while a broadcaster is already
    connected must NOT tear down their active stream. A new live input is only created when
    there's no existing one, or Cloudflare confirms the old one is gone (e.g. expired).
    """
    if existing_uid:
        existing = client.get_live_input(existing_uid)
        # A live input in Cloudflare's "errored" state (corrupted/malformed) is permanently
        # broken — reusing it would hand the broadcaster credentials that can never connect.
        # Fall through to create a fresh one instead; any other state (idle/disconnected/
        # connected) is safe to reuse as-is.
        state = (existing or {}).get("status", {}).get("current", {}).get("state")
        if existing is not None and state != "errored":
            hls_url, dash_url = client.build_playback_urls(existing_uid)
            rtmps = existing.get("rtmps", {})
            return {
                "cf_live_input_uid": existing_uid,
                "cf_rtmps_url": rtmps.get("url", ""),
                "cf_rtmps_key": rtmps.get("streamKey", ""),
                "cf_playback_hls_url": hls_url,
                "cf_playback_dash_url": dash_url,
            }

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
