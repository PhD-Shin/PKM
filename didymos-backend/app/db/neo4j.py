"""
Neo4j 연결 관리 (Bolt 사용)
"""
from app.db.neo4j_bolt import Neo4jBoltClient
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Global client instance
_neo4j_client = None


def get_neo4j_client() -> Neo4jBoltClient:
    """
    Neo4j Bolt 클라이언트 반환
    """
    global _neo4j_client
    if _neo4j_client is None:
        try:
            _neo4j_client = Neo4jBoltClient(
                uri=settings.neo4j_uri,
                username=settings.neo4j_username,
                password=settings.neo4j_password,
                database=settings.neo4j_database
            )
            logger.info("Neo4j Bolt client created successfully")
        except Exception as e:
            logger.error(f"Failed to create Neo4j client: {e}")
            raise e
    return _neo4j_client


def init_indices():
    """
    초기 인덱스 생성 및 연결 확인
    """
    try:
        client = get_neo4j_client()

        # 연결 확인
        if client.verify_connectivity():
            logger.info("✓ Neo4j connection verified successfully (Bolt)")
        else:
            logger.error("✗ Neo4j connection verification failed")
            raise Exception("Cannot verify Neo4j connectivity")

        create_indexes(client)
        # 벡터 인덱스 초기화
        from app.services.vector_service import initialize_vector_index
        initialize_vector_index()

        logger.info("Graph connection initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize indices: {e}")
        raise e


def create_indexes(client):
    """
    고유 제약/인덱스 생성 (존재하면 무시)
    """
    constraints = [
        "CREATE CONSTRAINT note_id IF NOT EXISTS FOR (n:Note) REQUIRE n.note_id IS UNIQUE",
        "CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE",
        "CREATE CONSTRAINT vault_id IF NOT EXISTS FOR (v:Vault) REQUIRE v.id IS UNIQUE",
        "CREATE CONSTRAINT topic_id IF NOT EXISTS FOR (t:Topic) REQUIRE t.id IS UNIQUE",
        "CREATE CONSTRAINT project_id IF NOT EXISTS FOR (p:Project) REQUIRE p.id IS UNIQUE",
        "CREATE CONSTRAINT task_id IF NOT EXISTS FOR (t:Task) REQUIRE t.id IS UNIQUE",
    ]
    for cypher in constraints:
        try:
            client.query(cypher, {})
        except Exception as e:
            logger.warning(f"Index creation skipped: {e}")
