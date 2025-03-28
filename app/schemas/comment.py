from pydantic import BaseModel, Field
from datetime import datetime

from app.types import ReactionType
from app.schemas import UserBase


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=500)


class CommentResponse(BaseModel):
    id: int
    post_id: int
    date_created: datetime
    content: str
    likes: int
    dislikes: int
    user_reaction: ReactionType = ReactionType.NONE
    user: UserBase
