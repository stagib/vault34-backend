from neo4j import Transaction

from app.db import driver


def log_search_(search_id, query, user):
    def log_user_search(tx: Transaction, id, q, user_id):
        tx.run(
            """
                MATCH (s:Search {query: $query}) 
                MATCH (u:User {user_id: $user_id})
                MERGE (u)-[t:SEARCHED]->(s)
                ON CREATE SET t.count = 1
                ON MATCH SET t.count = t.count + 1
                SET t.search_id = $id
        """,
            parameters={"query": q, "id": id, "user_id": user_id},
        )

    def log_search(tx: Transaction, q):
        tx.run(
            """
                MERGE (s:Search {query: $query}) 
                ON CREATE SET s.count = 1
                ON MATCH SET s.count = s.count + 1
            """,
            parameters={"query": q},
        )

    with driver.session() as session:
        session.execute_write(log_search, query)
        if user:
            session.execute_write(log_user_search, search_id, query, user.id)
    return search_id


def log_search_click_(search_id, post_id):
    def log_search_click(tx: Transaction, search_id, post_id):
        tx.run(
            """
                MATCH (:User)-[t:SEARCHED {search_id: $search_id}]->(s:Search)
                MATCH (p:Post {post_id: $post_id})
                MERGE (s)-[c:CLICKED]->(p)
                ON CREATE SET c.count = 1
                ON MATCH SET c.count = c.count + 1
                REMOVE t.search_id

            """,
            parameters={"search_id": search_id, "post_id": post_id},
        )

    with driver.session() as session:
        session.execute_write(log_search_click, search_id, post_id)
