import json
import os

import redis.asyncio as redis

_redis_client: redis.Redis | None = None
DEFAULT_REDIS_PORT = 6380
DEFAULT_HISTORY_TTL_SECONDS = 7200
DEFAULT_MAX_MESSAGES = 6
SESSION_KEY_PREFIX = "conversation"


def _build_azure_redis_url() -> str:
    host = os.environ["AZURE_REDIS_HOST"]
    password = os.environ["AZURE_REDIS_PASSWORD"]
    port = int(os.environ.get("AZURE_REDIS_PORT", DEFAULT_REDIS_PORT))

    return f"rediss://:{password}@{host}:{port}/0"


def get_redis() -> redis.Redis:
    global _redis_client

    if _redis_client is None:
        _redis_client = redis.from_url(
            _build_azure_redis_url(),
            encoding="utf-8",
            decode_responses=True,
        )

    return _redis_client


def _session_key(conversation_id: str) -> str:
    return f"{SESSION_KEY_PREFIX}:{conversation_id}"


async def get_history(conversation_id: str) -> list[dict]:
    """Get conversation history from Azure Cache for Redis."""
    items = await get_redis().lrange(_session_key(conversation_id), 0, -1)
    return [json.loads(item) for item in items]


async def append_turn(conversation_id: str, user_msg: str, assistant_msg: str) -> None:
    """Persist the latest turns in Azure Cache for Redis."""
    key = _session_key(conversation_id)
    ttl_seconds = int(os.environ.get("AZURE_REDIS_HISTORY_TTL_SECONDS", DEFAULT_HISTORY_TTL_SECONDS))
    client = get_redis()

    await client.rpush(
        key,
        json.dumps({"role": "user", "content": user_msg}),
        json.dumps({"role": "assistant", "content": assistant_msg}),
    )
    await client.ltrim(key, -DEFAULT_MAX_MESSAGES, -1)
    await client.expire(key, ttl_seconds)
