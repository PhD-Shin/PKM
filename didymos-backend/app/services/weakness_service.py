"""
약점 분석 서비스
"The chain is only as strong as its weakest link" 원칙에 기반한 약점 탐지

- 고립된 Topic 발견
- 방치된 Project 탐지
- 만성적으로 미루는 Task 분석
- 연결이 희박한 지식 영역 발견
- 지식 공백 탐지
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def find_isolated_topics(
    user_id: str,
    vault_id: str,
    min_notes_threshold: int = 3
) -> List[Dict[str, Any]]:
    """
    고립된 Topic 찾기
    - Topic은 여러 노트에서 언급되지만, 그 노트들끼리 연결이 전혀 없는 경우
    - 개념은 있지만 통합되지 않은 지식 영역

    Args:
        user_id: 사용자 ID
        vault_id: Vault ID
        min_notes_threshold: 최소 노트 수 (이상이어야 고립으로 판단)

    Returns:
        고립된 Topic 리스트
    """
    from app.db.neo4j import get_neo4j_client

    client = get_neo4j_client()

    cypher = """
    MATCH (u:User {id: $user_id})-[:OWNS]->(v:Vault {id: $vault_id})
    MATCH (v)-[:HAS_NOTE]->(n:Note)-[:MENTIONS]->(topic:Topic)
    WITH topic, collect(DISTINCT n) AS notes
    WHERE size(notes) >= $min_notes_threshold

    // 이 Topic을 언급한 노트들끼리 연결이 있는지 확인
    UNWIND notes AS n1
    UNWIND notes AS n2
    WITH topic, notes, n1, n2
    WHERE n1.note_id < n2.note_id
    OPTIONAL MATCH (n1)-[rel:MENTIONS|:RELATES_TO]-(n2)

    WITH topic, notes, count(rel) AS connections
    WHERE connections = 0

    RETURN topic.name AS topic_name,
           [n IN notes | n.note_id] AS note_ids,
           [n IN notes | n.title] AS note_titles,
           size(notes) AS note_count
    ORDER BY note_count DESC
    LIMIT 10
    """

    try:
        result = client.query(cypher, {
            "user_id": user_id,
            "vault_id": vault_id,
            "min_notes_threshold": min_notes_threshold
        })

        isolated = []
        for row in result:
            isolated.append({
                "topic_name": row["topic_name"],
                "note_count": row["note_count"],
                "note_ids": row["note_ids"],
                "note_titles": row.get("note_titles", row["note_ids"]),
                "severity": "high" if row["note_count"] >= 5 else "medium",
                "recommendation": f"Connect {row['note_count']} notes about '{row['topic_name']}' to integrate this knowledge area"
            })

        return isolated

    except Exception as e:
        logger.error(f"Failed to find isolated topics: {e}")
        return []


def find_stale_projects(
    user_id: str,
    vault_id: str,
    days_threshold: int = 30
) -> List[Dict[str, Any]]:
    """
    방치된 Project 찾기
    - 일정 기간 이상 업데이트가 없는 프로젝트
    - status가 'active'이지만 실제로는 진행되지 않는 프로젝트

    Args:
        user_id: 사용자 ID
        vault_id: Vault ID
        days_threshold: 방치 판단 기준 일수

    Returns:
        방치된 프로젝트 리스트
    """
    from app.db.neo4j import get_neo4j_client

    client = get_neo4j_client()

    # Threshold 날짜 계산
    threshold_date = datetime.now() - timedelta(days=days_threshold)
    threshold_iso = threshold_date.isoformat()

    cypher = """
    MATCH (u:User {id: $user_id})-[:OWNS]->(v:Vault {id: $vault_id})
    MATCH (v)-[:HAS_NOTE]->(n:Note)
    WHERE n.path STARTS WITH 'Projects/' OR n.folder = 'Projects'

    // 마지막 수정 시간 확인
    WITH n
    WHERE n.updated_at < $threshold_date OR n.updated_at IS NULL

    // 관련 Task 확인
    OPTIONAL MATCH (n)-[:HAS_TASK]->(t:Task)
    WHERE t.status IN ['todo', 'in_progress']

    WITH n, collect(t) AS tasks

    RETURN n.note_id AS note_id,
           n.title AS title,
           n.path AS path,
           n.updated_at AS last_updated,
           size(tasks) AS pending_task_count,
           [task IN tasks | {title: task.title, status: task.status, due_date: task.due_date}] AS pending_tasks
    ORDER BY n.updated_at ASC NULLS FIRST
    LIMIT 20
    """

    try:
        result = client.query(cypher, {
            "user_id": user_id,
            "vault_id": vault_id,
            "threshold_date": threshold_iso
        })

        stale = []
        today = datetime.now()

        for row in result:
            days_since_update = None
            if row.get("last_updated"):
                try:
                    last_update = datetime.fromisoformat(row["last_updated"])
                    days_since_update = (today - last_update).days
                except:
                    pass

            severity = "critical" if days_since_update and days_since_update > 90 else \
                      "high" if days_since_update and days_since_update > 60 else "medium"

            stale.append({
                "note_id": row["note_id"],
                "title": row.get("title", row["note_id"]),
                "path": row.get("path", row["note_id"]),
                "days_since_update": days_since_update,
                "pending_task_count": row.get("pending_task_count", 0),
                "pending_tasks": row.get("pending_tasks", []),
                "severity": severity,
                "recommendation": f"Review and update this project. {row.get('pending_task_count', 0)} tasks are waiting."
            })

        return stale

    except Exception as e:
        logger.error(f"Failed to find stale projects: {e}")
        return []


def find_chronic_overdue(
    user_id: str,
    vault_id: str,
    overdue_threshold: int = 7
) -> List[Dict[str, Any]]:
    """
    만성적으로 미루는 Task 찾기
    - 일정 기간 이상 overdue 상태인 Task
    - 반복적으로 미루는 패턴 발견

    Args:
        user_id: 사용자 ID
        vault_id: Vault ID
        overdue_threshold: Overdue 판단 기준 일수

    Returns:
        만성 overdue Task 리스트
    """
    from app.db.neo4j import get_neo4j_client

    client = get_neo4j_client()

    today = datetime.now().date().isoformat()

    cypher = """
    MATCH (u:User {id: $user_id})-[:OWNS]->(v:Vault {id: $vault_id})
    MATCH (v)-[:HAS_NOTE]->(n:Note)-[:HAS_TASK]->(t:Task)
    WHERE t.status IN ['todo', 'in_progress']
      AND t.due_date < $today

    WITH t, n, t.due_date AS due_date

    RETURN t.id AS task_id,
           t.title AS title,
           t.status AS status,
           t.priority AS priority,
           due_date,
           n.note_id AS note_id,
           n.title AS note_title
    ORDER BY due_date ASC
    LIMIT 20
    """

    try:
        result = client.query(cypher, {
            "user_id": user_id,
            "vault_id": vault_id,
            "today": today
        })

        chronic = []
        today_date = datetime.now().date()

        for row in result:
            days_overdue = 0
            if row.get("due_date"):
                try:
                    due_date = datetime.fromisoformat(row["due_date"]).date()
                    days_overdue = (today_date - due_date).days
                except:
                    pass

            if days_overdue < overdue_threshold:
                continue

            severity = "critical" if days_overdue > 30 else \
                      "high" if days_overdue > 14 else "medium"

            chronic.append({
                "task_id": row.get("task_id"),
                "title": row.get("title", "Untitled task"),
                "status": row.get("status", "todo"),
                "priority": row.get("priority", "medium"),
                "due_date": row.get("due_date"),
                "days_overdue": days_overdue,
                "note_id": row.get("note_id"),
                "note_title": row.get("note_title", row.get("note_id")),
                "severity": severity,
                "recommendation": f"This task is {days_overdue} days overdue. Consider breaking it into smaller tasks or re-evaluating priority."
            })

        return chronic

    except Exception as e:
        logger.error(f"Failed to find chronic overdue tasks: {e}")
        return []


def find_weak_clusters(
    user_id: str,
    vault_id: str,
    min_size: int = 3,
    max_density: float = 0.3
) -> List[Dict[str, Any]]:
    """
    연결이 희박한 지식 영역 찾기
    - Community는 존재하지만 내부 연결이 매우 적은 클러스터
    - 개념들이 모여있지만 통합되지 않은 영역

    Args:
        user_id: 사용자 ID
        vault_id: Vault ID
        min_size: 최소 클러스터 크기
        max_density: 최대 밀집도 (이하면 약한 것으로 판단)

    Returns:
        약한 클러스터 리스트
    """
    from app.db.neo4j import get_neo4j_client
    from app.services.pattern_service import detect_communities, analyze_vault_patterns

    try:
        # Pattern analysis로 community 먼저 탐지
        patterns = analyze_vault_patterns(user_id, vault_id)
        communities = patterns.get("communities", [])

        weak = []

        for comm in communities:
            if comm["size"] < min_size:
                continue

            # 밀집도 계산: actual_edges / possible_edges
            # possible_edges = n * (n-1) / 2
            n = comm["size"]
            possible_edges = n * (n - 1) / 2

            # 실제 edge 수 계산 (community 내부 노트들 간 연결)
            client = get_neo4j_client()

            cypher = """
            MATCH (n1:Note)-[rel:MENTIONS|:RELATES_TO]-(n2:Note)
            WHERE n1.note_id IN $note_ids
              AND n2.note_id IN $note_ids
              AND n1.note_id < n2.note_id
            RETURN count(DISTINCT rel) AS edge_count
            """

            result = client.query(cypher, {"note_ids": comm["notes"]})
            actual_edges = result[0]["edge_count"] if result else 0

            density = actual_edges / possible_edges if possible_edges > 0 else 0

            if density <= max_density:
                weak.append({
                    "cluster_id": comm["id"],
                    "size": comm["size"],
                    "note_ids": comm["notes"][:10],  # 일부만
                    "density": round(density, 3),
                    "actual_edges": actual_edges,
                    "possible_edges": int(possible_edges),
                    "severity": "high" if density < 0.1 else "medium",
                    "recommendation": f"This cluster has {comm['size']} notes but only {actual_edges} connections. Add more links to integrate this knowledge area."
                })

        # 밀집도 낮은 순으로 정렬
        weak.sort(key=lambda x: x["density"])

        return weak[:10]

    except Exception as e:
        logger.error(f"Failed to find weak clusters: {e}")
        return []


def detect_knowledge_gaps(
    user_id: str,
    vault_id: str,
    min_topic_mentions: int = 5,
    max_notes_with_content: int = 2
) -> List[Dict[str, Any]]:
    """
    지식 공백 탐지
    - Topic은 많이 언급되지만 실제 설명 노트가 부족한 경우
    - 개념을 자주 쓰지만 깊이 있는 이해가 부족한 영역

    Args:
        user_id: 사용자 ID
        vault_id: Vault ID
        min_topic_mentions: 최소 언급 횟수
        max_notes_with_content: 최대 실제 내용 노트 수

    Returns:
        지식 공백 리스트
    """
    from app.db.neo4j import get_neo4j_client

    client = get_neo4j_client()

    cypher = """
    MATCH (u:User {id: $user_id})-[:OWNS]->(v:Vault {id: $vault_id})
    MATCH (v)-[:HAS_NOTE]->(n:Note)-[:MENTIONS]->(topic:Topic)

    WITH topic, collect(DISTINCT n) AS notes
    WHERE size(notes) >= $min_mentions

    // 실제 내용이 있는 노트 필터링 (TODO: 임시로 모든 노트 카운트)
    WITH topic, notes, size(notes) AS total_mentions

    RETURN topic.name AS topic_name,
           total_mentions,
           [n IN notes | n.note_id][..5] AS sample_note_ids,
           [n IN notes | n.title][..5] AS sample_note_titles
    ORDER BY total_mentions DESC
    LIMIT 10
    """

    try:
        result = client.query(cypher, {
            "user_id": user_id,
            "vault_id": vault_id,
            "min_mentions": min_topic_mentions
        })

        gaps = []
        for row in result:
            gaps.append({
                "topic_name": row["topic_name"],
                "mention_count": row["total_mentions"],
                "sample_note_ids": row.get("sample_note_ids", []),
                "sample_note_titles": row.get("sample_note_titles", []),
                "severity": "high" if row["total_mentions"] >= 10 else "medium",
                "recommendation": f"'{row['topic_name']}' is mentioned {row['total_mentions']} times but may lack deep coverage. Consider creating a comprehensive note."
            })

        return gaps

    except Exception as e:
        logger.error(f"Failed to detect knowledge gaps: {e}")
        return []


def analyze_weaknesses(
    user_id: str,
    vault_id: str
) -> Dict[str, Any]:
    """
    종합 약점 분석
    "The chain is only as strong as its weakest link" 원칙

    Args:
        user_id: 사용자 ID
        vault_id: Vault ID

    Returns:
        모든 약점 분석 결과 + 우선순위 추천
    """
    logger.info(f"Analyzing weaknesses for user {user_id}, vault {vault_id}")

    # 모든 약점 탐지
    isolated_topics = find_isolated_topics(user_id, vault_id)
    stale_projects = find_stale_projects(user_id, vault_id, days_threshold=30)
    chronic_tasks = find_chronic_overdue(user_id, vault_id, overdue_threshold=7)
    weak_clusters = find_weak_clusters(user_id, vault_id)
    knowledge_gaps = detect_knowledge_gaps(user_id, vault_id)

    # 각 카테고리별 심각도 점수 계산
    def calculate_severity_score(items: List[Dict]) -> float:
        if not items:
            return 0.0

        severity_weights = {"critical": 10, "high": 5, "medium": 2, "low": 1}
        total = sum(severity_weights.get(item.get("severity", "low"), 0) for item in items)
        return round(total / len(items), 2)

    # 가장 심각한 약점 식별
    weaknesses_summary = {
        "isolated_topics": {
            "count": len(isolated_topics),
            "severity_score": calculate_severity_score(isolated_topics),
            "items": isolated_topics[:5]
        },
        "stale_projects": {
            "count": len(stale_projects),
            "severity_score": calculate_severity_score(stale_projects),
            "items": stale_projects[:5]
        },
        "chronic_overdue_tasks": {
            "count": len(chronic_tasks),
            "severity_score": calculate_severity_score(chronic_tasks),
            "items": chronic_tasks[:5]
        },
        "weak_clusters": {
            "count": len(weak_clusters),
            "severity_score": calculate_severity_score(weak_clusters),
            "items": weak_clusters[:5]
        },
        "knowledge_gaps": {
            "count": len(knowledge_gaps),
            "severity_score": calculate_severity_score(knowledge_gaps),
            "items": knowledge_gaps[:5]
        }
    }

    # 전체 약점 점수 계산
    total_weakness_score = sum(
        cat["severity_score"] for cat in weaknesses_summary.values()
    )

    # 가장 심각한 카테고리 찾기
    critical_category = max(
        weaknesses_summary.items(),
        key=lambda x: x[1]["severity_score"]
    )

    return {
        "weaknesses": weaknesses_summary,
        "total_weakness_score": round(total_weakness_score, 2),
        "critical_weakness": {
            "category": critical_category[0],
            "severity_score": critical_category[1]["severity_score"],
            "count": critical_category[1]["count"],
            "top_items": critical_category[1]["items"][:3]
        },
        "strengthening_plan": generate_strengthening_plan(weaknesses_summary)
    }


def generate_strengthening_plan(
    weaknesses: Dict[str, Any]
) -> List[Dict[str, str]]:
    """
    약점 보완 계획 생성

    Args:
        weaknesses: 약점 분석 결과

    Returns:
        보완 계획 리스트 (우선순위 순)
    """
    plan = []

    # 1. Chronic overdue tasks
    if weaknesses["chronic_overdue_tasks"]["count"] > 0:
        plan.append({
            "priority": 1,
            "action": "Complete or reschedule overdue tasks",
            "reason": f"{weaknesses['chronic_overdue_tasks']['count']} tasks are chronically overdue",
            "steps": [
                "Review top 3 overdue tasks",
                "Break down into smaller tasks if needed",
                "Set realistic new deadlines",
                "Complete at least 1 task this week"
            ]
        })

    # 2. Stale projects
    if weaknesses["stale_projects"]["count"] > 0:
        plan.append({
            "priority": 2,
            "action": "Revive or archive stale projects",
            "reason": f"{weaknesses['stale_projects']['count']} projects have no recent activity",
            "steps": [
                "Review each stale project",
                "Decide: continue, pause, or archive",
                "Update project status notes",
                "Create next action for active projects"
            ]
        })

    # 3. Isolated topics
    if weaknesses["isolated_topics"]["count"] > 0:
        plan.append({
            "priority": 3,
            "action": "Connect isolated knowledge areas",
            "reason": f"{weaknesses['isolated_topics']['count']} topics have unconnected notes",
            "steps": [
                "Pick top isolated topic",
                "Review all related notes",
                "Find connections between them",
                "Add links to integrate knowledge"
            ]
        })

    # 4. Weak clusters
    if weaknesses["weak_clusters"]["count"] > 0:
        plan.append({
            "priority": 4,
            "action": "Strengthen weak knowledge clusters",
            "reason": f"{weaknesses['weak_clusters']['count']} clusters are poorly connected",
            "steps": [
                "Identify the weakest cluster",
                "Create hub note for this area",
                "Link related concepts together",
                "Add summary and overview"
            ]
        })

    # 5. Knowledge gaps
    if weaknesses["knowledge_gaps"]["count"] > 0:
        plan.append({
            "priority": 5,
            "action": "Fill knowledge gaps",
            "reason": f"{weaknesses['knowledge_gaps']['count']} topics need deeper coverage",
            "steps": [
                "Pick most-mentioned topic",
                "Create comprehensive note",
                "Add examples and explanations",
                "Link to related concepts"
            ]
        })

    return plan
