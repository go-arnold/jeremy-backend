import time

import cloudinary
import cloudinary.utils

# Whitelist of upload contexts the frontend can request a signature for — deliberately
# closed rather than letting the client pick any resource_type/folder, so a regular user
# can't, say, get a signature to write into "artists/covers". `staff_only=False` contexts
# are the ones any authenticated user may use (community submissions, their own avatar).
UPLOAD_CONTEXTS = {
    "webtv_video": {"resource_type": "video", "folder": "webtv/videos", "staff_only": True},
    "webtv_thumbnail": {"resource_type": "image", "folder": "webtv/thumbnails", "staff_only": True},
    "podcast_audio": {"resource_type": "video", "folder": "podcasts/audio", "staff_only": True},
    "podcast_cover": {"resource_type": "image", "folder": "podcasts/covers", "staff_only": True},
    "release_cover": {"resource_type": "image", "folder": "releases/covers", "staff_only": True},
    "release_preview": {"resource_type": "video", "folder": "releases/previews", "staff_only": True},
    "artist_photo": {"resource_type": "image", "folder": "artists/photos", "staff_only": True},
    "artist_cover": {"resource_type": "image", "folder": "artists/covers", "staff_only": True},
    "artist_gallery_photo": {"resource_type": "image", "folder": "artists/gallery", "staff_only": True},
    "emission_cover": {"resource_type": "image", "folder": "emissions/covers", "staff_only": True},
    "radio_cover": {"resource_type": "image", "folder": "radio/covers", "staff_only": True},
    "challenge_cover": {"resource_type": "image", "folder": "community/challenges", "staff_only": True},
    "community_image": {"resource_type": "image", "folder": "community/posts", "staff_only": False},
    "community_video": {"resource_type": "video", "folder": "community/posts", "staff_only": False},
    "community_song": {"resource_type": "video", "folder": "community/posts", "staff_only": False},
    "user_avatar": {"resource_type": "image", "folder": "users/avatars", "staff_only": False},
    "user_cover": {"resource_type": "image", "folder": "users/covers", "staff_only": False},
}

# Cloudinary treats anything with a time dimension (audio included) as "video" — using this
# resource type (rather than "raw") is what makes Cloudinary actually decode/transcode the
# upload, which is what gives us real binary validation and automatic duration extraction,
# instead of just storing opaque bytes as-is.


def build_signature(folder: str, resource_type: str) -> dict:
    """Signed params for the frontend to upload DIRECTLY to Cloudinary — the file's bytes
    never pass through our server, keeping large video/audio uploads fast and off our VPS."""
    config = cloudinary.config()
    timestamp = int(time.time())
    params_to_sign = {"timestamp": timestamp, "folder": folder}
    signature = cloudinary.utils.api_sign_request(params_to_sign, config.api_secret)
    return {
        "timestamp": timestamp,
        "signature": signature,
        "api_key": config.api_key,
        "cloud_name": config.cloud_name,
        "folder": folder,
        "resource_type": resource_type,
        "upload_url": f"https://api.cloudinary.com/v1_1/{config.cloud_name}/{resource_type}/upload",
    }
