from fastapi import APIRouter, Depends, HTTPException
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.database.neo4j import log_search_click_

from app.models import Comment, Post, Reaction
from app.schemas.comment import CommentCreate, CommentResponse
from app.schemas.reaction import ReactionBase
from app.types import ReactionType
from app.utils import calculate_post_score
from app.utils.auth import get_user, get_search_id

router = APIRouter(tags=["Comment"])


@router.get("/posts/{post_id}/comments", response_model=Page[CommentResponse])
def get_comments(
    post_id: int,
    search_id=Depends(get_search_id),
    user: dict = Depends(get_user),
    db: Session = Depends(get_db),
):
    db_post = db.query(Post).filter(Post.id == post_id).first()
    if not db_post:
        raise HTTPException(status_code=404, detail="Post not found")

    paginated_comments = paginate(
        db_post.comments.order_by(desc(Comment.date_created))
    )

    if user:
        log_search_click_(search_id, post_id)
        comment_ids = [comment.id for comment in paginated_comments.items]
        reactions = (
            db.query(Reaction)
            .filter(
                Reaction.comment_id.in_(comment_ids),
                Reaction.user_id == user.id,
            )
            .all()
        )

        reactions_map = {
            reaction.comment_id: reaction.type for reaction in reactions
        }
        for comment in paginated_comments.items:
            comment.user_reaction = ReactionType.NONE
            if reactions_map.get(comment.id):
                comment.user_reaction = reactions_map.get(comment.id)

    db_post.score = calculate_post_score(db_post)
    db_post.views += 1

    try:
        db.commit()
    except Exception:
        raise HTTPException(status_code=500, detail="Internal error")
    return paginated_comments


@router.post("/posts/{post_id}/comments", response_model=CommentResponse)
def create_comment(
    post_id: int,
    comment: CommentCreate,
    user: dict = Depends(get_user),
    db: Session = Depends(get_db),
):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.comment_count += 1
    new_comment = Comment(
        user_id=user.id, post_id=post.id, content=comment.content
    )

    try:
        db.add(new_comment)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal error")
    return new_comment


@router.delete("/posts/{post_id}/comments/{comment_id}")
def delete_comment(
    post_id: int,
    comment_id: int,
    user: dict = Depends(get_user),
    db: Session = Depends(get_db),
):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    comment = (
        db.query(Comment)
        .filter(
            Comment.id == comment_id,
            Comment.post_id == post_id,
            Comment.user_id == user.id,
        )
        .first()
    )
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    comment.post.comment_count -= 1
    try:
        db.delete(comment)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal error")
    return {"detail": "Removed comment"}


def add_reaction(
    db_reaction: Reaction,
    reaction: Reaction,
    comment: Comment,
    user: dict,
    db: Session,
):
    if db_reaction:
        if db_reaction.type == reaction.type:
            return

        if db_reaction.type == ReactionType.LIKE:
            comment.likes -= 1
        elif db_reaction.type == ReactionType.DISLIKE:
            comment.dislikes -= 1

        if reaction.type == ReactionType.LIKE:
            comment.likes += 1
        elif reaction.type == ReactionType.DISLIKE:
            comment.dislikes += 1

        db_reaction.type = reaction.type
    else:
        if reaction.type == ReactionType.LIKE:
            comment.likes += 1
        elif reaction.type == ReactionType.DISLIKE:
            comment.dislikes += 1

        new_reaction = Reaction(
            user_id=user.id, comment_id=comment.id, type=reaction.type
        )
        db.add(new_reaction)


@router.post("/posts/{post_id}/comments/{comment_id}/reactions")
def react_to_comment(
    post_id: int,
    comment_id: int,
    reaction: ReactionBase,
    user: dict = Depends(get_user),
    db: Session = Depends(get_db),
):
    comment = (
        db.query(Comment)
        .filter(Comment.post_id == post_id, Comment.id == comment_id)
        .first()
    )
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    db_reaction = (
        db.query(Reaction)
        .filter(
            Reaction.comment_id == comment.id,
            Reaction.user_id == user.id,
        )
        .first()
    )

    try:
        add_reaction(db_reaction, reaction, comment, user, db)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal error")
    return {
        "type": reaction.type,
        "likes": comment.likes,
        "dislikes": comment.dislikes,
    }
