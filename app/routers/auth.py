from datetime import timedelta, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.schemas.user import UserBase, UserCreate
from app.utils.auth import (
    hash_password,
    verify_password,
    create_token,
    verify_token,
)

router = APIRouter(tags=["Auth"])


@router.get("/auth/verify", response_model=UserBase)
def verify_auth_token(user: dict = Depends(verify_token)):
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


@router.post("/auth/register")
def register_user(response: Response, user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username is already taken")

    hashed_password = hash_password(user.password)
    new_user = User(username=user.username, password=hashed_password)

    try:
        db.add(new_user)
        db.flush()

        """ with driver.session() as session:
            session.execute_write(create_user_, new_user) """

        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal error")

    time: timedelta = timedelta(hours=12)
    if user.remember_me:
        time = timedelta(days=30)

    expire_date = datetime.now(timezone.utc) + time
    token = create_token(new_user.username, new_user.id, expire_date)
    response.set_cookie(
        key="v34_auth",
        value=token,
        expires=expire_date,
        httponly=True,
        samesite="lax",
    )
    return {"detail": "User registered"}


@router.post("/auth/login")
def login(response: Response, user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Username or password is incorrect")

    if not verify_password(db_user.password, user.password):
        raise HTTPException(status_code=401, detail="Username or password is incorrect")

    time: timedelta = timedelta(hours=12)
    if user.remember_me:
        time = timedelta(days=30)

    expire_date = datetime.now(timezone.utc) + time
    token = create_token(db_user.username, db_user.id, expire_date)
    response.set_cookie(
        key="v34_auth",
        value=token,
        expires=expire_date,
        httponly=True,
        samesite="lax",
    )
    return {"detail": "Logged in"}


@router.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie("v34_auth")
    return {"detail": "Logged out"}
