from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
import numpy
from sqlalchemy import desc, Select
from sqlalchemy.orm import Session

from app.db import driver, get_db
from app.db.neo4j import (
    create_posts_,
    react_to_post_,
    log_search_click_,
)
from app.models import Post, Reaction
from app.schemas.post import PostBase, PostCreate, PostResponse
from app.schemas.reaction import ReactionBase
from app.types import RatingType, TargetType, ReactionType
from app.utils import (
    calculate_post_score,
    update_reaction_count,
    log_post_metric,
)

from app.utils.auth import get_user, get_search_id

router = APIRouter(tags=["Post"])


@router.post("/posts")
def create_post(posts: list[PostCreate], db: Session = Depends(get_db)):
    with driver.session() as session:
        post_objs = []
        neo4j_data = []

        for post in posts:
            rating = RatingType.EXPLICIT
            if post.rating == RatingType.QUESTIONABLE.value:
                rating = RatingType.QUESTIONABLE

            new_post = Post(
                title=post.tags,
                preview_url=post.preview_url,
                sample_url=post.sample_url,
                file_url=post.file_url,
                rating=rating,
                tags=post.tags,
                source=post.source,
                embedding=post.embedding,
            )
            post_objs.append(new_post)

        try:
            db.add_all(post_objs)
            db.flush()
            for post in post_objs:
                data = {
                    "id": post.id,
                    "date_created": post.date_created,
                    "score": post.score,
                }
                neo4j_data.append(data)

            session.execute_write(create_posts_, neo4j_data)
            db.commit()
        except Exception:
            db.rollback()
            raise HTTPException(status_code=500, detail="Internal error")

    return {"detail": "Added posts"}


@router.get("/posts/recommend", response_model=Page[PostBase])
def get_recommendation(
    db: Session = Depends(get_db),
):
    posts = db.query(Post.id, Post.sample_url, Post.preview_url).order_by(
        desc(Post.score)
    )
    return paginate(posts)


@router.get("/posts/{post_id}", response_model=PostResponse)
def get_post(
    post_id: int,
    user: dict = Depends(get_user),
    db: Session = Depends(get_db),
):
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if user:
        stmt = Select(Reaction.type).where(
            Reaction.target_type == TargetType.POST,
            Reaction.target_id == post_id,
            Reaction.user_id == user.id,
        )
        result = db.execute(stmt).scalar_one_or_none()
        if result:
            post.user_reaction = result
    return post


@router.put("/posts/{post_id}")
def update_post(
    post_id: int,
    search_id=Depends(get_search_id),
    user: dict = Depends(get_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # update every time
    if user:
        log_search_click_(search_id, post_id)

    # update only if enough time as elapsed since last update
    if post.last_updated + timedelta(minutes=30) < now:
        post.last_updated = now
        post.score = calculate_post_score(
            post.likes, post.dislikes, post.saves, post.comment_count
        )
        log_post_metric(db, post, now)

    try:
        db.commit()
    except Exception:
        raise HTTPException(status_code=500, detail="Internal error")
    return {"detail"}


@router.get("/posts/{post_id}/recommend", response_model=Page[PostBase])
def get_post_recommendation(
    post_id: int,
    db: Session = Depends(get_db),
):
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    vector = numpy.array(post.embedding).tolist()
    posts = db.query(Post.id, Post.sample_url, Post.preview_url).order_by(
        Post.embedding.cosine_distance(vector), desc(Post.score)
    )
    return paginate(posts)


@router.post("/posts/{post_id}/reactions")
def react_to_post(
    reaction: ReactionBase,
    post_id: int,
    user: dict = Depends(get_user),
    db: Session = Depends(get_db),
):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    stmt = Select(Reaction.type).where(
        Reaction.target_type == TargetType.POST,
        Reaction.target_id == post_id,
        Reaction.user_id == user.id,
    )

    prev_reaction = ReactionType.NONE
    db_reaction = db.execute(stmt).scalar_one_or_none()
    if not db_reaction:
        new_reaction = Reaction(
            target_type=TargetType.POST,
            target_id=post_id,
            user_id=user.id,
            type=reaction.type,
        )
        db.add(new_reaction)
    else:
        prev_reaction = db_reaction.type
        db_reaction.type = reaction.type

    try:
        update_reaction_count(post, prev_reaction, reaction.type)
        with driver.session() as session:
            session.execute_write(
                react_to_post_,
                user.id,
                post_id,
                reaction.type.value,
            )
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal error")
    return {"detail": "reaction added"}
