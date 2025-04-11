from pydantic import BaseModel

from app.types import ReactionType


class ReactionBase(BaseModel):
    type: ReactionType


class ReactionResponse(BaseModel):
    type: ReactionType
    likes: int
    dislikes: int
