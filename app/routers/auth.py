from fastapi import APIRouter, Depends

from app.schemas import UserBase
from app.utils.auth import get_user


router = APIRouter(tags=["Auth"])


@router.get("/verify-token", response_model=UserBase)
def verify_auth_token(user: dict = Depends(get_user)):
    return user
