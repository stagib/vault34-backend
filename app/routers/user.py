from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import driver, get_db
from app.models import User, Vault
from app.schemas.user import UserCreate, UserResponse
from app.schemas.vault import VaultResponse
from app.types import PrivacyType
from app.utils.auth import (
    create_token,
    get_user,
    hash_password,
    verify_password,
)
from app.utils.neo4j import create_user

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

    with driver.session() as session:
        session.execute_write(create_user, new_user.id, new_user.username)

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


@router.get("/users/{user_id}", response_model=UserResponse)
def get_current_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/users/{user_id}/vaults", response_model=Page[VaultResponse])
def get_user_vaults(
    user_id: int, user: dict = Depends(get_user), db: Session = Depends(get_db)
):
    query_user = db.query(User).filter(User.id == user_id).first()
    if not query_user:
        raise HTTPException(status_code=404, detail="User not found")

    if user and user.id == query_user.id:
        vaults = query_user.vaults.order_by(desc(Vault.date_created))
    else:
        vaults = query_user.vaults.order_by(desc(Vault.date_created)).filter(
            Vault.privacy == PrivacyType.PUBLIC
        )

    paginated_vaults = paginate(vaults)
    return paginated_vaults
