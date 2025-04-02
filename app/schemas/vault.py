from pydantic import BaseModel, Field
from datetime import datetime

from app.types import PrivacyType
from app.schemas import UserBase, PostBase


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
    user: UserBase
    previews: str
