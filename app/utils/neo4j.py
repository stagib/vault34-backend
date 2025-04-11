from neo4j import Transaction


def create_user(tx: Transaction, id: int, username: str):
    tx.run(
        "MERGE (u:User {id: $id}) SET u.username = $username",
        id=id,
        username=username,
    )


def create_post(tx: Transaction, id: int):
    tx.run("MERGE (p:Post {id: $id}) SET p.title = $title", id=id)
