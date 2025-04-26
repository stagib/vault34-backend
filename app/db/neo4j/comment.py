from neo4j import Transaction

from app.models import Comment


def create_comment_(tx: Transaction, comment: Comment):
    tx.run(
        """
        MATCH (u:User {id: $user_id}), (p:Post {id: $post_id})
        MERGE (c:Comment {id: $id}) 
        SET c.date_created = datetime($date_created)
        SET c.content = $content
        MERGE (u)-[:WROTE]->(c)
        MERGE (c)-[:ON]->(p)
    """,
        user_id=comment.user_id,
        post_id=comment.post_id,
        id=comment.id,
        date_created=comment.date_created,
        content=comment.content,
    )


def delete_comment_(tx: Transaction, comment_id: int):
    tx.run(
        """
        MATCH (c:Comment {id: $id})
        DETACH DELETE c
    """,
        id=comment_id,
    )


def create_reaction_(
    tx: Transaction, user_id: int, comment_id: int, type: str
):
    tx.run(
        """
        MATCH (u:User {id: $user_id}), (c:Comment {id: $comment_id})
        MERGE (u)-[r:REACTED]->(c)
        SET r.type = $type
    """,
        user_id=user_id,
        comment_id=comment_id,
        type=type,
    )
