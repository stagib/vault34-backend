from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi_pagination import Page
from fastapi_pagination.cursor import CursorPage
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import and_, desc, Select, or_
from sqlalchemy.orm import Session

from app.db import get_db

""" from app.db.neo4j import log_search_ """
from app.models import Post, Search, Vault
from app.schemas.post import PostBase
from app.schemas.search import SearchResponse
from app.schemas.vault import VaultBaseResponse
from app.types import OrderType, RatingType, FileType
from app.utils import normalize_text
from app.utils.search import log_search_metric

router = APIRouter(tags=["Search"])


def order_posts(posts, order):
    if order == OrderType.TRENDING:
        p = posts.order_by(desc(Post.trend_score))
    elif order == OrderType.POPULAR:
        p = posts.order_by(desc(Post.score))
    elif order == OrderType.POPULAR_WEEK:
        p = posts.order_by(desc(Post.week_score))
    elif order == OrderType.POPULAR_MONTH:
        p = posts.order_by(desc(Post.month_score))
    elif order == OrderType.POPULAR_YEAR:
        p = posts.order_by(desc(Post.year_score))
    elif order == OrderType.NEWEST:
        p = posts.order_by(desc(Post.date_created))
    else:
        p = posts.order_by(desc(Post.trend_score))
    return p


def filter_posts(posts, query):
    words = query.lower().split()
    words = [word.strip() for word in words]
    conditions = [Post.title.ilike(f"%{word}%") for word in words]

    if query.isdigit():
        int_query = int(query)
        p = posts.filter(
            or_(Post.id == int_query, Post.source_id == int_query)
        )
    else:
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


@router.get("/posts", response_model=CursorPage[PostBase])
def search_posts(
    query: str = None,
    rating: RatingType = RatingType.EXPLICIT,
    order: OrderType = OrderType.TRENDING,
    type: FileType = None,
    filter_ai: bool = False,
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    posts = db.query(Post.id, Post.sample_url, Post.preview_url, Post.type)
    posts = order_posts(posts, order)

    if rating == RatingType.QUESTIONABLE:
        posts = posts.filter(Post.rating == RatingType.QUESTIONABLE)

    if type:
        posts = posts.filter(Post.type == type)

    if filter_ai:
        posts = posts.filter(Post.ai_generated == False)

    if query:
        normalized_query = normalize_text(query)
        posts = filter_posts(posts, normalized_query)
        search = db.get(Search, normalized_query)

        if not search:
            search = Search(query=normalized_query, last_updated=now)
            db.add(search)

        if search and search.last_updated + timedelta(days=1) < now:
            search.last_updated = now
            log_search_metric(db, search, now)

        try:
            db.commit()
        except Exception:
            raise HTTPException(status_code=500, detail="Internal error")
        """ search_id = str(uuid4())
        update_search_count(db, normalized_query)
        log_search_(search_id, normalized_query, user)

        response.set_cookie(
            key="search_id", value=search_id, httponly=True, samesite="lax"
        ) """
    return paginate(posts)


@router.get("/vaults", response_model=Page[VaultBaseResponse])
def get_vaults(query: str = Query(None), db: Session = Depends(get_db)):
    vaults = db.query(Vault).order_by(Vault.likes)
    if query:
        normalized_query = normalize_text(query)
        words = normalized_query.lower().split()
        words = [word.strip() for word in words]
        conditions = [Vault.title.ilike(f"%{word}%") for word in words]
        vaults = vaults.filter(and_(*conditions))
    return paginate(vaults)


@router.get("/searches", response_model=list[SearchResponse])
def get_searches(
    query: str = Query(None),
    db: Session = Depends(get_db),
):
    stmt = Select(Search.query, Search.score).order_by(desc(Search.score))

    if query:
        normalized_query = normalize_text(query)
        stmt = stmt.where(Search.query.ilike(f"{normalized_query}%"))
    stmt = stmt.limit(8)
    result = db.execute(stmt)
    return [dict(row._mapping) for row in result.all()]
