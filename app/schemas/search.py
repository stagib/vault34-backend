from pydantic import BaseModel


class SearchResponse(BaseModel):
    query: str
