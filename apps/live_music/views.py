from django.conf import settings
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.engagement.mixins import EngagementActionsMixin
from apps.realtime.mixins import LiveChatViewSetMixin
from core.permissions import IsAdminOrReadOnly

from . import services
from .models import MusicLiveSession, MusicLiveSlot
from .serializers import (
    MusicLiveSessionSerializer,
    MusicLiveSessionWriteSerializer,
    MusicLiveSlotSerializer,
    MusicLiveSlotWriteSerializer,
)


@extend_schema(tags=["Live Music"])
@extend_schema_view(
    create=extend_schema(
        examples=[
            OpenApiExample(
                "Nouvelle session live",
                value={
                    "title": "Session acoustique en direct",
                    "cover": "https://res.cloudinary.com/artdukivu/image/upload/v1721581234/live_music/covers/session.jpg",
                    "artists": [4, 9],
                },
                request_only=True,
            )
        ]
    )
)
class MusicLiveSessionViewSet(EngagementActionsMixin, LiveChatViewSetMixin, ModelViewSet):
    queryset = MusicLiveSession.objects.prefetch_related("artists")
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = "slug"
    chat_room_type = "live_music"

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return MusicLiveSessionWriteSerializer
        return MusicLiveSessionSerializer

    def perform_create(self, serializer):
        serializer.instance = services.create_session(dict(serializer.validated_data))

    def perform_update(self, serializer):
        serializer.instance = services.update_session(serializer.instance, dict(serializer.validated_data))

    def perform_destroy(self, instance):
        services.delete_session(instance)

    @action(detail=False, methods=["get"])
    def current(self, request):
        session = MusicLiveSession.objects.filter(status=MusicLiveSession.STATUS_LIVE).first()
        if not session:
            return Response({"detail": "Aucun son en direct actuellement."}, status=status.HTTP_404_NOT_FOUND)
        return Response(MusicLiveSessionSerializer(session).data)

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
    def go_live(self, request, slug=None):
        session = services.start_live(self.get_object())
        return Response(
            {
                "status": session.status,
                "rtmp_server_url": settings.MEDIAMTX_RTMP_SERVER_URL,
                "stream_key": session.stream_key,
                "playback_hls_url": session.playback_hls_url,
            }
        )

    @extend_schema(
        examples=[OpenApiExample("Diffusion terminée", value={"status": "ended"}, response_only=True)]
    )
    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def end_live(self, request, slug=None):
        session = services.end_live(self.get_object())
        return Response({"status": session.status})


@extend_schema(tags=["Live Music"])
@extend_schema_view(
    create=extend_schema(
        examples=[
            OpenApiExample(
                "Nouveau créneau",
                value={
                    "title": "Créneau vendredi soir",
                    "artist": 4,
                    "day_of_week": 5,
                    "start_time": "20:00:00",
                    "end_time": "22:00:00",
                },
                request_only=True,
            )
        ]
    )
)
class MusicLiveSlotViewSet(ModelViewSet):
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        qs = MusicLiveSlot.objects.select_related("artist").order_by("day_of_week", "start_time")
        day = self.request.query_params.get("day")
        if day is not None:
            qs = qs.filter(day_of_week=day)
        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return MusicLiveSlotWriteSerializer
        return MusicLiveSlotSerializer

    def perform_create(self, serializer):
        serializer.instance = services.create_slot(dict(serializer.validated_data))

    def perform_update(self, serializer):
        serializer.instance = services.update_slot(serializer.instance, dict(serializer.validated_data))

    def perform_destroy(self, instance):
        services.delete_slot(instance)
