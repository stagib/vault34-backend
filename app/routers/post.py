from fastapi import APIRouter, Depends, HTTPException
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
import numpy
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import driver, get_db
from app.database.neo4j import create_post_, create_reaction_
from app.models import Post, Reaction
from app.schemas.post import PostBase, PostCreate, PostResponse
from app.schemas.reaction import ReactionBase
from app.types import ReactionType
from app.utils import add_item_to_string, calculate_post_score
from app.utils.auth import get_user

router = APIRouter(tags=["Post"])


@router.post("/posts")
def create_post(posts: list[PostCreate], db: Session = Depends(get_db)):
    with driver.session() as session:
        for post in posts:
            db_post = (
                db.query(Post).filter(Post.post_id == post.post_id).first()
            )
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
                embedding=post.embedding,
            )

            try:
                db.add(new_post)
                db.flush()

                session.execute_write(create_post_, new_post)

                db.commit()
            except Exception:
                db.rollback()
                raise HTTPException(status_code=500, detail="Internal error")

    return {"detail": f"Post {post.post_id} added"}


@router.get("/posts/recommend", response_model=Page[PostBase])
def get_recommendation(
    user: dict = Depends(get_user),
    db: Session = Depends(get_db),
):
    posts = db.query(Post).order_by(desc(Post.score))
    if user and user.history:
        history = list(map(int, user.history.strip().split()))
        posts = posts.filter(~Post.id.in_(history))

    posts = posts.limit(1000)
    paginated_posts = paginate(posts)
    return paginated_posts


@router.get("/posts/{post_id}", response_model=PostResponse)
def get_post(
    post_id: int,
    user: dict = Depends(get_user),
    db: Session = Depends(get_db),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if user:
        user_reaction = post.reactions.filter(
            Reaction.user_id == user.id
        ).first()
        if user_reaction:
            post.user_reaction = user_reaction.type

        user.history = add_item_to_string(user.history, str(post_id))
        db.commit()

    return post


@router.put("/posts/{post_id}")
def update_post(
    post_id: int,
    db: Session = Depends(get_db),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.score = calculate_post_score(post)
    post.views += 1  # will change later

    try:
        db.commit()
    except Exception:
        raise HTTPException(status_code=500, detail="Internal error")
    return {"detail"}


@router.get("/posts/{post_id}/recommend", response_model=Page[PostBase])
def get_post_recommendation(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    vector = numpy.array(post.embedding).tolist()

    posts = (
        db.query(Post)
        .order_by(Post.embedding.cosine_distance(vector), desc(Post.score))
        .filter(Post.embedding.cosine_distance(vector) > 0.05)
        .limit(1000)
    )

    paginated_posts = paginate(posts)
    return paginated_posts


def add_reaction(
    db_reaction: Reaction,
    reaction: Reaction,
    post: Post,
    user: dict,
    db: Session,
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
    else:
        if reaction.type == ReactionType.LIKE:
            post.likes += 1
        elif reaction.type == ReactionType.DISLIKE:
            post.dislikes += 1

        new_reaction = Reaction(
            user_id=user.id, post_id=post.id, type=reaction.type
        )
        db.add(new_reaction)


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

    try:
        add_reaction(db_reaction, reaction, post, user, db)

        with driver.session() as session:
            session.execute_write(
                create_reaction_,
                user.id,
                post.id,
                reaction.type.value,
            )

        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal error")

    return {
        "type": reaction.type,
        "likes": post.likes,
        "dislikes": post.dislikes,
    }
