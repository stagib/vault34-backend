from datetime import datetime

from pydantic import BaseModel, Field
from typing import Optional

from app.schemas.post import PostBase, PostResponse
from app.schemas.user import UserBase
from app.types import PrivacyType, ReactionType


class VaultPostBase(BaseModel):
    id: int
    vault_id: int
    index: int
    post: PostBase


class EntryResponse(BaseModel):
    id: int
    total: int
    post: PostResponse


class VaultBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=30)
    privacy: PrivacyType
    layout: str = Field(..., min_length=1, max_length=30)


class VaultResponse(BaseModel):
    id: int
    date_created: datetime
    title: str
    privacy: PrivacyType
    layout: str
    post_count: int
    likes: int
    dislikes: int
    user: UserBase
    previews: list[str]
    user_reaction: ReactionType = ReactionType.NONE
