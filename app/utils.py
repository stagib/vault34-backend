import jwt
from datetime import datetime, timezone, timedelta
from argon2 import PasswordHasher
from typing import Annotated
from fastapi import Depends, Cookie
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Post
from app.config import settings

ph = PasswordHasher()


def hash_password(password: str):
    return ph.hash(password)


def verify_password(hashed_password: str, plain_password: str):
    try:
        ph.verify(hashed_password, plain_password)
        return True
    except Exception:
        return False


def add_item_to_string(string: str, item: str, limit: int = 100):
    string_list = string.split()
    if item in string_list:
        string_list.remove(item)
    string_list.append(item)
    if len(string_list) > limit:
        string_list.pop(0)
    return " ".join(string_list)


def get_emeddings(post_ids: str, db: Session):
    id_list = post_ids.split()
    posts = db.query(Post).filter(Post.id.in_(id_list)).all()
    return [post.embedding for post in posts]


def calculate_post_score(post: Post):
    now = datetime.now()
    hours_since = (now - post.date_created).total_seconds() / 3600
    reactions = post.likes + post.dislikes
    score = (
        reactions * 1 + post.comment_count * 2 + post.saves * 3 + post.views * 0.1
    ) / (hours_since + 1) ** 1.5
    return score


def create_token(id):
    token = jwt.encode(
        {
            "id": id,
            "exp": datetime.now(timezone.utc) + timedelta(hours=12),
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return token


def get_user(
    auth_token: Annotated[str | None, Cookie()] = None,
    db: Session = Depends(get_db),
):
    if not auth_token:
        return None
    try:
        payload = jwt.decode(
            auth_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id = payload.get("id")
        if not user_id or user_id is None:
            return None

        user = db.query(User).filter(User.id == user_id).first()
        if not user or user is None:
            return None
        return user
    except jwt.InvalidTokenError:
        return None
