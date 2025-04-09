from fastapi import APIRouter, Query, Depends, HTTPException
from fastapi_pagination import Page, paginate as paginate_t
from fastapi_pagination.ext.sqlalchemy import paginate
from fastapi_pagination.utils import disable_installed_extensions_check
from sqlalchemy import desc, select, and_
from sqlalchemy.orm import Session
import numpy

from app.database import get_db
from app.models import Post, Reaction, SearchQuery
from app.schemas import PostBase, PostResponse, ReactionBase, PostCreate
from app.utils import get_user, add_item_to_string, calculate_post_score
from app.types import ReactionType, RatingType, OrderType


router = APIRouter(tags=["Post"])


@router.post("/posts")
def create_post(posts: list[PostCreate], db: Session = Depends(get_db)):
    for post in posts:
        db_post = db.query(Post).filter(Post.post_id == post.post_id).first()
        if db_post:
            return {"detail": f"Post {db_post.post_id} already exists"}

        new_post = Post(
            post_id=post.post_id,
            preview_url=post.preview_url,
            sample_url=post.sample_url,
            file_url=post.file_url,
            owner=post.owner,
            rating=post.rating,
            tags=post.tags,
            source=post.source,
            score=post.score,
            embedding=post.embedding,
        )
        new_post.post_score = calculate_post_score(new_post)
        db.add(new_post)
    db.commit()
    return {"detail": f"Post {post.post_id} added"}


@router.get("/posts", response_model=Page[PostBase])
def get_posts(
    query: str = Query(None),
    rating: RatingType = Query(RatingType.EXPLICIT),
    order: OrderType = Query(OrderType.TRENDING),
    db: Session = Depends(get_db),
):
    posts = db.query(Post).order_by(desc(Post.post_score))

    if order == OrderType.TRENDING:
        posts = posts.order_by(desc(Post.post_score))
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

        words = query.lower().split()
        words = [word.strip() for word in words]
        conditions = [Post.tags.ilike(f"%{word}%") for word in words]
        posts = posts.filter(and_(*conditions))

    posts = posts.limit(1000)
    paginated_posts = paginate(posts)
    return paginated_posts


@router.get("/posts/recommend", response_model=Page[PostBase])
def get_post_recommendation(
    user: dict = Depends(get_user),
    db: Session = Depends(get_db),
):
    posts = db.query(Post).order_by(desc(Post.post_score))
    if user and user.history:
        history = list(map(int, user.history.strip().split()))
        posts = posts.filter(~Post.id.in_(history))

    posts = posts.limit(1000)
    paginated_posts = paginate(posts)
    return paginated_posts


@router.get("/posts/{post_id}", response_model=PostResponse)
def get_post(
    post_id: int, user: dict = Depends(get_user), db: Session = Depends(get_db)
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if user:
        user_reaction = post.reactions.filter(Reaction.user_id == user.id).first()
        if user_reaction:
            post.user_reaction = user_reaction.type

        user.history = add_item_to_string(user.history, str(post_id))
        db.commit()

    post.post_score = calculate_post_score(post)
    db.commit()
    return post


@router.get("/posts/{post_id}/recommend", response_model=Page[PostBase])
def get_post_recommendation(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    vector = numpy.array(post.embedding).tolist()
    results = db.scalars(
        select(Post)
        .order_by(Post.embedding.cosine_distance(vector), desc(Post.post_score))
        .filter(
            Post.embedding != vector,
            Post.embedding.cosine_distance(vector).between(0.08, 0.4),
        )
        .limit(1000)
    ).all()
    disable_installed_extensions_check()
    paginated_posts = paginate_t(results)
    return paginated_posts


def add_reaction(
    db_reaction: Reaction, reaction: Reaction, post: Post, user: dict, db: Session
):
    if db_reaction:
        if db_reaction.type == reaction.type:
            return

        if db_reaction.type == ReactionType.LIKE:
            post.likes -= 1
        elif db_reaction.type == ReactionType.DISLIKE:
            post.dislikes -= 1

        if reaction.type == ReactionType.LIKE:
            post.likes += 1
        elif reaction.type == ReactionType.DISLIKE:
            post.dislikes += 1

        db_reaction.type = reaction.type
        db.commit()
    else:
        if reaction.type == ReactionType.LIKE:
            post.likes += 1
        elif reaction.type == ReactionType.DISLIKE:
            post.dislikes += 1

        new_reaction = Reaction(user_id=user.id, post_id=post.id, type=reaction.type)
        db.add(new_reaction)
        db.commit()


@router.post("/posts/{post_id}/reactions")
def react_to_post(
    reaction: ReactionBase,
    post_id: int,
    user: dict = Depends(get_user),
    db: Session = Depends(get_db),
):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    db_reaction = (
        db.query(Reaction)
        .filter(Reaction.post_id == post_id, Reaction.user_id == user.id)
        .first()
    )

    add_reaction(db_reaction, reaction, post, user, db)
    return {
        "type": reaction.type,
        "likes": post.likes,
        "dislikes": post.dislikes,
    }
