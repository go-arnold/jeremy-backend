"""Reusable OpenAPI example building blocks (drf_spectacular.utils.OpenApiExample).

Before this, no view anywhere declared a real `examples=`, so drf-spectacular fell back to
generic auto-guessed placeholders ("string", 0, "http://example.com"...) for every request/
response body in Swagger UI — accurate for the field *types*, but not helpful for anything with
real structure (guests, media items, live-stream credentials...). Small fragments live here so
the same realistic shape isn't retyped across every app that needs it.
"""

from drf_spectacular.utils import OpenApiExample

GUEST_EXAMPLE = {
    "guests": [
        {"name": "Aline Mwamba", "artist_id": 12, "user_id": None},
        {"name": "Invité surprise", "artist_id": None, "user_id": None},
    ]
}

MEDIA_ITEM_EXAMPLE = [
    {"type": "image", "url": "https://res.cloudinary.com/artdukivu/image/upload/v1721581234/sample.jpg"}
]


def live_stream_response_example(media_type="audio"):
    key = f"{media_type}_3f9a1c2b7e4d5f60a1b2c3d4e5f60718"
    return OpenApiExample(
        "Diffusion démarrée",
        value={
            "is_live": True,
            "rtmp_server_url": "rtmp://art-du-kivu-api.kelor.tech:1935/live",
            "stream_key": key,
            "playback_hls_url": f"https://art-du-kivu-api.kelor.tech/live-hls/processed/{key}/index.m3u8",
        },
        response_only=True,
    )


def end_live_response_example():
    return OpenApiExample(
        "Diffusion terminée",
        value={"is_live": False},
        response_only=True,
    )
