from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
import numpy
from sqlalchemy import desc, Select
from sqlalchemy.orm import Session

from app.database import driver, get_db
from app.database.neo4j import (
    create_posts_,
    create_reaction_,
    log_search_click_,
)
from app.models import Post, Reaction
from app.schemas.post import PostBase, PostCreate, PostResponse
from app.schemas.reaction import ReactionBase
from app.types import RatingType, TargetType
from app.utils import calculate_post_score

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


@router.get("/posts/recommend", response_model=list[PostBase])
def get_recommendation(
    page: int = Query(1, ge=1, le=100),
    size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * size

    stmt = (
        Select(Post.id, Post.sample_url, Post.preview_url)
        .order_by(desc(Post.score))
        .offset(offset)
        .limit(size)
    )
    result = db.execute(stmt)
    return [dict(row._mapping) for row in result.all()]


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
    if post.last_updated + timedelta(minutes=5) < now:
        post.score = calculate_post_score(post)
        post.last_updated = now

    try:
        db.commit()
    except Exception:
        raise HTTPException(status_code=500, detail="Internal error")
    return {"detail"}


@router.get("/posts/{post_id}/recommend", response_model=list[PostBase])
def get_post_recommendation(
    post_id: int,
    page: int = Query(1, ge=1, le=100),
    size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = Select(Post.embedding).where(Post.id == post_id)
    result = db.execute(stmt).scalar_one_or_none()
    if not result:
        return []

    vector = numpy.array(result).tolist()
    offset = (page - 1) * size

    stmt = (
        Select(Post.id, Post.sample_url, Post.preview_url)
        .order_by(Post.embedding.cosine_distance(vector), desc(Post.score))
        .offset(offset)
        .limit(size)
    )
    result = db.execute(stmt)
    return [dict(row._mapping) for row in result.all()]


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
        db_reaction.type = reaction.type

    try:
        with driver.session() as session:
            session.execute_write(
                create_reaction_,
                user.id,
                post.id,
                reaction.type.value,
            )
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal error")
    return {"detail": "reaction added"}
