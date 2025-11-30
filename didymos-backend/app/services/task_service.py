"""
Task 관리 서비스
"""
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def update_task(client, task_id: str, updates: Dict[str, Any]) -> bool:
    """
    Task 상태/우선순위 업데이트
    """
    if not updates:
        return True

    set_clauses = []
    params: Dict[str, Any] = {"task_id": task_id}

    if "status" in updates:
        set_clauses.append("t.status = $status")
        params["status"] = updates["status"]

    if "priority" in updates:
        set_clauses.append("t.priority = $priority")
        params["priority"] = updates["priority"]

    set_clause = ", ".join(set_clauses)

    try:
        result = client.query(
            f"""
            MATCH (t:Task {{id: $task_id}})
            SET {set_clause}, t.updated_at = datetime()
            RETURN t.id AS id
            """,
            params,
        )

        success = bool(result and result[0].get("id"))
        if success:
            logger.info(f"✅ Task updated: {task_id}")
        return success
    except Exception as e:
        logger.error(f"Error updating task {task_id}: {e}")
        return False


def list_tasks(
    client,
    vault_id: str,
    status: Optional[str] = None,
    priority: Optional[str] = None,
) -> List[Dict]:
    """
    Vault의 Task 목록 조회 (MENTIONS 관계 기반)
    """
    where_clauses = []
    params: Dict[str, Any] = {"vault_id": vault_id}

    if status:
        where_clauses.append("t.status = $status")
        params["status"] = status

    if priority:
        where_clauses.append("t.priority = $priority")
        params["priority"] = priority

    where_clause = ""
    if where_clauses:
        where_clause = "AND " + " AND ".join(where_clauses)

    try:
        result = client.query(
            f"""
            MATCH (v:Vault {{id: $vault_id}})-[:HAS_NOTE]->(n:Note)-[:MENTIONS]->(t:Task)
            WHERE 1=1 {where_clause}
            RETURN 
                t.id AS id,
                COALESCE(t.title, t.id) AS title,
                COALESCE(t.status, 'todo') AS status,
                COALESCE(t.priority, 'normal') AS priority,
                n.note_id AS note_id,
                n.title AS note_title
            ORDER BY 
                CASE COALESCE(t.priority, 'normal')
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 3
                    ELSE 4
                END,
                t.updated_at DESC
            """,
            params,
        )

        tasks: List[Dict[str, Any]] = []
        for record in result or []:
            tasks.append(
                {
                    "id": record.get("id", ""),
                    "title": record.get("title", ""),
                    "status": record.get("status", "todo"),
                    "priority": record.get("priority", "normal"),
                    "note_id": record.get("note_id", ""),
                    "note_title": record.get("note_title", ""),
                }
            )

        logger.info(f"Found {len(tasks)} tasks for vault {vault_id}")
        return tasks
    except Exception as e:
        logger.error(f"Error listing tasks for vault {vault_id}: {e}")
        return []
