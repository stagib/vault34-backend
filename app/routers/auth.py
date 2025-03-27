from fastapi import APIRouter, Depends

from app.utils import get_current_user
from app.schemas import UserBase


router = APIRouter(tags=["Auth"])


@router.get("/verify-token", response_model=UserBase)
def verify_auth_token(user: dict = Depends(get_current_user)):
    return user
