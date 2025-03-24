from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination

from app.config import settings
from app.database import engine
from app.models import Base
from app.routers import post


app = FastAPI()
app.include_router(post.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

add_pagination(app)

Base.metadata.create_all(bind=engine)
