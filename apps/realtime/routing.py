from django.urls import re_path

from .consumers import LiveRoomConsumer

# The only real live surfaces — restricting the URL pattern to these (rather than accepting any
# \w+ string) stops a client from minting arbitrary presence/group namespaces at will.
ROOM_TYPES = ("radio", "live_music", "webtv", "emission")

websocket_urlpatterns = [
    re_path(
        rf"^ws/live/(?P<room_type>{'|'.join(ROOM_TYPES)})/(?P<room_id>[\w-]+)/$",
        LiveRoomConsumer.as_asgi(),
    ),
]
