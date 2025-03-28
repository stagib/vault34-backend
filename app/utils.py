import asyncio
import aiohttp
import torch
import clip
import jwt
from datetime import datetime, timezone, timedelta
from argon2 import PasswordHasher
from typing import Annotated
from PIL import Image
from fastapi import Depends, Cookie
from sqlalchemy.orm import Session
from io import BytesIO

from app.database import get_db
from app.models import User
from app.config import settings

device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)
ph = PasswordHasher()


async def fetch_image(session, post):
    try:
        async with session.get(post.get("file_url"), timeout=30) as res:
            if res.status == 200:
                img_data = await res.read()
                return {
                    "img": Image.open(BytesIO(img_data)).convert("RGB"),
                    "id": post.get("id"),
                }
    except Exception as e:
        return None
    return None


async def fetch_all_images(post_data):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_image(session, post) for post in post_data]
        images = await asyncio.gather(*tasks)
        map = {}
        for image in images:
            if image is None or not image.get("img"):
                continue
            map[image.get("id")] = image.get("img")
        return map


def get_image_vector(image):
    try:
        input = preprocess(image).unsqueeze(0).to(device)
        with torch.no_grad():
            vector = model.encode_image(input).cpu().numpy().tolist()[0]
            return vector
    except Exception as e:
        return None


def hash_password(password: str):
    return ph.hash(password)


def verify_password(hashed_password: str, plain_password: str):
    try:
        ph.verify(hashed_password, plain_password)
        return True
    except Exception:
        return False


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
