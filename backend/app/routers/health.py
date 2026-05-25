from fastapi import APIRouter
import redis.asyncio as redis
import os

router = APIRouter()


@router.get("/health")
async def health():
    """Health check endpoint with Redis connectivity test."""
    checks = {}

    # Redis
    try:
        r = redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379"))
        await r.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    return {"status": "ok", "checks": checks}
