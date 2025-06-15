from datetime import datetime

from pydantic import BaseModel
from typing import Optional

from app.types import ReactionType


class PostBase(BaseModel):
    id: int
    sample_url: str
    preview_url: str
    type: str


class PostResponse(BaseModel):
    id: int
    date_created: datetime
    preview_url: str
    sample_url: str
    file_url: str
    source: str
    title: str
    top_tags: list[str]
    rating: str
    type: str
    likes: int
    dislikes: int
    user_reaction: ReactionType = ReactionType.NONE
    last_updated: datetime


class PostCreate(BaseModel):
    post_id: int
    preview_url: str
    sample_url: str
    file_url: str
    owner: str
    rating: str
    tags: str
    source: str
    score: Optional[int] = 0
    embedding: list[float]
    type: str
