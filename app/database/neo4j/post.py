from neo4j import Transaction

from app.models import Post


def create_post_(tx: Transaction, post: Post):
    tx.run(
        """
        MERGE (p:Post {id: $id}) 
        SET p.date_created = datetime($date_created), p.score = $score 
    """,
        id=post.id,
        date_created=post.date_created,
        score=post.score,
    )


def update_post_(tx: Transaction, post: Post):
    tx.run(
        """
        MATCH (p:Post {id: $id}) 
        SET p.score = $score 
    """,
        id=post.id,
        score=post.score,
    )


def create_reaction_(tx: Transaction, user_id: int, post_id: int, type: str):
    tx.run(
        """
        MATCH (u:User {id: $user_id})
        MATCH (p:Post {id: $post_id})
        MERGE (u)-[r:REACTED]->(p)
        SET r.type = $type
    """,
        user_id=user_id,
        post_id=post_id,
        type=type,
    )
