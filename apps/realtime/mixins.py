from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.contenttypes.models import ContentType
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from core.pagination import SmallPagination

from . import presence
from .models import LiveChatMessage
from .serializers import LiveChatMessageSerializer


class LiveChatViewSetMixin:
    """Mounts GET/POST `chat` + GET `online-count` actions on a live-surface ViewSet.

    Set `chat_room_type` on the ViewSet (e.g. "webtv", "live_music") — it's the
    `room_type` half of the WebSocket group `live.<room_type>.<object id>` that
    apps.realtime.consumers.LiveRoomConsumer relays messages/presence over.
    """

    chat_room_type = None

    @action(detail=True, methods=["get", "post"], permission_classes=[permissions.IsAuthenticatedOrReadOnly])
    def chat(self, request, *args, **kwargs):
        instance = self.get_object()
        content_type = ContentType.objects.get_for_model(instance)

        if request.method == "GET":
            qs = (
                LiveChatMessage.objects.filter(
                    content_type=content_type, object_id=instance.pk, is_deleted=False
                )
                .select_related("author")
                .order_by("-created_at")
            )
            paginator = SmallPagination()
            page = paginator.paginate_queryset(qs, request, view=self)
            return paginator.get_paginated_response(LiveChatMessageSerializer(page, many=True).data)

        message = str(request.data.get("message", "")).strip()
        if not message:
            return Response({"detail": "Message vide."}, status=status.HTTP_400_BAD_REQUEST)

        chat_message = LiveChatMessage.objects.create(
            content_type=content_type, object_id=instance.pk, author=request.user, message=message[:500]
        )
        data = LiveChatMessageSerializer(chat_message).data
        group_name = f"live.{self.chat_room_type}.{instance.pk}"
        async_to_sync(get_channel_layer().group_send)(group_name, {"type": "chat.message", "message": data})
        return Response(data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="online-count")
    def online_count(self, request, *args, **kwargs):
        instance = self.get_object()
        return Response({"online_count": presence.count(self.chat_room_type, str(instance.pk))})
