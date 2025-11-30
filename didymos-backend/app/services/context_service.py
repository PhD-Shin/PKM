"""
Context 생성 서비스 (Hybrid: Graph + Vector)
"""
from typing import Dict, Any, List
import logging

from app.db.neo4j import get_neo4j_client
from app.services.vector_service import find_semantically_similar_notes

logger = logging.getLogger(__name__)


def get_note_context(note_id: str, content_preview: str = "") -> Dict[str, Any]:
    """
    노트의 전체 컨텍스트 반환
    """
    client = get_neo4j_client()

    # 1. 구조적 데이터
    topics = get_topics_for_note(client, note_id)
    projects = get_projects_for_note(client, note_id)
    tasks = get_tasks_in_note(client, note_id)

    # 2. 추천 (Hybrid: Graph + Vector)
    graph_related = find_structurally_related_notes(client, note_id)
    query = content_preview if content_preview else note_id
    vector_related = find_semantically_similar_notes(query, limit=3)

    related_notes = merge_related_notes(
        graph_related, vector_related, current_note_id=note_id
    )

    return {
        "topics": topics,
        "projects": projects,
        "tasks": tasks,
        "related_notes": related_notes,
    }


def merge_related_notes(
    graph_list: List[Dict[str, Any]],
    vector_list: List[Dict[str, Any]],
    current_note_id: str,
) -> List[Dict[str, Any]]:
    """
    두 리스트 병합 (중복 제거)
    """
    seen = {current_note_id}
    merged: List[Dict[str, Any]] = []

    for note in graph_list:
        if note.get("note_id") and note["note_id"] not in seen:
            merged.append(note)
            seen.add(note["note_id"])

    for note in vector_list:
        if note.get("note_id") and note["note_id"] not in seen:
            merged.append(note)
            seen.add(note["note_id"])

    return merged[:5]


def get_topics_for_note(client, note_id: str) -> List[Dict[str, Any]]:
    """노트가 언급한 토픽 조회"""
    try:
        cypher = """
        MATCH (n:Note {note_id: $note_id})-[r:MENTIONS]->(t:Topic)
        RETURN t.id AS id,
               coalesce(t.name, t.id) AS name,
               COUNT(r) AS mention_count
        """
        records = client.query(cypher, {"note_id": note_id}) or []

        topics: List[Dict[str, Any]] = []
        for record in records:
            mention_count = record.get("mention_count", 0) or 0
            importance_score = round(min(mention_count / 5.0, 1.0), 2)
            topics.append(
                {
                    "id": record.get("id", ""),
                    "name": record.get("name", ""),
                    "mention_count": mention_count,
                    "importance_score": importance_score,
                }
            )
        return topics
    except Exception as e:
        logger.error(f"Failed to fetch topics for note {note_id}: {e}")
        return []


def get_projects_for_note(client, note_id: str) -> List[Dict[str, Any]]:
    """노트와 연결된 프로젝트 조회"""
    try:
        cypher = """
        MATCH (n:Note {note_id: $note_id})-[:MENTIONS]->(p:Project)
        RETURN p.id AS id,
               coalesce(p.name, p.id) AS name,
               coalesce(p.status, 'unknown') AS status,
               toString(coalesce(p.updated_at, p.created_at, datetime())) AS updated_at
        """
        records = client.query(cypher, {"note_id": note_id}) or []

        projects: List[Dict[str, Any]] = []
        for record in records:
            projects.append(
                {
                    "id": record.get("id", ""),
                    "name": record.get("name", ""),
                    "status": record.get("status", "unknown"),
                    "updated_at": record.get("updated_at", ""),
                }
            )
        return projects
    except Exception as e:
        logger.error(f"Failed to fetch projects for note {note_id}: {e}")
        return []


def get_tasks_in_note(client, note_id: str) -> List[Dict[str, Any]]:
    """노트 내 태스크 조회"""
    try:
        cypher = """
        MATCH (n:Note {note_id: $note_id})-[:MENTIONS]->(t:Task)
        RETURN t.id AS id,
               coalesce(t.title, t.id) AS title,
               coalesce(t.status, 'unknown') AS status,
               coalesce(t.priority, 'normal') AS priority
        """
        records = client.query(cypher, {"note_id": note_id}) or []

        tasks: List[Dict[str, Any]] = []
        for record in records:
            tasks.append(
                {
                    "id": record.get("id", ""),
                    "title": record.get("title", ""),
                    "status": record.get("status", "unknown"),
                    "priority": record.get("priority", "normal"),
                }
            )
        return tasks
    except Exception as e:
        logger.error(f"Failed to fetch tasks for note {note_id}: {e}")
        return []


def find_structurally_related_notes(
    client, note_id: str, limit: int = 3
) -> List[Dict[str, Any]]:
    """공통 Topic 기반 유사 노트 찾기 (Graph)"""
    try:
        cypher = """
        MATCH (n:Note {note_id: $note_id})-[:MENTIONS]->(t:Topic)<-[:MENTIONS]-(related:Note)
        WHERE n <> related
        WITH related, COUNT(DISTINCT t) AS common_topics
        ORDER BY common_topics DESC
        LIMIT $limit
        RETURN related.note_id AS note_id,
               related.title AS title,
               related.path AS path,
               common_topics
        """
        records = client.query(cypher, {"note_id": note_id, "limit": limit}) or []

        related: List[Dict[str, Any]] = []
        for record in records:
            common_topics = record.get("common_topics", 0) or 0
            similarity = round(min(common_topics / 5.0, 1.0), 2)
            related.append(
                {
                    "note_id": record.get("note_id", ""),
                    "title": record.get("title", ""),
                    "path": record.get("path", ""),
                    "similarity": similarity,
                    "reason": "structural",
                }
            )
        return related
    except Exception as e:
        logger.error(f"Graph search error for note {note_id}: {e}")
        return []
