import hmac

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response


@extend_schema(tags=["Streaming"])
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def mediamtx_webhook(request):
    """Receives MediaMTX's `runOnReady`/`runOnNotReady` hook calls and flips the matching
    Emission/RadioProgram/MusicLiveSession/WebTVVideo's live status.

    Unlike the old Cloudflare webhook, this never touches the public internet — MediaMTX and
    this API share a private Docker Compose network, so a shared secret is sufficient (no
    HMAC/timestamp scheme needed, there's no third party's request to authenticate)."""
    secret = settings.MEDIAMTX_WEBHOOK_SECRET
    if not secret or not hmac.compare_digest(request.headers.get("X-Internal-Secret", ""), secret):
        return Response({"detail": "Secret invalide."}, status=status.HTTP_403_FORBIDDEN)

    stream_key = request.data.get("path", "")
    event = request.data.get("event", "")
    if not stream_key or event not in ("ready", "not_ready"):
        return Response({"detail": "ignoré — payload incomplet."})

    is_live = event == "ready"

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
        obj = model.objects.filter(stream_key=stream_key).first()
        if obj:
            obj.status = live_value if is_live else ended_value
            obj.save(update_fields=["status"])
            return Response({"detail": "mis à jour"})

    video = WebTVVideo.objects.filter(stream_key=stream_key).first()
    if video:
        video.is_live = is_live
        video.save(update_fields=["is_live"])
        return Response({"detail": "mis à jour"})

    return Response({"detail": "aucune ressource live correspondante"}, status=status.HTTP_404_NOT_FOUND)
