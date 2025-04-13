from neo4j import Transaction

from app.models import User


def create_user_(tx: Transaction, user: User):
    tx.run(
        "MERGE (u:User {id: $id}) SET  u.date_created = datetime($date_created), u.username = $username",
        id=user.id,
        date_created=user.date_created,
        username=user.username,
    )


def follow_user_(tx: Transaction, user_id, target_id):
    tx.run(
        """
        MATCH (u:User {id: $user_id}), (t:User {id: $target_id})
        MERGE (u)-[:FOLLOWS]->(t)
    """,
        user_id=user_id,
        target_id=target_id,
    )


def unfollow_user_(tx: Transaction, user_id, target_id):
    tx.run(
        """
        MATCH (:User {id: $user_id})-[f:FOLLOWS]->(:User {id: $target_id})
        DELETE f
    """,
        user_id=user_id,
        target_id=target_id,
    )
