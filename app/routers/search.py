from fastapi import APIRouter, Depends, Query, Response
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.database.neo4j import log_search_
from app.models import Post, SearchQuery
from app.schemas.post import PostBase
from app.types import OrderType, RatingType
from app.utils.auth import get_user

router = APIRouter(tags=["Search"])


@router.get("/posts", response_model=Page[PostBase])
def get_posts(
    response: Response,
    query: str = Query(None),
    rating: RatingType = Query(RatingType.EXPLICIT),
    order: OrderType = Query(OrderType.TRENDING),
    user: dict = Depends(get_user),
    db: Session = Depends(get_db),
):
    posts = db.query(Post).order_by(desc(Post.score))

    if order == OrderType.TRENDING:
        posts = posts.order_by(desc(Post.score))
    elif order == OrderType.LIKES:
        posts = posts.order_by(desc(Post.likes))
    elif order == OrderType.views:
        posts = posts.order_by(desc(Post.views))
    elif order == OrderType.NEWEST:
        posts = posts.order_by(desc(Post.date_created))
    elif order == OrderType.OLDEST:
        posts = posts.order_by(Post.date_created)

    if rating == RatingType.QUESTIONABLE:
        posts = posts.filter(Post.rating == RatingType.QUESTIONABLE.value)

    if query:
        db_query = db.get(SearchQuery, query)
        if db_query:
            db_query.count += 1
        else:
            new_query = SearchQuery(query=query)
            db.add(new_query)
        db.commit()
        search_id = log_search_(query, user)
        response.set_cookie(
            key="search_id", value=search_id, httponly=True, samesite="lax"
        )
        words = query.lower().split()
        words = [word.strip() for word in words]
        conditions = [Post.tags.ilike(f"%{word}%") for word in words]
        posts = posts.filter(and_(*conditions))

    posts = posts.limit(1000)
    paginated_posts = paginate(posts)
    return paginated_posts
