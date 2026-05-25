from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    message: str
    conversation_id: str
    user_id: str = "local-dev-user"   # hardcoded for local dev; replaced by JWT claim in prod


class FeedbackRequest(BaseModel):
    conversation_id: str
    turn_id: str
    rating: str   # "up" | "down"
    comment: Optional[str] = None


class Citation(BaseModel):
    heading: str
    url: str


class ChatMetadata(BaseModel):
    citations: list[Citation]
    suggested_questions: list[str]
    turn_id: str
