import requests
import datetime
from fastapi import APIRouter, Query, Depends, HTTPException
from fastapi_pagination import Page, paginate as paginate_t
from fastapi_pagination.ext.sqlalchemy import paginate
from fastapi_pagination.utils import disable_installed_extensions_check
from sqlalchemy import desc, select
from sqlalchemy.orm import Session
import numpy

from app.config import settings
from app.database import get_db
from app.models import Post, Reaction
from app.schemas import PostBase, PostResponse, ReactionBase
from app.utils import (
    fetch_all_images,
    get_image_vector,
    get_user,
    add_item_to_string,
    calculate_post_score,
)
from app.types import ReactionType


router = APIRouter(tags=["Post"])


@router.get("/posts/t", response_model=Page[PostBase])
async def get_posts(tags: str = Query(None), db: Session = Depends(get_db)):
    params = {"limit": 50, "json": 1}
    if tags:
        params["tags"] = tags

    post_data = []
    res = requests.get(f"{settings.API_URL}", params=params)
    if res.status_code == 200:
        post_data = res.json()

    images = await fetch_all_images(post_data)
    if not images:
        return {"error": "message"}

    for post in post_data:
        if db.query(Post).filter(Post.post_id == post.get("id")).first():
            continue
        if not images.get(post.get("id")):
            continue

        image_vector = get_image_vector(images.get(post.get("id")))
        if image_vector is None:
            continue
        new_post = Post(
            post_id=post.get("id"),
            preview_url=post.get("preview_url"),
            sample_url=post.get("sample_url"),
            file_url=post.get("file_url"),
            owner=post.get("owner"),
            rating=post.get("rating"),
            tags=post.get("tags"),
            source=post.get("source"),
            score=post.get("score"),
            embedding=image_vector,
        )
        db.add(new_post)
    db.commit()
    posts = db.query(Post).order_by(desc(Post.date_created))
    paginated_posts = paginate(posts)
    return paginated_posts


@router.get("/posts/trending", response_model=Page[PostBase])
def get_trending_posts(db: Session = Depends(get_db)):
    trend_start = datetime.datetime.now() - datetime.timedelta(days=7)
    trending = (
        db.query(Post)
        .join(Reaction)
        .filter(Reaction.date_created >= trend_start)
        .order_by(desc(Post.likes), desc(Post.score))
        .limit(1000)
    )
    paginated_posts = paginate(trending)

    """ embeddings = get_emeddings(user.history, db)
    user_profile = numpy.mean(embeddings, axis=0).tolist()
    results = db.scalars(
        select(Post)
        .order_by(Post.embedding.cosine_distance(user_profile) < 0.5)
        .limit(1000)
    ).all()
    disable_installed_extensions_check()
    paginated_posts = paginate_t(results) """
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

    post.views += 1
    post.post_score = calculate_post_score(post)
    db.commit()
    return post


@router.get("/posts/{post_id}/recommend", response_model=Page[PostBase])
def get_post_recommendation(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    vector = numpy.array(post.embedding).tolist()
    results = db.scalars(
        select(Post)
        .order_by(Post.embedding.cosine_distance(vector))
        .filter(Post.embedding != vector, Post.embedding.cosine_distance(vector) < 0.2)
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
