import re
import string
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, Response
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import and_, desc, Select
from sqlalchemy.orm import Session

from app.database import get_db
from app.database.neo4j import log_search_
from app.models import Post, Search
from app.schemas.post import PostBase
from app.schemas.search import SearchResponse
from app.types import OrderType, RatingType
from app.utils.auth import get_user

router = APIRouter(tags=["Search"])


def normalize_text(query: str):
    q = query
    q = q.lower()
    q = q.strip()
    q = re.sub(r"\s+", " ", q)
    return q


def order_posts(posts, order):
    if order == OrderType.TRENDING:
        p = posts.order_by(desc(Post.score))
    elif order == OrderType.LIKES:
        p = posts.order_by(desc(Post.likes))
    elif order == OrderType.NEWEST:
        p = posts.order_by(desc(Post.date_created))
    elif order == OrderType.OLDEST:
        p = posts.order_by(Post.date_created)
    return p


def filter_posts(posts, query):
    words = query.lower().split()
    words = [word.strip() for word in words]
    conditions = [Post.tags.ilike(f"%{word}%") for word in words]
    p = posts.filter(and_(*conditions))
    return p


def update_search_count(db: Session, query: str):
    db_query = db.get(Search, query)
    if db_query:
        db_query.count += 1
    else:
        new_query = Search(query=query)
        db.add(new_query)
    db.commit()


@router.get("/posts", response_model=Page[PostBase])
def search_posts(
    response: Response,
    query: str = Query(None),
    rating: RatingType = Query(RatingType.EXPLICIT),
    order: OrderType = Query(OrderType.TRENDING),
    user: dict = Depends(get_user),
    db: Session = Depends(get_db),
):
    posts = db.query(Post.id, Post.sample_url, Post.preview_url)
    posts = order_posts(posts, order)

    if rating == RatingType.QUESTIONABLE:
        posts = posts.filter(Post.rating == RatingType.QUESTIONABLE)

    if query:
        normalized_query = normalize_text(query)
        search_id = str(uuid4())
        posts = filter_posts(posts, normalized_query)
        update_search_count(db, normalized_query)
        log_search_(search_id, normalized_query, user)

        response.set_cookie(
            key="search_id", value=search_id, httponly=True, samesite="lax"
        )
    return paginate(posts)


@router.get("/searches", response_model=list[SearchResponse])
def get_searches(
    query: str = Query(None),
    db: Session = Depends(get_db),
):
    stmt = Select(Search.query, Search.count).order_by(desc(Search.count))

    if query:
        normalized_query = normalize_text(query)
        stmt = stmt.where(Search.query.ilike(f"{normalized_query}%"))
    stmt = stmt.limit(8)
    result = db.execute(stmt)
    return [dict(row._mapping) for row in result.all()]
