from fastapi import APIRouter, Depends, HTTPException
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import desc
from sqlalchemy.orm import Session

""" from app.db.neo4j import create_user_ """
from app.db import get_db
from app.models import User, Vault, Post, Reaction
from app.schemas.user import UserResponse
from app.schemas.vault import VaultBase
from app.schemas.post import PostBase
from app.types import PrivacyType, ReactionType, TargetType
from app.utils.auth import verify_token

router = APIRouter(tags=["User"])


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/users/{user_id}/vaults", response_model=Page[VaultBase])
def get_user_vaults(
    user_id: int,
    user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    query_user = db.query(User).filter(User.id == user_id).first()
    if not query_user:
        raise HTTPException(status_code=404, detail="User not found")

    vaults = (
        db.query(Vault)
        .filter(Vault.user_id == query_user.id)
        .order_by(desc(Vault.score), desc(Vault.post_count), desc(Vault.date_created))
    )

    if not user or user.get("id") != query_user.id:
        vaults = vaults.filter(Vault.privacy == PrivacyType.PUBLIC)

    paginated_vaults = paginate(vaults)
    return paginated_vaults


@router.get("/users/{user_id}/reactions", response_model=Page[PostBase])
def get_user_reaction(
    user_id: int,
    type: ReactionType = ReactionType.LIKE,
    db: Session = Depends(get_db),
):
    reactions = (
        db.query(Reaction.target_id)
        .filter(
            Reaction.user_id == user_id,
            Reaction.target_type == TargetType.POST,
            Reaction.type == type,
        )
        .limit(1000)
        .all()
    )

    post_ids = [id for (id,) in reactions]
    posts = db.query(Post.id, Post.sample_url, Post.preview_url, Post.type).filter(
        Post.id.in_(post_ids)
    )
    return paginate(posts)


""" @router.post("/users/{user_id}/followers")
def follow_user(
    user_id: int, user: dict = Depends(get_user), db: Session = Depends(get_db)
):
    query_user = db.query(User).filter(User.id == user_id).first()
    if not query_user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if user.id == query_user.id:
        raise HTTPException(status_code=400, detail="Can not follow self")

    try:
        with driver.session() as session:
            session.execute_write(follow_user_, user.id, query_user.id)

    except Exception:
        raise HTTPException(status_code=500, detail="Internal error")
    return {"detail": "Followed user"}


@router.delete("/users/{user_id}/followers")
def unfollow_user(user_id: int, user: dict = Depends(get_user)):
    try:
        with driver.session() as session:
            session.execute_write(unfollow_user_, user.id, user_id)
    except Exception:
        raise HTTPException(status_code=500, detail="Internal error")
    return {"detail": "Unfollowed user"}
 """
