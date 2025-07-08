from datetime import datetime

from pydantic import BaseModel, Field
from typing import Optional

from app.schemas.post import PostBase, PostResponse
from app.schemas.user import UserBase
from app.types import PrivacyType, ReactionType, LayoutType


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
    title: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=0, max_length=100)
    privacy: PrivacyType
    layout: LayoutType


class VaultBaseResponse(BaseModel):
    id: int
    title: str
    description: str
    post_count: int
    previews: list[str]
    privacy: PrivacyType
    layout: str
    user: UserBase


class VaultResponse(BaseModel):
    id: int
    date_created: datetime
    title: str
    description: str
    privacy: PrivacyType
    layout: str
    post_count: int
    likes: int
    dislikes: int
    user: UserBase
    previews: list[str]
    user_reaction: ReactionType = ReactionType.NONE
    last_updated: datetime
