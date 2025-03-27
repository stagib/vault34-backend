from sqlalchemy import func, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy import Enum
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.database import Base
from app.types import ReactionType


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    date_created = Column(DateTime, default=func.now(), nullable=False)
    username = Column(String, nullable=False)
    password = Column(String, nullable=False)
    reactions = relationship("Reaction", back_populates="user")
    comments = relationship("Comment", back_populates="user")


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

    embedding = Column(Vector(512))
    """ views = Column(Integer)
    view_time = Column(Integer)
    saves = Column(Integer)
    reactions = Column(Integer) """

    reactions = relationship("Reaction", back_populates="post", lazy="dynamic")
    comments = relationship("Comment", back_populates="post")

    @property
    def likes(self) -> int:
        return self.reactions.filter(Reaction.type == ReactionType.LIKE).count()

    @property
    def dislikes(self) -> int:
        return self.reactions.filter(Reaction.type == ReactionType.DISLIKE).count()


class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    date_created = Column(DateTime, default=func.now(), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    content = Column(String, nullable=False)
    post = relationship("Post", back_populates="comments")
    user = relationship("User", back_populates="comments")
    reactions = relationship("Reaction", back_populates="comment")


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
