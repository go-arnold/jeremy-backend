"""Adapters turning any FeaturedContent.content_object into the flat
{type, id, slug, title, description, image_url} shape the home page's "Contenus à la Une"
carousel expects — one function per supported model (see models.FEATURABLE_APP_MODELS)."""

from apps.media_uploads.fields import resolve_cloudinary_url


def _artist(obj):
    return {
        "type": "artist",
        "id": obj.pk,
        "slug": obj.slug,
        "title": obj.name,
        "description": obj.bio,
        "image_url": resolve_cloudinary_url(obj.photo, "image"),
    }


def _emission(obj):
    return {
        "type": "emission",
        "id": obj.pk,
        "slug": obj.slug,
        "title": obj.title,
        "description": obj.description,
        "image_url": resolve_cloudinary_url(obj.cover, "image"),
    }


def _radio_program(obj):
    return {
        "type": "radio",
        "id": obj.pk,
        "slug": obj.slug,
        "title": obj.title,
        "description": obj.description,
        "image_url": resolve_cloudinary_url(obj.cover, "image"),
    }


def _webtv_video(obj):
    return {
        "type": "webtv",
        "id": obj.pk,
        "slug": obj.slug,
        "title": obj.title,
        "description": obj.description,
        "image_url": resolve_cloudinary_url(obj.thumbnail, "image"),
    }


def _live_music_session(obj):
    return {
        "type": "live_music",
        "id": obj.pk,
        "slug": obj.slug,
        "title": obj.title,
        "description": "",  # MusicLiveSession has no description field
        "image_url": resolve_cloudinary_url(obj.cover, "image"),
    }


def _event(obj):
    return {
        "type": "event",
        "id": obj.pk,
        "slug": obj.slug,
        "title": obj.title,
        "description": obj.description,
        "image_url": resolve_cloudinary_url(obj.image, "image"),
    }


def _music_release(obj):
    return {
        "type": "release",
        "id": obj.pk,
        "slug": obj.slug,
        "title": obj.title,
        "description": obj.description,
        "image_url": resolve_cloudinary_url(obj.cover, "image"),
    }


def _article(obj):
    return {
        "type": "article",
        "id": obj.pk,
        "slug": obj.slug,
        "title": obj.title,
        "description": obj.excerpt,
        "image_url": resolve_cloudinary_url(obj.featured_image, "image"),
    }


def _podcast_episode(obj):
    return {
        "type": "podcast",
        "id": obj.pk,
        "slug": obj.slug,
        "title": obj.title,
        "description": obj.description,
        # PodcastEpisode has no cover of its own — falls back to its series' cover.
        "image_url": resolve_cloudinary_url(obj.series.cover, "image"),
    }


_ADAPTERS = {
    "Artist": _artist,
    "Emission": _emission,
    "RadioProgram": _radio_program,
    "WebTVVideo": _webtv_video,
    "MusicLiveSession": _live_music_session,
    "Event": _event,
    "MusicRelease": _music_release,
    "Article": _article,
    "PodcastEpisode": _podcast_episode,
}


def serialize_featured_content(obj) -> dict | None:
    """Returns None if `obj` isn't one of the supported types — the caller should skip it
    rather than error, since FEATURABLE_APP_MODELS is meant to keep this from happening in
    practice, but a model rename/removal shouldn't be able to break the whole home payload."""
    adapter = _ADAPTERS.get(type(obj).__name__)
    return adapter(obj) if adapter else None
