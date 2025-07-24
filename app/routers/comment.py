from fastapi import APIRouter, Depends, HTTPException
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import desc, Select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Comment, Post, Reaction
from app.schemas.comment import CommentCreate, CommentResponse
from app.schemas.reaction import ReactionCreate
from app.types import ReactionType, TargetType
from app.utils import update_reaction_count
from app.utils.auth import get_user

router = APIRouter(tags=["Comment"])


@router.get("/posts/{post_id}/comments", response_model=Page[CommentResponse])
def get_comments(
    post_id: int,
    user: dict = Depends(get_user),
    db: Session = Depends(get_db),
):
    db_post = db.get(Post, post_id)
    if not db_post:
        raise HTTPException(status_code=404, detail="Post not found")

    paginated_comments = paginate(db_post.comments.order_by(desc(Comment.date_created)))

    if user:
        comment_ids = [comment.id for comment in paginated_comments.items]
        reactions = (
            db.query(Reaction)
            .filter(
                Reaction.user_id == user.id,
                Reaction.target_type == TargetType.COMMENT,
                Reaction.target_id.in_(comment_ids),
            )
            .all()
        )

        reactions_map = {reaction.target_id: reaction.type for reaction in reactions}
        for comment in paginated_comments.items:
            if reactions_map.get(comment.id):
                comment.user_reaction = reactions_map.get(comment.id)
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

    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.comment_count += 1
    new_comment = Comment(user_id=user.id, post_id=post.id, content=comment.content)

    try:
        db.add(new_comment)
        db.commit()
    except Exception:
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


@router.post("/posts/{post_id}/comments/{comment_id}/reactions")
def react_to_comment(
    post_id: int,
    comment_id: int,
    reaction: ReactionCreate,
    user: dict = Depends(get_user),
    db: Session = Depends(get_db),
):
    comment = db.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    stmt = Select(Reaction).where(
        Reaction.target_type == TargetType.COMMENT,
        Reaction.target_id == comment_id,
        Reaction.user_id == user.id,
    )

    prev_reaction = ReactionType.NONE
    db_reaction = db.execute(stmt).scalar_one_or_none()
    if not db_reaction:
        new_reaction = Reaction(
            target_type=TargetType.COMMENT,
            target_id=comment_id,
            user_id=user.id,
            type=reaction.type,
        )
        db.add(new_reaction)
    else:
        prev_reaction = db_reaction.type
        db_reaction.type = reaction.type

    try:
        update_reaction_count(comment, prev_reaction, reaction.type)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal error")
    return {
        "likes": comment.likes,
        "dislikes": comment.dislikes,
        "type": reaction.type,
    }
