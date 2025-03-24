import requests
from fastapi import APIRouter, Query, Depends, HTTPException
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Post
from app.schemas import PostBase, PostResponse


router = APIRouter(tags=["Post"])


@router.get("/posts", response_model=Page[PostBase])
def get_posts(tags: str = Query(None), db: Session = Depends(get_db)):
    params = {"limit": 1000, "json": 1}

    if tags:
        params["tags"] = tags

    res = requests.get(f"{settings.API_URL}", params=params)

    if res.status_code == 200:
        post_data = res.json()
        for post in post_data:
            if db.query(Post).filter(Post.post_id == post.get("id")).first():
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
                status=post.get("status"),
                score=post.get("score"),
            )
            db.add(new_post)
            db.commit()

    posts = db.query(Post).order_by(desc(Post.date_created))
    paginated_posts = paginate(posts)
    return paginated_posts


@router.get("/posts/recommend", response_model=Page[PostBase])
def get_recommendation(db: Session = Depends(get_db)):
    posts = db.query(Post).order_by(desc(Post.date_created))
    paginated_posts = paginate(posts)
    return paginated_posts


@router.get("/posts/{post_id}", response_model=PostResponse)
def get_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.get("/posts/{post_id}/recommend", response_model=Page[PostBase])
def get_post_recommendation(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    posts = db.query(Post)
    paginated_posts = paginate(posts)
    return paginated_posts
