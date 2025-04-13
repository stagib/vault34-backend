from neo4j import Transaction


def create_user_(tx: Transaction, user):
    tx.run(
        "MERGE (u:User {id: $id}) SET  u.date_created = datetime($date_created), u.username = $username",
        id=user.id,
        date_created=user.date_created,
        username=user.username,
    )
