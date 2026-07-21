from drf_spectacular.utils import OpenApiExample, extend_schema, inline_serializer
from rest_framework import permissions, serializers, status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response

from core.throttling import UploadRateThrottle

from . import services


@extend_schema(
    tags=["Media"],
    request=inline_serializer("UploadSignatureRequest", fields={"context": serializers.CharField()}),
    responses=inline_serializer(
        "UploadSignatureResponse",
        fields={
            "signature": serializers.CharField(),
            "timestamp": serializers.IntegerField(),
            "api_key": serializers.CharField(),
            "cloud_name": serializers.CharField(),
            "folder": serializers.CharField(),
            "resource_type": serializers.CharField(),
            "upload_url": serializers.CharField(),
        },
    ),
    examples=[
        OpenApiExample("Contexte", value={"context": "artist_gallery_photo"}, request_only=True),
        OpenApiExample(
            "Paramètres signés",
            value={
                "signature": "9c1f8e2a...",
                "timestamp": 1721581234,
                "api_key": "123456789012345",
                "cloud_name": "artdukivu",
                "folder": "artists/gallery",
                "resource_type": "image",
                "upload_url": "https://api.cloudinary.com/v1_1/artdukivu/image/upload",
            },
            response_only=True,
        ),
    ],
)
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
@throttle_classes([UploadRateThrottle])
def upload_signature(request):
    """Issues signed params for a direct-to-Cloudinary upload — the frontend POSTs the
    actual file straight to Cloudinary's `upload_url` using these params, never through
    this API. See apps.media_uploads.services.UPLOAD_CONTEXTS for the allowed contexts."""
    context = request.data.get("context")
    config = services.UPLOAD_CONTEXTS.get(context)
    if config is None:
        return Response(
            {"detail": "Contexte d'upload inconnu.", "code": "invalid_context"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if config["staff_only"] and not request.user.is_staff:
        return Response(
            {"detail": "Ce type d'upload est réservé aux administrateurs.", "code": "forbidden_context"},
            status=status.HTTP_403_FORBIDDEN,
        )
    return Response(services.build_signature(config["folder"], config["resource_type"]))
