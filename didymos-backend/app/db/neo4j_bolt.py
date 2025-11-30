"""
Neo4j Bolt 드라이버 클라이언트
HTTP Query API 대신 Bolt를 사용해 쿼리를 실행합니다.
"""
from typing import List, Dict, Any
import logging
from neo4j import GraphDatabase, Driver

logger = logging.getLogger(__name__)


class Neo4jBoltClient:
    """Neo4j Bolt 쿼리 클라이언트"""

    def __init__(self, uri: str, username: str, password: str, database: str = "neo4j"):
        self.database = database
        self.uri = self._normalize_uri(uri)
        self.driver: Driver = GraphDatabase.driver(self.uri, auth=(username, password))
        logger.info(f"Neo4j Bolt Client initialized: {self.uri} / db={database}")

    def query(self, cypher: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Cypher 쿼리를 실행하고 dict 리스트로 반환
        """
        params = params or {}
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(cypher, params)
                return [record.data() for record in result]
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            raise

    def verify_connectivity(self) -> bool:
        """연결 확인"""
        try:
            self.driver.verify_connectivity()
            return True
        except Exception as e:
            logger.error(f"Connectivity check failed: {e}")
            return False

    def close(self):
        """드라이버 종료"""
        try:
            self.driver.close()
        except Exception as e:
            logger.error(f"Error closing driver: {e}")

    @staticmethod
    def _normalize_uri(uri: str) -> str:
        """
        AuraDB 호환을 위해 인증서 검증을 완화한 bolt+ssc 스킴으로 변환
        (neo4j+s → bolt+ssc)
        """
        if uri.startswith("neo4j+s://"):
            return uri.replace("neo4j+s://", "bolt+ssc://")
        if uri.startswith("neo4j://"):
            return uri.replace("neo4j://", "bolt://")
        return uri
