from pydantic import BaseModel

from app.types import ReactionType


class ReactionCreate(BaseModel):
    type: ReactionType
