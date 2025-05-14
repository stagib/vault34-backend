from neo4j import Transaction

""" from app.db import driver """
from app.models import Post


def create_posts_(tx: Transaction, posts: list[Post]):
    tx.run(
        """
        UNWIND $posts AS post
        MERGE (p:Post {post_id: post.id}) 
        SET p.date_created = datetime(post.date_created), p.score = post.score 
    """,
        posts=posts,
    )


def update_post_(tx: Transaction, post: Post):
    tx.run(
        """
        MATCH (p:Post {post_id: $id}) 
        SET p.score = $score 
    """,
        id=post.id,
        score=post.score,
    )


def react_to_post_(tx: Transaction, user_id: int, post_id: int, type: str):
    tx.run(
        """
        MATCH (u:User {user_id: $user_id})
        MATCH (p:Post {post_id: $post_id})
        MERGE (u)-[r:REACTED_TO_POST]->(p)
        SET r.type = $type
    """,
        user_id=user_id,
        post_id=post_id,
        type=type,
    )


def get_top_tags_(post_id):
    def get_top_tags(tx: Transaction, post_id: int):
        results = tx.run(
            """
            MATCH (s:Search)-[c:CLICKED]-(:Post {post_id: $post_id})
            RETURN s.query AS query
            ORDER BY c.count DESC
            LIMIT 5
        """,
            post_id=post_id,
        )
        return [record["query"] for record in results]

    with driver.session() as session:
        results = session.execute_read(get_top_tags, post_id)
        return results
