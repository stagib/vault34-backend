from enum import Enum


class ReactionType(Enum):
    LIKE = "like"
    DISLIKE = "dislike"
    NONE = "none"


class PrivacyType(Enum):
    PRIVATE = "private"
    PUBLIC = "public"
