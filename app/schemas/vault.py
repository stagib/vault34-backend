from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas import PostBase, UserBase
from app.types import PrivacyType


class VaultPostBase(BaseModel):
    id: int
    post: PostBase


class VaultBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=30)
    privacy: PrivacyType


class VaultResponse(BaseModel):
    id: int
    date_created: datetime
    title: str
    privacy: PrivacyType
    post_count: int
    user: UserBase
    previews: str
