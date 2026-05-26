from fastapi import APIRouter

from app.services.session import get_redis

router = APIRouter()


@router.get("/health")
async def health():
    """Health check endpoint with Azure Cache for Redis connectivity test."""
    checks = {}

    try:
        await get_redis().ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    return {"status": "ok", "checks": checks}
