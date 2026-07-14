import re
import socket
from ipaddress import ip_address
from urllib.parse import urlparse

import cloudinary
import cloudinary.api
import cloudinary.exceptions
import requests
from rest_framework import serializers

# https://res.cloudinary.com/<cloud>/<resource_type>/upload/[transformations/].../v<version>/<public_id>.<ext>
_CLOUDINARY_URL_RE = re.compile(
    r"^https://res\.cloudinary\.com/(?P<cloud>[^/]+)/(?P<resource_type>image|video|raw)/upload/"
    r"(?:[^/]+/)*?v\d+/(?P<public_id>.+?)(?:\.[a-zA-Z0-9]+)?$"
)

# Known video/audio embed platforms: these are page URLs (not raw media files), so they can
# never pass a Content-Type check — trusted by domain instead, matching how they were always
# meant to be used (e.g. a YouTube link for Web TV, a SoundCloud link for a release preview).
_TRUSTED_EMBED_HOSTS = {
    "youtube.com",
    "youtu.be",
    "vimeo.com",
    "soundcloud.com",
}

# Cloudinary's "video" resource type also covers audio (see the comment in services.py) — a
# remote audio file legitimately reports an audio/* Content-Type, not video/*.
_ALLOWED_CONTENT_TYPE_PREFIXES = {
    "image": ("image/",),
    "video": ("video/", "audio/"),
}


def _extract_public_id(url: str):
    match = _CLOUDINARY_URL_RE.match(url)
    if not match:
        return None
    return match.group("public_id"), match.group("resource_type")


def _is_trusted_embed_host(hostname: str) -> bool:
    hostname = hostname.lower()
    return any(hostname == host or hostname.endswith(f".{host}") for host in _TRUSTED_EMBED_HOSTS)


def _is_public_host(hostname: str) -> bool:
    """Rejects hostnames that resolve to a private/loopback/link-local address, so validating an
    external URL can't be used to make our server probe internal network services (SSRF)."""
    try:
        addresses = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False
    for family, _, _, _, sockaddr in addresses:
        ip = ip_address(sockaddr[0])
        if not ip.is_global:
            return False
    return True


def _verify_external_url(url: str, expected_resource_type: str) -> None:
    """Best-effort strict check for a media URL we don't host ourselves: confirm it resolves to
    a public host (not an SSRF vector) and that the remote server actually declares the expected
    media Content-Type — a real, if lighter, binary-content signal instead of trusting the URL's
    file extension."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise serializers.ValidationError("Seules les URLs http(s) sont acceptées.")

    if _is_trusted_embed_host(parsed.hostname):
        return

    if not _is_public_host(parsed.hostname):
        raise serializers.ValidationError("Cette URL n'est pas accessible depuis nos serveurs.")

    try:
        response = requests.head(url, timeout=5, allow_redirects=True)
        content_type = response.headers.get("Content-Type", "")
        if response.status_code >= 400 or not content_type:
            response = requests.get(url, timeout=5, stream=True, headers={"Range": "bytes=0-0"})
            content_type = response.headers.get("Content-Type", "")
    except requests.RequestException as exc:
        raise serializers.ValidationError(f"Impossible de vérifier cette URL : {exc}") from exc

    if not content_type.lower().startswith(_ALLOWED_CONTENT_TYPE_PREFIXES[expected_resource_type]):
        raise serializers.ValidationError(
            f"Ce champ attend un contenu de type « {expected_resource_type} », le serveur "
            f"distant a répondu « {content_type or 'inconnu'} »."
        )


def verify_cloudinary_asset(url: str, expected_resource_type: str) -> None:
    """Strict validation for a media URL. If it claims to be hosted on OUR Cloudinary account,
    confirm it's a real, already-processed asset of the expected type — this is what actually
    validates the binary content (Cloudinary had to decode/transcode it to store it), not just
    the file extension in the URL.

    URLs hosted elsewhere still get a real check — a live Content-Type lookup against an
    SSRF-guarded host (see `_verify_external_url`) — except for known video/audio embed
    platforms (YouTube, Vimeo, SoundCloud), which are page URLs by nature and are trusted by
    domain instead, so legitimate external references keep working.
    """
    prefix = f"https://res.cloudinary.com/{cloudinary.config().cloud_name}/"
    if not url.startswith(prefix):
        _verify_external_url(url, expected_resource_type)
        return

    parsed = _extract_public_id(url)
    if not parsed:
        raise serializers.ValidationError("URL Cloudinary mal formée.")

    public_id, url_resource_type = parsed
    if url_resource_type != expected_resource_type:
        raise serializers.ValidationError(
            f"Ce champ attend un contenu de type « {expected_resource_type} », pas « {url_resource_type} »."
        )

    try:
        cloudinary.api.resource(public_id, resource_type=expected_resource_type)
    except cloudinary.exceptions.NotFound as exc:
        raise serializers.ValidationError(
            "Aucun média correspondant trouvé sur Cloudinary — vérifiez que l'upload a bien abouti."
        ) from exc
    except cloudinary.exceptions.Error as exc:
        raise serializers.ValidationError(f"Impossible de vérifier ce média : {exc}") from exc


def validate_media_items(items: list) -> None:
    """Applies verify_cloudinary_asset to each {"type": ..., "url": ...} item in a generic
    media list (used by community posts, whose media can be a mix of images/songs/videos).
    Items without a recognized type/url are left untouched — this list's shape is
    intentionally more flexible than a single-purpose field.
    """
    type_to_resource_type = {"image": "image", "video": "video", "song": "video"}
    for item in items:
        if not isinstance(item, dict):
            continue
        resource_type = type_to_resource_type.get(item.get("type"))
        url = item.get("url")
        if resource_type and url:
            verify_cloudinary_asset(url, resource_type)
