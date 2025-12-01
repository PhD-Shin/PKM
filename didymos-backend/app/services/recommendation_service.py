"""
의사결정 추천 서비스
- 연결 제안: 유사한 노트 추천
- Task 우선순위: 중요도 + 마감일 기반
- 놓친 연결: 같은 Topic을 다루지만 연결 안 된 노트
"""
from typing import Dict, List, Any, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def recommend_connections_for_note(
    note_id: str,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    특정 노트와 연결하면 좋을 노트 추천 (벡터 유사도 기반)

    Args:
        note_id: 대상 노트 ID
        limit: 추천 개수

    Returns:
        추천 노트 리스트 (유사도 포함)
    """
    from app.db.neo4j import get_neo4j_client

    client = get_neo4j_client()

    # 벡터 유사도 검색
    cypher = """
    MATCH (source:Note {note_id: $note_id})
    CALL db.index.vector.queryNodes('note_embeddings', $top_k, source.embedding)
    YIELD node AS similar, score
    WHERE similar.note_id <> $note_id
      AND NOT (source)-[:MENTIONS|:RELATES_TO]-(similar)
    RETURN similar.note_id AS note_id,
           similar.title AS title,
           similar.path AS path,
           score
    ORDER BY score DESC
    LIMIT $limit
    """

    try:
        result = client.query(cypher, {
            "note_id": note_id,
            "top_k": limit * 2,  # 여유있게 가져와서 필터링
            "limit": limit
        })

        recommendations = []
        for row in result:
            recommendations.append({
                "note_id": row["note_id"],
                "title": row.get("title", row["note_id"]),
                "path": row.get("path", row["note_id"]),
                "similarity": round(float(row["score"]), 4),
                "reason": "Similar content"
            })

        return recommendations

    except Exception as e:
        logger.error(f"Failed to get recommendations: {e}")
        return []


def prioritize_tasks(
    user_id: str,
    vault_id: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Task 우선순위 계산 (중요도 + 마감일 + 연결성)

    우선순위 점수 = priority_weight + due_weight + connection_weight
    - priority: high=3, medium=2, low=1
    - due_date: 오늘/내일=3, 이번주=2, 이후=1, 없음=0
    - connections: 많이 연결된 노트와 관련된 Task일수록 높음

    Args:
        user_id: 사용자 ID
        vault_id: Vault ID
        limit: 반환할 Task 수

    Returns:
        우선순위 정렬된 Task 리스트
    """
    from app.db.neo4j import get_neo4j_client

    client = get_neo4j_client()

    cypher = """
    MATCH (u:User {id: $user_id})-[:OWNS]->(v:Vault {id: $vault_id})
    MATCH (v)-[:HAS_NOTE]->(n:Note)-[r:HAS_TASK]->(t:Task)
    WHERE t.status IN ['todo', 'in_progress']
    OPTIONAL MATCH (n)-[rels]-()
    WITH t, n,
         count(DISTINCT rels) AS connection_count,
         t.priority AS priority,
         t.due_date AS due_date,
         t.title AS title,
         t.status AS status,
         n.note_id AS note_id,
         n.title AS note_title

    // Priority weight
    WITH t, n, connection_count, title, status, note_id, note_title, due_date,
         CASE priority
           WHEN 'high' THEN 3.0
           WHEN 'medium' THEN 2.0
           WHEN 'low' THEN 1.0
           ELSE 1.5
         END AS priority_weight

    // Due date weight (계산은 애플리케이션에서 수행)
    RETURN t.id AS task_id,
           title,
           status,
           priority,
           due_date,
           note_id,
           note_title,
           connection_count,
           priority_weight
    ORDER BY priority_weight DESC, connection_count DESC
    LIMIT $limit
    """

    try:
        result = client.query(cypher, {
            "user_id": user_id,
            "vault_id": vault_id,
            "limit": limit * 2  # 여유있게 가져와서 재정렬
        })

        tasks = []
        today = datetime.now().date()

        for row in result:
            due_weight = 0.0
            urgency_label = "No deadline"

            if row.get("due_date"):
                try:
                    due_date = datetime.fromisoformat(row["due_date"]).date()
                    days_until = (due_date - today).days

                    if days_until < 0:
                        due_weight = 5.0
                        urgency_label = f"Overdue ({abs(days_until)}d)"
                    elif days_until == 0:
                        due_weight = 4.0
                        urgency_label = "Due today"
                    elif days_until == 1:
                        due_weight = 3.5
                        urgency_label = "Due tomorrow"
                    elif days_until <= 7:
                        due_weight = 2.5
                        urgency_label = f"Due in {days_until}d"
                    elif days_until <= 30:
                        due_weight = 1.5
                        urgency_label = f"Due in {days_until}d"
                    else:
                        due_weight = 0.5
                        urgency_label = f"Due in {days_until}d"
                except:
                    pass

            connection_weight = min(row.get("connection_count", 0) * 0.1, 2.0)
            priority_weight = row.get("priority_weight", 1.5)

            total_score = priority_weight + due_weight + connection_weight

            tasks.append({
                "task_id": row.get("task_id"),
                "title": row.get("title", "Untitled task"),
                "status": row.get("status", "todo"),
                "priority": row.get("priority", "medium"),
                "due_date": row.get("due_date"),
                "note_id": row.get("note_id"),
                "note_title": row.get("note_title"),
                "score": round(total_score, 2),
                "urgency": urgency_label,
                "connections": row.get("connection_count", 0)
            })

        # 점수로 재정렬
        tasks.sort(key=lambda x: x["score"], reverse=True)

        return tasks[:limit]

    except Exception as e:
        logger.error(f"Failed to prioritize tasks: {e}")
        return []


def find_missing_connections(
    user_id: str,
    vault_id: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    놓친 연결 찾기
    - 같은 Topic을 언급하지만 서로 연결되지 않은 노트 쌍 찾기

    Args:
        user_id: 사용자 ID
        vault_id: Vault ID
        limit: 반환할 연결 제안 수

    Returns:
        연결 제안 리스트
    """
    from app.db.neo4j import get_neo4j_client

    client = get_neo4j_client()

    cypher = """
    MATCH (u:User {id: $user_id})-[:OWNS]->(v:Vault {id: $vault_id})
    MATCH (v)-[:HAS_NOTE]->(n1:Note)-[:MENTIONS]->(topic:Topic)<-[:MENTIONS]-(n2:Note)
    WHERE n1.note_id < n2.note_id
      AND NOT (n1)-[:MENTIONS|:RELATES_TO]-(n2)
    WITH n1, n2, collect(DISTINCT topic.name) AS shared_topics
    WHERE size(shared_topics) >= 2
    RETURN n1.note_id AS note1_id,
           n1.title AS note1_title,
           n2.note_id AS note2_id,
           n2.title AS note2_title,
           shared_topics,
           size(shared_topics) AS topic_count
    ORDER BY topic_count DESC
    LIMIT $limit
    """

    try:
        result = client.query(cypher, {
            "user_id": user_id,
            "vault_id": vault_id,
            "limit": limit
        })

        suggestions = []
        for row in result:
            suggestions.append({
                "note1_id": row["note1_id"],
                "note1_title": row.get("note1_title", row["note1_id"]),
                "note2_id": row["note2_id"],
                "note2_title": row.get("note2_title", row["note2_id"]),
                "shared_topics": row["shared_topics"],
                "topic_count": row["topic_count"],
                "reason": f"Share {row['topic_count']} topics: {', '.join(row['shared_topics'][:3])}"
            })

        return suggestions

    except Exception as e:
        logger.error(f"Failed to find missing connections: {e}")
        return []


def get_recommendations(
    user_id: str,
    vault_id: str,
    note_id: str = None
) -> Dict[str, Any]:
    """
    종합 추천 생성

    Args:
        user_id: 사용자 ID
        vault_id: Vault ID
        note_id: (선택) 특정 노트에 대한 추천

    Returns:
        모든 추천 결과
    """
    recommendations = {}

    # 1. 특정 노트에 대한 연결 추천
    if note_id:
        recommendations["suggested_connections"] = recommend_connections_for_note(
            note_id=note_id,
            limit=5
        )

    # 2. 우선순위 Task
    recommendations["priority_tasks"] = prioritize_tasks(
        user_id=user_id,
        vault_id=vault_id,
        limit=10
    )

    # 3. 놓친 연결
    recommendations["missing_connections"] = find_missing_connections(
        user_id=user_id,
        vault_id=vault_id,
        limit=10
    )

    return recommendations
