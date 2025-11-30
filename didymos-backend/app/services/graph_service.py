"""
Neo4j 그래프 서비스
Bolt 클라이언트를 사용한 그래프 데이터 관리
"""
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def upsert_note(
    client,
    user_id: str,
    vault_id: str,
    note_data: Dict[str, Any],
) -> bool:
    """
    User, Vault, Note 노드를 생성하고 관계를 설정

    Args:
        client: Neo4j 클라이언트 (Bolt)
        user_id: 사용자 ID
        vault_id: Vault ID
        note_data: 노트 데이터 (note_id, title, path, tags, created_at, updated_at 포함)

    Returns:
        성공 여부
    """
    try:
        cypher = """
        MERGE (u:User {id: $user_id})
          ON CREATE SET u.created_at = datetime()

        MERGE (v:Vault {id: $vault_id})
          ON CREATE SET v.created_at = datetime()
        MERGE (u)-[:OWNS]->(v)

        MERGE (n:Note {note_id: $note_id})
          ON CREATE SET
            n.title = $title,
            n.path = $path,
            n.created_at = $created_at,
            n.updated_at = $updated_at,
            n.tags = $tags
          ON MATCH SET
            n.title = $title,
            n.path = $path,
            n.updated_at = $updated_at,
            n.tags = $tags

        MERGE (v)-[:HAS_NOTE]->(n)
        RETURN n.note_id AS note_id
        """

        params = {
            "user_id": user_id,
            "vault_id": vault_id,
            "note_id": note_data["note_id"],
            "title": note_data["title"],
            "path": note_data["path"],
            "tags": note_data.get("tags", []),
            "created_at": note_data["created_at"],
            "updated_at": note_data["updated_at"],
        }

        result = client.query(cypher, params)

        if result and len(result) > 0:
            logger.info(f"✅ Note saved: {result[0].get('note_id')}")
            return True
        return False

    except Exception as e:
        logger.error(f"Error saving note: {e}")
        return False


def get_note(client, note_id: str) -> Optional[Dict[str, Any]]:
    """
    노트 ID로 노트 조회

    Args:
        client: Neo4j 클라이언트 (Bolt)
        note_id: 노트 ID

    Returns:
        노트 데이터 딕셔너리 또는 None
    """
    try:
        cypher = """
        MATCH (n:Note {note_id: $note_id})
        RETURN n.note_id AS note_id,
               n.title AS title,
               n.path AS path,
               n.tags AS tags,
               toString(n.created_at) AS created_at,
               toString(n.updated_at) AS updated_at
        """

        result = client.query(cypher, {"note_id": note_id})

        if result and len(result) > 0:
            return result[0]
        return None

    except Exception as e:
        logger.error(f"Error fetching note: {e}")
        return None


def get_all_notes(client, user_id: str, vault_id: str) -> list:
    """
    특정 Vault의 모든 노트 조회

    Args:
        client: Neo4j 클라이언트 (Bolt)
        user_id: 사용자 ID
        vault_id: Vault ID

    Returns:
        노트 리스트
    """
    try:
        cypher = """
        MATCH (u:User {id: $user_id})-[:OWNS]->(v:Vault {id: $vault_id})-[:HAS_NOTE]->(n:Note)
        RETURN n.note_id AS note_id,
               n.title AS title,
               n.path AS path,
               n.tags AS tags,
               toString(n.created_at) AS created_at,
               toString(n.updated_at) AS updated_at
        ORDER BY n.updated_at DESC
        """

        result = client.query(cypher, {"user_id": user_id, "vault_id": vault_id})
        return result if result else []

    except Exception as e:
        logger.error(f"Error fetching notes: {e}")
        return []
