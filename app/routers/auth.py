from fastapi import APIRouter, Depends, HTTPException

from app.schemas.user import UserBase
from app.utils.auth import get_user

router = APIRouter(tags=["Auth"])


@router.get("/verify-token", response_model=UserBase)
def verify_auth_token(user: dict = Depends(get_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")

    return user
