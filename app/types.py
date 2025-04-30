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
    RELEVANCE = "relevance"
    TRENDING = "trending"
    POPULAR = "popular"
    POPULAR_WEEK = "popular_week"
    POPULAR_MONTH = "popular_month"
    POPULAR_YEAR = "popular_year"
    NEWEST = "newest"
