import datetime
from sqlalchemy import func, Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy import Enum
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.database import Base
from app.types import ReactionType, PrivacyType


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    date_created = Column(DateTime, default=func.now(), nullable=False)
    username = Column(String, nullable=False)
    password = Column(String, nullable=False)
    history = Column(String, nullable=False, default="")
    reactions = relationship("Reaction", back_populates="user", lazy="dynamic")
    comments = relationship("Comment", back_populates="user", lazy="dynamic")
    vaults = relationship("Vault", back_populates="user", lazy="dynamic")


class VaultPost(Base):
    __tablename__ = "vault_post"
    id = Column(Integer, primary_key=True, index=True)
    date_created = Column(DateTime, default=func.now())
    vault_id = Column(Integer, ForeignKey("vaults.id"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    vault = relationship("Vault", back_populates="vault_posts")
    post = relationship("Post", backref="vault_post")


class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, index=True)
    date_created = Column(DateTime, default=func.now(), nullable=False)

    post_id = Column(Integer)
    preview_url = Column(String)
    sample_url = Column(String)
    file_url = Column(String)
    owner = Column(String)
    rating = Column(String)
    tags = Column(String)
    source = Column(String)
    score = Column(Integer)

    reactions = relationship("Reaction", back_populates="post", lazy="dynamic")
    comments = relationship("Comment", back_populates="post", lazy="dynamic")

    embedding = Column(Vector(512))
    likes = Column(Integer, default=0)
    dislikes = Column(Integer, default=0)
    views = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    post_score = Column(Float, default=0)


class Vault(Base):
    __tablename__ = "vaults"
    id = Column(Integer, primary_key=True, index=True)
    date_created = Column(DateTime, default=func.now())
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    privacy = Column(Enum(PrivacyType), nullable=False, default=PrivacyType.PRIVATE)
    previews = Column(String, default="")
    post_count = Column(Integer, default=0)
    user = relationship("User", back_populates="vaults")
    vault_posts = relationship(
        "VaultPost", back_populates="vault", cascade="all, delete-orphan"
    )


class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    date_created = Column(DateTime, default=func.now(), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    content = Column(String, nullable=False)
    post = relationship("Post", back_populates="comments")
    user = relationship("User", back_populates="comments")
    reactions = relationship("Reaction", back_populates="comment", lazy="dynamic")
    likes = Column(Integer, default=0)
    dislikes = Column(Integer, default=0)


class Reaction(Base):
    __tablename__ = "reactions"
    id = Column(Integer, primary_key=True, index=True)
    date_created = Column(DateTime, default=func.now(), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="reactions")
    type = Column(Enum(ReactionType), nullable=False)

    post_id = Column(Integer, ForeignKey("posts.id"), nullable=True)
    comment_id = Column(Integer, ForeignKey("comments.id"), nullable=True)
    post = relationship("Post", back_populates="reactions")
    comment = relationship("Comment", back_populates="reactions")
