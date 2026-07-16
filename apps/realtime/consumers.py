from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from . import presence
from .presence import GLOBAL_PRESENCE_ROOM_TYPE


class LiveRoomConsumer(AsyncJsonWebsocketConsumer):
    """One room per live surface: ws/live/<room_type>/<room_id>/

    Handles presence (join/heartbeat/leave -> online count) and relays chat
    messages pushed server-side from the REST chat endpoint. Anonymous
    connections are accepted so "online followers" counts every viewer, not
    just logged-in ones; posting a chat message still requires auth via REST.
    """

    async def connect(self):
        self.room_type = self.scope["url_route"]["kwargs"]["room_type"]
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.group_name = f"live.{self.room_type}.{self.room_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await sync_to_async(presence.join)(self.room_type, self.room_id, self.channel_name)
        await self._touch_global_presence(presence.join)
        await self._broadcast_count()

    async def disconnect(self, close_code):
        await sync_to_async(presence.leave)(self.room_type, self.room_id, self.channel_name)
        await self._touch_global_presence(presence.leave)
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        await self._broadcast_count()

    async def receive_json(self, content, **kwargs):
        if content.get("type") == "heartbeat":
            await sync_to_async(presence.heartbeat)(self.room_type, self.room_id, self.channel_name)
            await self._touch_global_presence(presence.heartbeat)

    async def _touch_global_presence(self, fn) -> None:
        user = self.scope.get("user")
        if user is not None and user.is_authenticated:
            await sync_to_async(fn)(GLOBAL_PRESENCE_ROOM_TYPE, str(user.id), self.channel_name)

    async def _broadcast_count(self):
        online_count = await sync_to_async(presence.count)(self.room_type, self.room_id)
        await self.channel_layer.group_send(
            self.group_name, {"type": "presence.count", "count": online_count}
        )

    async def presence_count(self, event):
        await self.send_json({"event": "presence.count", "count": event["count"]})

    async def chat_message(self, event):
        await self.send_json({"event": "chat.message", "message": event["message"]})
