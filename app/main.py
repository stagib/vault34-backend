from alembic.config import Config
from contextlib import asynccontextmanager
from alembic import command
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination

from app.config import settings
from app.routers import auth, comment, post, user, vault, search


def run_migrations():
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(post.router)
app.include_router(search.router)
app.include_router(comment.router)
app.include_router(vault.router)
app.include_router(user.router)
app.include_router(auth.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

add_pagination(app)
