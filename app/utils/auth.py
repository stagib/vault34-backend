from datetime import datetime
from typing import Annotated

from argon2 import PasswordHasher
from fastapi import Cookie, Depends
import jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import User

ph = PasswordHasher()


def hash_password(password: str):
    return ph.hash(password)


def verify_password(hashed_password: str, plain_password: str):
    try:
        ph.verify(hashed_password, plain_password)
        return True
    except Exception:
        return False


def create_token(username: str, user_id: int, expire_date: datetime):
    payload = {
        "username": username,
        "id": user_id,
        "exp": expire_date,
    }
    token = jwt.encode(
        payload,
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


def get_search_id(search_id: Annotated[str | None, Cookie()] = None):
    if not search_id:
        return None
    return search_id
