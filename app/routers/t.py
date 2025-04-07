import requests
from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Post
from app.utils import fetch_all_images, get_image_vector


router = APIRouter()


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
