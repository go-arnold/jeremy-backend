from django.urls import re_path

from .consumers import LiveRoomConsumer

websocket_urlpatterns = [
    re_path(r"^ws/live/(?P<room_type>\w+)/(?P<room_id>[\w-]+)/$", LiveRoomConsumer.as_asgi()),
]
