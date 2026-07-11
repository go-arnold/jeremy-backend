from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser


@database_sync_to_async
def _get_user_from_token(token: str):
    from django.contrib.auth import get_user_model
    from rest_framework_simplejwt.tokens import AccessToken

    try:
        access = AccessToken(token)
        return get_user_model().objects.get(pk=access["user_id"])
    except Exception:
        return AnonymousUser()


class JWTAuthMiddleware:
    """Authenticates WebSocket connections from a `?token=<access token>` query param.

    Browsers can't set custom headers on a WebSocket handshake, so the JWT access
    token travels as a query param instead of the usual `Authorization: Bearer` header.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        token = parse_qs(query_string).get("token", [None])[0]
        scope["user"] = await _get_user_from_token(token) if token else AnonymousUser()
        return await self.app(scope, receive, send)
