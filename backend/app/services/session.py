import json
import os
import redis.asyncio as redis

_redis = None


def get_redis():
    global _redis
    if not _redis:
        _redis = redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379"))
    return _redis


async def get_history(conversation_id: str) -> list[dict]:
    """Get conversation history from Redis. Returns empty list if Redis unavailable."""
    try:
        r = get_redis()
        data = await r.get(f"session:{conversation_id}")
        if data:
            return json.loads(data)
        return []
    except Exception:
        return []   # Redis unavailable → zero-turn context, don't crash


async def append_turn(conversation_id: str, user_msg: str, assistant_msg: str):
    """Append a conversation turn to Redis. Silent fail if Redis unavailable."""
    try:
        r = get_redis()
        history = await get_history(conversation_id)
        history.append({"role": "user", "content": user_msg})
        history.append({"role": "assistant", "content": assistant_msg})
        history = history[-6:]   # keep last 3 turns (6 messages)
        await r.setex(
            f"session:{conversation_id}",
            7200,   # 2 hour TTL
            json.dumps(history)
        )
    except Exception:
        pass   # Redis unavailable → silent fail
