from typing import Annotated
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi_pagination.ext.sqlalchemy import paginate
from fastapi_pagination.cursor import CursorPage
import numpy
import random
from sqlalchemy import desc, Select, exists, and_
from sqlalchemy.orm import Session

from app.db import get_db

""" from app.db.neo4j import (
    create_posts_,
    react_to_post_,
    log_search_click_,
) """
from app.models import Post, Reaction, Vault
from app.schemas.post import PostBase, PostCreate, PostResponse
from app.schemas.reaction import ReactionBase
from app.schemas.vault import VaultBaseResponse
import app.types as ta
from app.utils import update_reaction_count, normalize_text
from app.utils.auth import get_user, get_search_id
from app.utils.post import log_post_metric, update_top_vaults
from app.utils.search import create_post_title_filter

router = APIRouter(tags=["Post"])


@router.post("/posts")
def create_post(
    posts: list[PostCreate],
    user: dict = Depends(get_user),
    db: Session = Depends(get_db),
):
    if not user or user.role != ta.UserRole.ADMIN:
        raise HTTPException(status_code=401, detail="Not authenticated")

    post_objs = []
    """ neo4j_data = [] """

    if len(posts) > 1000:
        raise HTTPException(status_code=422, detail="Unprocessable Entity")

    for post in posts:
        prev_post = db.query(
            exists().where(Post.source_id == post.post_id)
        ).scalar()
        if prev_post:
            continue

        rating = ta.RatingType.EXPLICIT
        if post.rating == ta.RatingType.QUESTIONABLE.value:
            rating = ta.RatingType.QUESTIONABLE

        type = ta.FileType.IMAGE
        if post.type == ta.FileType.VIDEO.value:
            type = ta.FileType.VIDEO

        split_tags = post.tags.split()
        random_tags = split_tags
        if len(split_tags) >= 5:
            random_tags = random.sample(split_tags, 5)

        ai_generated = False
        if "ai_generated" in post.tags:
            ai_generated = True

        new_post = Post(
            source_id=post.post_id,
            title=post.tags,
            preview_url=post.preview_url,
            sample_url=post.sample_url,
            file_url=post.file_url,
            rating=rating,
            source=post.source,
            embedding=post.embedding,
            top_tags=random_tags,
            likes=post.score,
            score=post.score,
            week_score=post.score,
            month_score=post.score,
            year_score=post.score,
            type=type,
            ai_generated=ai_generated,
        )
        post_objs.append(new_post)

    try:
        db.add_all(post_objs)

        """ db.flush()
        for post in post_objs:
            data = {
                "id": post.id,
                "date_created": post.date_created,
                "score": post.score,
            }
            neo4j_data.append(data)

        session.execute_write(create_posts_, neo4j_data)  """
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal error")

    return {"detail": "Added posts"}


@router.get("/posts/recommend", response_model=CursorPage[PostBase])
def get_recommendation(
    db: Session = Depends(get_db),
):
    posts = db.query(
        Post.id, Post.sample_url, Post.preview_url, Post.type
    ).order_by(desc(Post.week_score))
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
            Reaction.target_type == ta.TargetType.POST,
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
        """log_search_click_(search_id, post_id)"""

    # update only if enough time as elapsed since last update
    if post.last_updated + timedelta(days=1) < now:
        post.last_updated = now
        log_post_metric(db, post, now)
        update_top_vaults(db, post)
        """ update_top_tags(post) """

    try:
        db.commit()
    except Exception:
        raise HTTPException(status_code=500, detail="Internal error")
    return {"detail"}


@router.get("/posts/{post_id}/recommend", response_model=CursorPage[PostBase])
def get_post_recommendation(
    post_id: int,
    query: Annotated[str | None, Query(min_length=1, max_length=50)] = None,
    type: ta.FileType = None,
    rating: ta.RatingType = ta.RatingType.EXPLICIT,
    filter_ai: bool = False,
    db: Session = Depends(get_db),
):
    stmt = Select(Post.embedding).where(Post.id == post_id)
    embedding = db.execute(stmt).scalar_one_or_none()
    if embedding is None:
        raise HTTPException(status_code=404, detail="Post not found")

    filters = []
    vector = numpy.array(embedding).tolist()

    if query:
        normalized_query = normalize_text(query)
        title_filters = create_post_title_filter(normalized_query)
        filters.append(*title_filters)

    if type:
        filters.append(Post.type == type)

    if rating == ta.RatingType.QUESTIONABLE:
        filters.append(Post.rating == ta.RatingType.QUESTIONABLE)

    if filter_ai:
        filters.append(Post.ai_generated == False)

    posts = (
        Select(Post.id, Post.sample_url, Post.preview_url, Post.type)
        .where(and_(*filters))
        .order_by(Post.embedding.cosine_distance(vector))
    )
    return paginate(db, posts)


@router.get(
    "/posts/{post_id}/recommend/vaults", response_model=list[VaultBaseResponse]
)
def get_post_vault_recommendation(post_id: int, db: Session = Depends(get_db)):
    vaults = []
    top_vaults = db.query(Post.top_vaults).filter(Post.id == post_id).first()
    if top_vaults[0]:
        ids = [int(id) for id in top_vaults[0]]
        vaults = (
            db.query(Vault)
            .filter(Vault.id.in_(ids), Vault.privacy == ta.PrivacyType.PUBLIC)
            .limit(4)
            .all()
        )
    return vaults


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

    stmt = Select(Reaction).where(
        Reaction.target_type == ta.TargetType.POST,
        Reaction.target_id == post_id,
        Reaction.user_id == user.id,
    )

    prev_reaction = ta.ReactionType.NONE
    db_reaction = db.execute(stmt).scalar_one_or_none()
    if not db_reaction:
        new_reaction = Reaction(
            target_type=ta.TargetType.POST,
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
        """ with driver.session() as session:
            session.execute_write(
                react_to_post_,
                user.id,
                post_id,
                reaction.type.value,
            ) """
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal error")
    return {"detail": "reaction added"}
