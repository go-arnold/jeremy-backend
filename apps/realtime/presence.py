import time

import redis
from django.conf import settings

# A connection counts as "online" if it heartbeated within this window. The
# client is expected to ping roughly every 15s, so 30s tolerates one missed beat.
PRESENCE_TTL_SECONDS = 30

# Connects straight to REDIS_URL rather than going through django_redis's cache
# backend: settings/local.py swaps CACHES to LocMemCache for local dev (no local
# Redis needed for caching), but Celery — and now presence — still talk to the
# real (Aiven) Redis directly, same as CHANNEL_LAYERS does.
_client: redis.Redis | None = None


def _get_client() -> redis.Redis:
    global _client
    if _client is None:
        kwargs = {"decode_responses": True}
        if settings.REDIS_URL.startswith("rediss://"):
            kwargs["ssl_cert_reqs"] = None
        _client = redis.from_url(settings.REDIS_URL, **kwargs)
    return _client


def _key(room_type: str, room_id: str) -> str:
    return f"presence:{room_type}:{room_id}"


def join(room_type: str, room_id: str, member_id: str) -> None:
    _get_client().zadd(_key(room_type, room_id), {member_id: time.time()})


def heartbeat(room_type: str, room_id: str, member_id: str) -> None:
    join(room_type, room_id, member_id)


def leave(room_type: str, room_id: str, member_id: str) -> None:
    _get_client().zrem(_key(room_type, room_id), member_id)


def count(room_type: str, room_id: str) -> int:
    conn = _get_client()
    key = _key(room_type, room_id)
    cutoff = time.time() - PRESENCE_TTL_SECONDS
    conn.zremrangebyscore(key, "-inf", cutoff)
    return conn.zcard(key)
