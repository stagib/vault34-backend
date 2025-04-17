from neo4j import Transaction

from app.models import Vault


def create_vault_(tx: Transaction, vault: Vault):
    tx.run(
        """
        MATCH (u:User {id: $user_id})
        MERGE (v:Vault {id: $id}) 
        SET v.date_created = datetime($date_created)
        SET v.title = $title
        SET v.score = $score
        MERGE (u)-[:CREATED]->(v)
    """,
        user_id=vault.user_id,
        id=vault.id,
        date_created=vault.date_created,
        title=vault.title,
        score=vault.likes + vault.dislikes,
    )


def update_vault_(tx: Transaction, vault: Vault):
    tx.run(
        """
        MATCH (v:Vault {id: $id}) 
        SET v.title = $title
        SET v.score = $score
    """,
        id=vault.id,
        title=vault.title,
        score=vault.likes + vault.dislikes,
    )


def delete_vault_(tx: Transaction, vault_id: int):
    tx.run(
        """
        MATCH (v:Vault {id: $id})
        DETACH DELETE v
    """,
        id=vault_id,
    )


def add_post_(tx: Transaction, vault_id: int, post_id: int):
    tx.run(
        """
        MATCH (v:Vault {id: $vault_id})
        MATCH (p:Post {id: $post_id})
        MERGE (v)-[:CONTAINS]->(p)
    """,
        vault_id=vault_id,
        post_id=post_id,
    )


def remove_post_(tx: Transaction, vault_id: int, post_id: int):
    tx.run(
        """
        MATCH (:Vault {id: $vault_id})-[c:CONTAINS]->(:Post {id: $post_id})
        DELETE c
    """,
        vault_id=vault_id,
        post_id=post_id,
    )


def create_reaction_(tx: Transaction, user_id: int, vault_id: int, type: str):
    results = tx.run(
        """
            MATCH (u:User {id: $user_id}), (v:Vault {id: $vault_id})
            MERGE (u)-[r:REACTED]->(v)
            WITH r, r.type AS type
            SET r.type = $type
            RETURN type
        """,
        user_id=user_id,
        vault_id=vault_id,
        type=type,
    ).single()

    return results.get("type") if results else None


def invite_user_(tx: Transaction, user_id: int, vault_id: int):
    tx.run(
        """
            MATCH (u:User {id: $user_id}), (v:Vault {id: $vault_id})
            MERGE (v)-[:INVITED]->(u)
        """,
        user_id=user_id,
        vault_id=vault_id,
    )


def accept_invite(tx: Transaction, user_id: int, vault_id: int):
    tx.run(
        """
            MATCH (u:User {id: $user_id})-[i:INVITED]->(v:Vault {id: $vault_id})
            DELETE i
            MERGE (u)-[:JOINED]->(v)
        """,
        user_id=user_id,
        vault_id=vault_id,
    )


def decline_invite(tx: Transaction, user_id: int, vault_id: int):
    tx.run(
        """
            MATCH (:User {id: $user_id})-[i:INVITED]->(:Vault {id: $vault_id})
            DELETE i
        """,
        user_id=user_id,
        vault_id=vault_id,
    )
