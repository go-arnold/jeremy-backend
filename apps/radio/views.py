from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.realtime import presence
from core.pagination import SmallPagination
from core.permissions import IsAdminOrReadOnly, IsOwnerOrAdmin
from core.serializers import BulkDeleteSerializer
from core.throttling import ChatRateThrottle, UploadThrottleMixin

from . import services
from .models import RadioChat, RadioProgram

# Radio is one continuous channel (not per-program) — presence/chat all share this room id.
from .serializers import (
    RadioChatSerializer,
    RadioProgramBulkCreateSerializer,
    RadioProgramBulkUpdateSerializer,
    RadioProgramSerializer,
    RadioProgramWriteSerializer,
)

RADIO_ROOM_ID = "live"


@extend_schema(tags=["Radio"])
@extend_schema_view(
    create=extend_schema(
        examples=[
            OpenApiExample(
                "Nouvelle émission radio",
                value={
                    "title": "Matinale du Kivu",
                    "description": "L'actualité et la musique pour bien démarrer la journée.",
                    "cover": "https://res.cloudinary.com/artdukivu/image/upload/v1721581234/radio/covers/matinale.jpg",
                    "start_time": "07:00:00",
                    "end_time": "09:00:00",
                    "day_of_week": 0,
                    "presenter": "Jean-Marc",
                },
                request_only=True,
            )
        ]
    )
)
class RadioProgramViewSet(UploadThrottleMixin, ModelViewSet):
    queryset = RadioProgram.objects.all()
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = "id"

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return RadioProgramWriteSerializer
        return RadioProgramSerializer

    def get_queryset(self):
        qs = RadioProgram.objects.all().order_by("day_of_week", "start_time")
        day = self.request.query_params.get("day")
        if day is not None:
            qs = qs.filter(day_of_week=day)
        return qs

    def perform_create(self, serializer):
        serializer.instance = services.create_program(dict(serializer.validated_data))

    def perform_update(self, serializer):
        serializer.instance = services.update_program(serializer.instance, dict(serializer.validated_data))

    def perform_destroy(self, instance):
        services.delete_program(instance)

    @extend_schema(
        examples=[
            OpenApiExample(
                "Diffusion démarrée",
                value={
                    "status": "live",
                    "rtmp_server_url": "rtmp://art-du-kivu-api.kelor.tech:1935/live",
                    "stream_key": "audio_3f9a1c2b7e4d5f60a1b2c3d4e5f60718",
                    "playback_hls_url": "https://art-du-kivu-api.kelor.tech/live-hls/processed/audio_3f9a1c2b7e4d5f60a1b2c3d4e5f60718/index.m3u8",
                },
                response_only=True,
                description="stream_key change à chaque appel — jamais réutilisé d'une diffusion à l'autre.",
            )
        ]
    )
    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def go_live(self, request, id=None):
        program = services.start_live(self.get_object())
        return Response(
            {
                "status": program.status,
                "rtmp_server_url": settings.MEDIAMTX_RTMP_SERVER_URL,
                "stream_key": program.stream_key,
                "playback_hls_url": program.playback_hls_url,
            }
        )

    @extend_schema(
        examples=[OpenApiExample("Diffusion terminée", value={"status": "ended"}, response_only=True)]
    )
    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def end_live(self, request, id=None):
        program = services.end_live(self.get_object())
        return Response({"status": program.status})

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def bulk_create(self, request):
        ser = RadioProgramBulkCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        created = services.bulk_create_programs(ser.validated_data["items"])
        return Response(
            {"created": len(created), "items": RadioProgramSerializer(created, many=True).data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def bulk_update(self, request):
        ser = RadioProgramBulkUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        count = services.bulk_update_programs(ser.validated_data["items"])
        return Response({"updated": count})

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def bulk_delete(self, request):
        ser = BulkDeleteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        count = services.bulk_delete_programs(ser.validated_data["ids"])
        return Response({"deleted": count})


@extend_schema(tags=["Radio"])
@extend_schema_view(
    create=extend_schema(
        examples=[
            OpenApiExample(
                "Nouveau message", value={"content": "Super émission aujourd'hui !"}, request_only=True
            )
        ]
    )
)
class RadioChatViewSet(ModelViewSet):
    pagination_class = SmallPagination
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self):
        return RadioChat.objects.filter(is_deleted=False).select_related("user").order_by("-created_at")[:50]

    def get_serializer_class(self):
        return RadioChatSerializer

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated()]
        if self.action == "destroy":
            return [IsOwnerOrAdmin()]
        return [permissions.AllowAny()]

    def get_throttles(self):
        if self.action == "create":
            return [ChatRateThrottle()] + super().get_throttles()
        return super().get_throttles()

    def perform_create(self, serializer):
        chat = serializer.save(user=self.request.user)
        async_to_sync(get_channel_layer().group_send)(
            f"live.radio.{RADIO_ROOM_ID}",
            {"type": "chat.message", "message": self.get_serializer(chat).data},
        )

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=["is_deleted"])


@extend_schema(tags=["Radio"], responses=RadioProgramSerializer)
@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def current_program(request):
    # Not cache_page'd (unlike other list endpoints) — listener_count below is a live
    # presence read, so caching the response would freeze it for the cache TTL.
    # localtime() matters here: day_of_week/start_time/end_time are local values
    # (Africa/Lubumbashi), while timezone.now() is UTC.
    now = timezone.localtime(timezone.now())
    current_day = now.weekday()
    current_time = now.time()

    program = RadioProgram.objects.filter(
        status=RadioProgram.STATUS_LIVE,
        day_of_week=current_day,
        start_time__lte=current_time,
        end_time__gte=current_time,
    ).first()

    if not program:
        program = (
            RadioProgram.objects.filter(
                day_of_week=current_day,
                start_time__lte=current_time,
            )
            .order_by("-start_time")
            .first()
        )

    if not program:
        return Response({"detail": "Aucun programme en cours."}, status=status.HTTP_404_NOT_FOUND)
    data = RadioProgramSerializer(program).data
    data["listener_count"] = presence.count("radio", RADIO_ROOM_ID)
    return Response(data)
