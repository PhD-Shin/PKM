"""
Weekly Review 서비스
"""
from typing import List, Dict
import logging
import uuid
import json

logger = logging.getLogger(__name__)


def get_weekly_review(client, vault_id: str) -> Dict:
    return {
        "new_topics": get_new_topics(client, vault_id, days=7),
        "forgotten_projects": get_forgotten_projects(client, vault_id, days=14),
        "overdue_tasks": get_overdue_tasks(client, vault_id),
        "most_active_notes": get_most_active_notes(client, vault_id, days=7),
    }


def get_new_topics(client, vault_id: str, days: int) -> List[Dict]:
    try:
        result = client.query(
            """
            MATCH (v:Vault {id: $vault_id})-[:HAS_NOTE]->(n:Note)-[:MENTIONS]->(t:Topic)
            WHERE datetime(n.updated_at) >= datetime() - duration({days: $days})
            WITH t, COUNT(DISTINCT n) AS mention_count, min(datetime(n.updated_at)) AS first_seen
            RETURN t.id AS name, mention_count, toString(first_seen) AS first_seen
            ORDER BY mention_count DESC
            LIMIT 10
            """,
            {"vault_id": vault_id, "days": days},
        )
        return [
            {
                "name": r.get("name", ""),
                "mention_count": r.get("mention_count", 0),
                "first_seen": r.get("first_seen", ""),
            }
            for r in result or []
        ]
    except Exception as e:
        logger.error(f"Error getting new topics: {e}")
        return []


def get_forgotten_projects(client, vault_id: str, days: int) -> List[Dict]:
    try:
        result = client.query(
            """
            MATCH (v:Vault {id: $vault_id})-[:HAS_NOTE]->(n:Note)-[:MENTIONS]->(p:Project)
            WITH p, max(datetime(n.updated_at)) AS last_updated
            WHERE last_updated < datetime() - duration({days: $days})
            RETURN 
                p.id AS name,
                coalesce(p.status, 'unknown') AS status,
                toString(last_updated) AS last_updated,
                duration.inDays(last_updated, datetime()).days AS days_inactive
            ORDER BY days_inactive DESC
            LIMIT 5
            """,
            {"vault_id": vault_id, "days": days},
        )
        return [
            {
                "name": r.get("name", ""),
                "status": r.get("status", "unknown"),
                "last_updated": r.get("last_updated", ""),
                "days_inactive": r.get("days_inactive", 0),
            }
            for r in result or []
        ]
    except Exception as e:
        logger.error(f"Error getting forgotten projects: {e}")
        return []


def get_overdue_tasks(client, vault_id: str) -> List[Dict]:
    try:
        result = client.query(
            """
            MATCH (v:Vault {id: $vault_id})-[:HAS_NOTE]->(n:Note)-[:MENTIONS]->(t:Task)
            WHERE coalesce(t.status, 'todo') IN ['todo', 'in_progress']
            RETURN 
                t.id AS id,
                coalesce(t.title, t.id) AS title,
                coalesce(t.priority, 'normal') AS priority,
                n.title AS note_title
            ORDER BY 
                CASE coalesce(t.priority, 'normal')
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 3
                    ELSE 4
                END,
                n.updated_at DESC
            LIMIT 10
            """,
            {"vault_id": vault_id},
        )
        return [
            {
                "id": r.get("id", ""),
                "title": r.get("title", ""),
                "priority": r.get("priority", "normal"),
                "note_title": r.get("note_title", ""),
            }
            for r in result or []
        ]
    except Exception as e:
        logger.error(f"Error getting overdue tasks: {e}")
        return []


def get_most_active_notes(client, vault_id: str, days: int) -> List[Dict]:
    try:
        result = client.query(
            """
            MATCH (v:Vault {id: $vault_id})-[:HAS_NOTE]->(n:Note)
            WHERE datetime(n.updated_at) >= datetime() - duration({days: $days})
            RETURN n.title AS title, n.path AS path, COUNT(*) AS update_count
            ORDER BY update_count DESC
            LIMIT 5
            """,
            {"vault_id": vault_id, "days": days},
        )
        return [
            {
                "title": r.get("title", ""),
                "path": r.get("path", ""),
                "update_count": r.get("update_count", 0),
            }
            for r in result or []
        ]
    except Exception as e:
        logger.error(f"Error getting active notes: {e}")
        return []


def save_weekly_review(client, vault_id: str, review_data: Dict) -> str:
    """
    리뷰 결과를 히스토리로 저장
    """
    review_id = str(uuid.uuid4())
    try:
        client.query(
            """
            MERGE (r:WeeklyReview {id: $id})
            SET r.vault_id = $vault_id,
                r.created_at = datetime(),
                r.data = $data
            """,
            {"id": review_id, "vault_id": vault_id, "data": json.dumps(review_data)},
        )
        return review_id
    except Exception as e:
        logger.error(f"Error saving weekly review: {e}")
        return ""


def list_review_history(client, vault_id: str, limit: int = 5) -> List[Dict]:
    try:
        result = client.query(
            """
            MATCH (r:WeeklyReview {vault_id: $vault_id})
            RETURN r.id AS id,
                   toString(r.created_at) AS created_at,
                   r.data AS data
            ORDER BY r.created_at DESC
            LIMIT $limit
            """,
            {"vault_id": vault_id, "limit": limit},
        )
        history: List[Dict] = []
        for row in result or []:
            data = row.get("data")
            try:
                parsed = json.loads(data) if isinstance(data, str) else data
            except Exception:
                parsed = {}
            history.append(
                {
                    "id": row.get("id", ""),
                    "vault_id": vault_id,
                    "created_at": row.get("created_at", ""),
                    "summary": parsed,
                }
            )
        return history
    except Exception as e:
        logger.error(f"Error listing review history: {e}")
        return []
