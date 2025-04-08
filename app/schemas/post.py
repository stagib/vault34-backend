from pydantic import BaseModel
from datetime import datetime

from app.types import ReactionType


class PostBase(BaseModel):
    id: int
    sample_url: str
    preview_url: str


class PostResponse(BaseModel):
    id: int
    date_created: datetime
    post_id: int
    preview_url: str
    sample_url: str
    file_url: str
    owner: str
    rating: str
    tags: str
    score: int
    likes: int
    dislikes: int
    user_reaction: ReactionType = ReactionType.NONE
    post_score: float


class PostCreate(BaseModel):
    post_id: int
    preview_url: str
    sample_url: str
    file_url: str
    owner: str
    rating: str
    tags: str
    source: str
    score: int
    embedding: list[float]
