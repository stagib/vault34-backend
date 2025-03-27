from pydantic import BaseModel
from datetime import datetime


class PostBase(BaseModel):
    id: int
    sample_url: str
    preview_url: str


class PostResponse(BaseModel):
    id: int
    date_created: datetime
    post_id: int
    preview_url: str
    sample_url: str
    file_url: str
    owner: str
    rating: str
    tags: str
    source: str
    score: int
    likes: int
    dislikes: int
