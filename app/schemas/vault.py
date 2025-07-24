from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.post import PostBase
from app.schemas.user import UserBase
from app.types import PrivacyType, ReactionType, LayoutType


class EntryPreview(BaseModel):
    id: int
    vault_id: int
    index: int
    post: PostBase


class VaultCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=0, max_length=100)
    privacy: PrivacyType
    layout: LayoutType


class VaultBase(BaseModel):
    id: int
    title: str
    post_count: int
    previews: list[str]
    privacy: PrivacyType


class VaultResponse(BaseModel):
    id: int
    title: str
    description: str
    privacy: PrivacyType
    layout: str
    post_count: int
    likes: int
    dislikes: int
    user: UserBase
    user_reaction: ReactionType = ReactionType.NONE
    last_updated: datetime
