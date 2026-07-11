import hashlib
import hmac
import time

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

# How much clock skew / delivery delay to tolerate before treating a webhook as stale. A
# validly-signed payload is otherwise valid forever, letting a captured request be replayed at
# any point in the future to flip a resource's live status on demand.
WEBHOOK_MAX_AGE_SECONDS = 300


def _verify_signature(raw_body: bytes, header_value: str) -> bool:
    if not settings.CLOUDFLARE_WEBHOOK_SECRET or not header_value:
        return False
    parts = dict(item.split("=", 1) for item in header_value.split(",") if "=" in item)
    ts, sig = parts.get("time"), parts.get("sig1")
    if not ts or not sig:
        return False
    try:
        if abs(time.time() - int(ts)) > WEBHOOK_MAX_AGE_SECONDS:
            return False
    except ValueError:
        return False
    expected = hmac.new(
        settings.CLOUDFLARE_WEBHOOK_SECRET.encode(), f"{ts}.".encode() + raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, sig)


@extend_schema(tags=["Streaming"])
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def cloudflare_webhook(request):
    """Receives Cloudflare Stream `live_input.connected`/`live_input.disconnected` events
    and flips the matching Emission/RadioProgram/MusicLiveSession/WebTVVideo's live status."""
    if not _verify_signature(request.body, request.headers.get("Webhook-Signature", "")):
        return Response({"detail": "Signature invalide."}, status=status.HTTP_403_FORBIDDEN)

    payload = request.data
    uid = payload.get("uid") or payload.get("live_input_uid")
    state = (payload.get("status") or {}).get("current", {}).get("state")
    if not uid or not state:
        return Response({"detail": "ignoré — payload incomplet."})

    is_connected = state == "connected"

    from apps.emissions.models import Emission
    from apps.live_music.models import MusicLiveSession
    from apps.radio.models import RadioProgram
    from apps.webtv.models import WebTVVideo

    status_models = [
        (Emission, Emission.STATUS_LIVE, Emission.STATUS_RECORDED),
        (RadioProgram, RadioProgram.STATUS_LIVE, RadioProgram.STATUS_ENDED),
        (MusicLiveSession, MusicLiveSession.STATUS_LIVE, MusicLiveSession.STATUS_ENDED),
    ]
    for model, live_value, ended_value in status_models:
        obj = model.objects.filter(cf_live_input_uid=uid).first()
        if obj:
            obj.status = live_value if is_connected else ended_value
            obj.save(update_fields=["status"])
            return Response({"detail": "mis à jour"})

    video = WebTVVideo.objects.filter(cf_live_input_uid=uid).first()
    if video:
        video.is_live = is_connected
        video.save(update_fields=["is_live"])
        return Response({"detail": "mis à jour"})

    return Response({"detail": "aucune ressource live correspondante"}, status=status.HTTP_404_NOT_FOUND)
