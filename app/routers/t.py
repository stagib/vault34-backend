import asyncio
from io import BytesIO

from PIL import Image
import aiohttp
import clip
from fastapi import APIRouter, Depends, Query
import requests
from sqlalchemy.orm import Session
import torch

from app.config import settings
from app.database import get_db
from app.models import Post

router = APIRouter()
device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)


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


@router.get("/test")
async def get_posts_t(tags: str = Query(None), db: Session = Depends(get_db)):
    params = {"limit": 50, "json": 1}
    if tags:
        params["tags"] = tags

    post_data = []
    res = requests.get(f"{settings.API_URL}", params=params)
    if res.status_code == 200:
        post_data = res.json()

    images = await fetch_all_images(post_data)
    if not images:
        return {"error": "message"}

    for post in post_data:
        if db.query(Post).filter(Post.post_id == post.get("id")).first():
            continue
        if not images.get(post.get("id")):
            continue

        image_vector = get_image_vector(images.get(post.get("id")))
        if image_vector is None:
            continue
        new_post = Post(
            post_id=post.get("id"),
            preview_url=post.get("preview_url"),
            sample_url=post.get("sample_url"),
            file_url=post.get("file_url"),
            owner=post.get("owner"),
            rating=post.get("rating"),
            tags=post.get("tags"),
            source=post.get("source"),
            score=post.get("score"),
            embedding=image_vector,
        )
        db.add(new_post)
    db.commit()

    return {"detail": "added new posts"}
