from neo4j import Transaction

from app.database import driver
from app.models import Vault


def get_user_vaults_(tx: Transaction, user_id: int, limit: int = 24):
    results = tx.run(
        """
        MATCH (:User {id: $user_id})-[:CREATED]->(v:Vault)
        RETURN v.id AS vault_id
        LIMIT $limit
    """,
        user_id=user_id,
        limit=limit,
    )
    return [record["vault_id"] for record in results]


def get_reacted_vaults_(tx: Transaction, user_id: int, limit: int = 10):
    results = tx.run(
        """
        MATCH (:User {id: $user_id})-[:REACTED]->(v:Vault)
        RETURN v.id AS vault_id
        LIMIT $limit
    """,
        user_id=user_id,
        limit=limit,
    )
    return [record["vault_id"] for record in results]


def get_connected_vaults_(tx: Transaction, vault_ids: list[int]):
    results = tx.run(
        """
        // Depth 1
        MATCH (v1:Vault)-[:CONTAINS]->(:Post)<-[:CONTAINS]-(v2:Vault)
        WHERE v1.id IN $vault_ids AND v1 <> v2
        RETURN v2.id AS vault_id
        LIMIT 10

        UNION

        // Depth 2
        MATCH (v1:Vault)-[:CONTAINS]->(:Post)<-[:CONTAINS]-(v2:Vault),
        (v2)-[:CONTAINS]->(:Post)<-[:CONTAINS]-(v3:Vault)
        WHERE v1.id IN $vault_ids AND v1 <> v2 AND v1 <> v3 AND v2 <> v3
        RETURN v3.id AS vault_id
        LIMIT 5
    """,
        vault_ids=vault_ids,
    )
    return [record["vault_id"] for record in results]


def create_vault_(tx: Transaction, vault: Vault):
    tx.run(
        """
        MATCH (u:User {id: $user_id})
        MERGE (v:Vault {id: $id}) 
        SET v.date_created = datetime($date_created)
        SET v.title = $title
        SET v.score = $score
        SET v.privacy = $privacy
        MERGE (u)-[:CREATED]->(v)
    """,
        user_id=vault.user_id,
        id=vault.id,
        date_created=vault.date_created,
        title=vault.title,
        score=vault.likes + vault.dislikes,
        privacy=vault.privacy.value,
    )


def update_vault_(tx: Transaction, vault: Vault):
    tx.run(
        """
        MATCH (v:Vault {id: $id}) 
        SET v.title = $title
        SET v.score = $score
        SET v.privacy = $privacy
    """,
        id=vault.id,
        title=vault.title,
        score=vault.likes + vault.dislikes,
        privacy=vault.privacy.value,
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


def react_to_vault_(tx: Transaction, user_id: int, vault_id: int, type: str):
    tx.run(
        """
        MATCH (u:User {id: $user_id}), (v:Vault {id: $vault_id})
        MERGE (u)-[r:REACTED_TO_VAULT]->(v)
        WITH r, r.type AS type
        SET r.type = $type
    """,
        user_id=user_id,
        vault_id=vault_id,
        type=type,
    )


def get_user_reaction_(user_id: int, vault_id):
    with driver.session() as session:
        result = session.run(
            """
            MATCH (:User {id: $user_id})-[r:REACTED]->(:Vault {id: $vault_id})
            RETURN r.type AS type
        """,
            user_id=user_id,
            vault_id=vault_id,
        ).single()
        return result["type"] if result else "none"


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
