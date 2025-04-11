from datetime import datetime

from pydantic import BaseModel, Field


class UserBase(BaseModel):
    id: int
    username: str


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    password: str = Field(..., min_length=3, max_length=100)


class UserResponse(BaseModel):
    id: int
    username: str
    date_created: datetime
