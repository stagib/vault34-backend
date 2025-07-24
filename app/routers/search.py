from datetime import datetime, timezone, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi_pagination import Page
from fastapi_pagination.cursor import CursorPage
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import and_, desc, Select
from sqlalchemy.orm import Session

from app.db import get_db

""" from app.db.neo4j import log_search_ """
from app.models import Post, Search, Vault
from app.schemas.post import PostBase
from app.schemas.search import SearchBase
from app.schemas.vault import VaultBase
from app.types import OrderType, RatingType, FileType, PrivacyType
from app.utils import normalize_text
from app.utils.search import log_search_metric, create_post_title_filter

router = APIRouter(tags=["Search"])


def get_post_order(order: OrderType):
    if order == OrderType.TRENDING:
        return desc(Post.trend_score)
    elif order == OrderType.POPULAR:
        return desc(Post.score)
    elif order == OrderType.POPULAR_WEEK:
        return desc(Post.week_score)
    elif order == OrderType.POPULAR_MONTH:
        return desc(Post.month_score)
    elif order == OrderType.POPULAR_YEAR:
        return desc(Post.year_score)
    elif order == OrderType.NEWEST:
        return desc(Post.date_created)
    else:
        return desc(Post.trend_score)


def get_vault_order(order: OrderType):
    if order == OrderType.TRENDING:
        return desc(Vault.trend_score)
    elif order == OrderType.POPULAR:
        return desc(Vault.score)
    elif order == OrderType.POPULAR_WEEK:
        return desc(Vault.week_score)
    elif order == OrderType.POPULAR_MONTH:
        return desc(Vault.month_score)
    elif order == OrderType.POPULAR_YEAR:
        return desc(Vault.year_score)
    elif order == OrderType.NEWEST:
        return desc(Vault.date_created)
    else:
        return desc(Vault.trend_score)


@router.get("/posts", response_model=CursorPage[PostBase])
def search_posts(
    query: Annotated[str | None, Query(min_length=1, max_length=50)] = None,
    rating: RatingType = RatingType.EXPLICIT,
    order: OrderType = OrderType.TRENDING,
    type: FileType = None,
    filter_ai: bool = False,
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    filters = []
    order_by = get_post_order(order)

    if rating == RatingType.QUESTIONABLE:
        filters.append(Post.rating == RatingType.QUESTIONABLE)

    if type:
        filters.append(Post.type == type)

    if filter_ai:
        filters.append(Post.ai_generated.is_(False))

    if query:
        normalized_query = normalize_text(query)
        title_filters = create_post_title_filter(query)
        for filter in title_filters:
            filters.append(filter)

        search = db.get(Search, normalized_query)

        if not search:
            search = Search(query=normalized_query, last_updated=now)
            db.add(search)
        else:
            search.score += 1
            if search.last_updated + timedelta(days=1) < now:
                search.last_updated = now
                log_search_metric(db, search, now)

        try:
            db.commit()
        except Exception:
            raise HTTPException(status_code=500, detail="Internal error")

    posts = (
        Select(Post.id, Post.sample_url, Post.preview_url, Post.type)
        .where(and_(*filters))
        .order_by(order_by)
    )
    return paginate(db, posts)


@router.get("/vaults", response_model=Page[VaultBase])
def get_vaults(
    query: Annotated[str | None, Query(min_length=1, max_length=50)] = None,
    order: OrderType = OrderType.POPULAR,
    db: Session = Depends(get_db),
):
    filters = []
    filters.append(Vault.privacy == PrivacyType.PUBLIC)
    order_by = get_vault_order(order)

    if query:
        normalized_query = normalize_text(query)
        words = normalized_query.split()
        for word in words:
            filters.append(Vault.title.ilike(f"%{word}%"))

    vaults = Select(Vault).where(and_(*filters)).order_by(order_by)
    return paginate(db, vaults)


@router.get("/searches", response_model=list[SearchBase])
def get_searches(
    query: Annotated[str | None, Query(min_length=1, max_length=50)] = None,
    db: Session = Depends(get_db),
):
    stmt = Select(Search.query, Search.score).order_by(desc(Search.score))

    if query:
        normalized_query = normalize_text(query)
        stmt = stmt.where(Search.query.ilike(f"{normalized_query}%"))
    stmt = stmt.limit(8)
    result = db.execute(stmt)
    return [dict(row._mapping) for row in result.all()]
