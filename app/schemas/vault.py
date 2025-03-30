from pydantic import BaseModel, Field

from app.types import PrivacyType
from app.schemas import UserBase, PostBase


class VaultBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=30)
    privacy: PrivacyType


class VaultResponse(BaseModel):
    id: int
    title: str
    privacy: PrivacyType
    user: UserBase


class VaultPostBase(BaseModel):
    id: int
    post: PostBase
