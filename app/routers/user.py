from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import UserCreate
from app.utils import hash_password, create_token, verify_password


router = APIRouter(tags=["User"])


@router.post("/users")
def register_user(response: Response, user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username is already taken")

    hashed_password = hash_password(user.password)
    new_user = User(username=user.username, password=hashed_password)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_token(id=new_user.id)
    response.set_cookie(key="auth_token", value=token)
    return {"detail": "User registered"}


@router.post("/users/login")
def login(response: Response, user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Username or password is incorrect")

    if not verify_password(db_user.password, user.password):
        raise HTTPException(status_code=401, detail="Username or password is incorrect")

    token = create_token(id=db_user.id)
    response.set_cookie(key="auth_token", value=token)
    return {"detail": "Logged in"}


@router.post("/users/logout")
def logout(response: Response):
    response.delete_cookie("auth_token")
    return {"detail": "Logged out"}
