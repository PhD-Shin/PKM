"""
Neo4j HTTP Query API 클라이언트
Bolt 프로토콜 대신 HTTP API를 사용
"""
import requests
from requests.auth import HTTPBasicAuth
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class Neo4jHTTPClient:
    """Neo4j HTTP Query API 클라이언트"""

    def __init__(self, uri: str, username: str, password: str, database: str = "neo4j"):
        """
        Args:
            uri: Neo4j URI (neo4j+s://xxxxx.databases.neo4j.io)
            username: Neo4j username
            password: Neo4j password
            database: Database name (default: neo4j)
        """
        # neo4j+s://xxxxx.databases.neo4j.io -> https://xxxxx.databases.neo4j.io
        self.base_url = uri.replace("neo4j+s://", "https://").replace("neo4j://", "http://")
        self.username = username
        self.password = password
        self.database = database
        self.query_url = f"{self.base_url}/db/{database}/query/v2"

        logger.info(f"Neo4j HTTP Client initialized: {self.query_url}")

    def query(self, cypher: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Cypher 쿼리 실행

        Args:
            cypher: Cypher 쿼리 문자열
            params: 쿼리 파라미터 (optional)

        Returns:
            결과 레코드 리스트
        """
        try:
            payload = {"statement": cypher}
            if params:
                payload["parameters"] = params

            response = requests.post(
                self.query_url,
                auth=HTTPBasicAuth(self.username, self.password),
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                json=payload,
                timeout=30
            )

            if response.status_code in [200, 202]:
                result = response.json()
                data = result.get("data", {})
                fields = data.get("fields", [])
                values = data.get("values", [])

                # Convert to list of dicts
                records = []
                for row in values:
                    record = dict(zip(fields, row))
                    records.append(record)

                return records
            else:
                logger.error(f"Query failed: {response.status_code} - {response.text}")
                raise Exception(f"Query failed: {response.status_code}")

        except Exception as e:
            logger.error(f"Query execution error: {e}")
            raise e

    def verify_connectivity(self) -> bool:
        """연결 확인"""
        try:
            result = self.query("RETURN 1 as num")
            return len(result) > 0 and result[0].get("num") == 1
        except Exception as e:
            logger.error(f"Connectivity check failed: {e}")
            return False
