from enum import Enum


class ReactionType(Enum):
    LIKE = "like"
    DISLIKE = "dislike"
    NONE = "none"


class TargetType(Enum):
    POST = "post"
    COMMENT = "comment"
    VAULT = "vault"


class PrivacyType(Enum):
    PRIVATE = "private"
    PUBLIC = "public"


class RatingType(Enum):
    EXPLICIT = "explicit"
    QUESTIONABLE = "questionable"


class OrderType(Enum):
    TRENDING = "trending"
    views = "views"
    LIKES = "likes"
    NEWEST = "newest"
    OLDEST = "oldest"
