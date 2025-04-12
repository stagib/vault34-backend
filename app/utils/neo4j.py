from neo4j import Transaction


def create_user(tx: Transaction, id: int, username: str):
    tx.run(
        "MERGE (u:User {id: $id}) SET u.username = $username",
        id=id,
        username=username,
    )


def create_post(tx: Transaction, post):
    tx.run(
        "MERGE (p:Post {id: $id}) SET p.score = $score",
        id=post.id,
        score=post.score,
    )


def create_reaction(tx: Transaction, user_id: int, post_id: int, type: str):
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


def create_vault(tx: Transaction, user_id: int, title: str):
    pass
