import requests
from django.conf import settings

BASE_URL = "https://api.cloudflare.com/client/v4"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json",
    }


def _live_inputs_url(suffix: str = "") -> str:
    return f"{BASE_URL}/accounts/{settings.CLOUDFLARE_ACCOUNT_ID}/stream/live_inputs{suffix}"


def create_live_input(name: str) -> dict:
    response = requests.post(
        _live_inputs_url(),
        json={"meta": {"name": name}, "recording": {"mode": "automatic"}},
        headers=_headers(),
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["result"]


def get_live_input(uid: str) -> dict:
    response = requests.get(_live_inputs_url(f"/{uid}"), headers=_headers(), timeout=10)
    response.raise_for_status()
    return response.json()["result"]


def delete_live_input(uid: str) -> None:
    response = requests.delete(_live_inputs_url(f"/{uid}"), headers=_headers(), timeout=10)
    if response.status_code not in (200, 204, 404):
        response.raise_for_status()


def build_playback_urls(uid: str) -> tuple[str, str]:
    host = settings.CLOUDFLARE_CUSTOMER_HOSTNAME
    return (
        f"https://{host}/{uid}/manifest/video.m3u8",
        f"https://{host}/{uid}/manifest/video.mpd",
    )
