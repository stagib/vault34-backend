from neo4j import Transaction

from app.models import Vault


def create_vault_(tx: Transaction, vault: Vault):
    tx.run(
        """
        MATCH (u:User {id: $user_id})
        MERGE (v:Vault {id: $id}) 
        SET v.date_created = datetime($date_created), v.title = $title
        MERGE (u)-[:CREATED]->(v)
    """,
        user_id=vault.user_id,
        id=vault.id,
        date_created=vault.date_created,
        title=vault.title,
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
