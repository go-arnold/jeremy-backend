import re

import cloudinary
import cloudinary.api
import cloudinary.exceptions
from rest_framework import serializers

# https://res.cloudinary.com/<cloud>/<resource_type>/upload/[transformations/].../v<version>/<public_id>.<ext>
_CLOUDINARY_URL_RE = re.compile(
    r"^https://res\.cloudinary\.com/(?P<cloud>[^/]+)/(?P<resource_type>image|video|raw)/upload/"
    r"(?:[^/]+/)*?v\d+/(?P<public_id>.+?)(?:\.[a-zA-Z0-9]+)?$"
)


def _extract_public_id(url: str):
    match = _CLOUDINARY_URL_RE.match(url)
    if not match:
        return None
    return match.group("public_id"), match.group("resource_type")


def verify_cloudinary_asset(url: str, expected_resource_type: str) -> None:
    """Strict validation for a media URL: if it claims to be hosted on OUR Cloudinary
    account, confirm it's a real, already-processed asset of the expected type — this is
    what actually validates the binary content (Cloudinary had to decode/transcode it to
    store it), not just the file extension in the URL.

    URLs hosted elsewhere are left alone: we have no way to validate content we don't
    store, and rejecting all non-Cloudinary URLs would break legitimate external references
    (e.g. an existing YouTube link) — matching today's behavior for those.
    """
    prefix = f"https://res.cloudinary.com/{cloudinary.config().cloud_name}/"
    if not url.startswith(prefix):
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
