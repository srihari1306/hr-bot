from fastapi import APIRouter
from app.models.schemas import FeedbackRequest
import logging

router = APIRouter()
logger = logging.getLogger("feedback")


@router.post("/feedback")
async def feedback(request: FeedbackRequest):
    """Log feedback. Local dev: console log. Production: Table Storage / App Insights."""
    logger.info(
        "FEEDBACK | conv=%s turn=%s rating=%s comment=%s",
        request.conversation_id,
        request.turn_id,
        request.rating,
        request.comment or ""
    )
    return {"status": "ok"}
