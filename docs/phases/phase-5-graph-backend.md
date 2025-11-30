# Phase 5-1: Graph API 구현 (Backend)

> 지식 그래프 시각화를 위한 백엔드 API 개발

**예상 시간**: 2~3시간  
**난이도**: ⭐⭐⭐⭐☆

---

## 목표

- Graph 서비스 로직 구현 (노드/엣지 데이터 생성)
- `/notes/graph/{note_id}` 엔드포인트 구현
- vis-network 포맷 호환성 확보
- API 테스트

---

## Step 5-1: Graph 서비스 작성

파일 생성: `didymos-backend/app/services/graph_service.py`

```python
"""
Graph 생성 서비스
"""
from neo4j import Driver
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


def get_note_graph(driver: Driver, note_id: str, hops: int = 1) -> Dict[str, Any]:
    """
    노트 중심 그래프 데이터 반환 (vis-network 형식)
    """
    nodes = []
    edges = []
    
    # 1. 중심 노트 추가
    center_node = get_center_note_node(driver, note_id)
    if center_node:
        nodes.append(center_node)
    
    # 2. 연결된 엔티티 및 관계 추가
    if hops >= 1:
        topics, topic_edges = get_connected_topics(driver, note_id)
        nodes.extend(topics)
        edges.extend(topic_edges)
        
        projects, project_edges = get_connected_projects(driver, note_id)
        nodes.extend(projects)
        edges.extend(project_edges)
        
        tasks, task_edges = get_connected_tasks(driver, note_id)
        nodes.extend(tasks)
        edges.extend(task_edges)
    
    # 3. 2 hop (옵션)
    if hops >= 2:
        related_notes, related_edges = get_related_notes(driver, note_id)
        nodes.extend(related_notes)
        edges.extend(related_edges)
    
    return {
        "nodes": nodes,
        "edges": edges
    }


def get_center_note_node(driver: Driver, note_id: str) -> Dict:
    """
    중심 노트 노드
    """
    try:
        with driver.session() as session:
            result = session.run(
                """
                MATCH (n:Note {note_id: $note_id})
                RETURN n.note_id AS id, n.title AS label
                """,
                note_id=note_id
            )
            
            record = result.single()
            if record:
                return {
                    "id": record["id"],
                    "label": record["label"],
                    "shape": "box",
                    "color": {
                        "background": "#6366F1",
                        "border": "#4F46E5"
                    },
                    "font": {"color": "#FFFFFF"},
                    "size": 30,
                    "group": "note"
                }
            return None
            
    except Exception as e:
        logger.error(f"Error getting center node: {e}")
        return None


def get_connected_topics(driver: Driver, note_id: str) -> tuple:
    """
    연결된 Topics
    """
    nodes = []
    edges = []
    
    try:
        with driver.session() as session:
            result = session.run(
                """
                MATCH (n:Note {note_id: $note_id})-[r:MENTIONS]->(t:Topic)
                RETURN t.name AS id, t.name AS label, r.confidence AS weight
                """,
                note_id=note_id
            )
            
            for record in result:
                nodes.append({
                    "id": f"topic_{record['id']}",
                    "label": record["label"],
                    "shape": "dot",
                    "color": {
                        "background": "#10B981",
                        "border": "#059669"
                    },
                    "size": 20,
                    "group": "topic"
                })
                
                edges.append({
                    "from": note_id,
                    "to": f"topic_{record['id']}",
                    "label": "mentions",
                    "arrows": "to",
                    "color": "#9CA3AF"
                })
        
        return nodes, edges
        
    except Exception as e:
        logger.error(f"Error getting topics: {e}")
        return [], []


def get_connected_projects(driver: Driver, note_id: str) -> tuple:
    """
    연결된 Projects
    """
    nodes = []
    edges = []
    
    try:
        with driver.session() as session:
            result = session.run(
                """
                MATCH (n:Note {note_id: $note_id})-[:RELATES_TO_PROJECT]->(p:Project)
                RETURN p.name AS id, p.name AS label, p.status AS status
                """,
                note_id=note_id
            )
            
            for record in result:
                # 상태에 따른 색상
                color = {
                    "active": {"background": "#F59E0B", "border": "#D97706"},
                    "paused": {"background": "#6B7280", "border": "#4B5563"},
                    "done": {"background": "#10B981", "border": "#059669"}
                }.get(record["status"], {"background": "#F59E0B", "border": "#D97706"})
                
                nodes.append({
                    "id": f"project_{record['id']}",
                    "label": record["label"],
                    "shape": "box",
                    "color": color,
                    "size": 20,
                    "group": "project"
                })
                
                edges.append({
                    "from": note_id,
                    "to": f"project_{record['id']}",
                    "label": "project",
                    "arrows": "to",
                    "color": "#9CA3AF",
                    "dashes": True
                })
        
        return nodes, edges
        
    except Exception as e:
        logger.error(f"Error getting projects: {e}")
        return [], []


def get_connected_tasks(driver: Driver, note_id: str) -> tuple:
    """
    연결된 Tasks
    """
    nodes = []
    edges = []
    
    try:
        with driver.session() as session:
            result = session.run(
                """
                MATCH (n:Note {note_id: $note_id})-[:CONTAINS_TASK]->(t:Task)
                RETURN t.id AS id, t.title AS label, t.priority AS priority
                LIMIT 5
                """,
                note_id=note_id
            )
            
            for record in result:
                # 우선순위에 따른 색상
                color = {
                    "high": {"background": "#EF4444", "border": "#DC2626"},
                    "medium": {"background": "#F59E0B", "border": "#D97706"},
                    "low": {"background": "#6B7280", "border": "#4B5563"}
                }.get(record["priority"], {"background": "#F59E0B", "border": "#D97706"})
                
                nodes.append({
                    "id": f"task_{record['id']}",
                    "label": record["label"][:30] + "...",  # 길이 제한
                    "shape": "diamond",
                    "color": color,
                    "size": 15,
                    "group": "task"
                })
                
                edges.append({
                    "from": note_id,
                    "to": f"task_{record['id']}",
                    "label": "task",
                    "arrows": "to",
                    "color": "#9CA3AF"
                })
        
        return nodes, edges
        
    except Exception as e:
        logger.error(f"Error getting tasks: {e}")
        return [], []


def get_related_notes(driver: Driver, note_id: str) -> tuple:
    """
    2 hop: 관련 노트
    """
    nodes = []
    edges = []
    
    try:
        with driver.session() as session:
            result = session.run(
                """
                MATCH (n:Note {note_id: $note_id})-[:MENTIONS]->(t:Topic)
                <-[:MENTIONS]-(related:Note)
                WHERE n <> related
                WITH related, COUNT(t) AS common
                ORDER BY common DESC
                LIMIT 3
                RETURN related.note_id AS id, related.title AS label
                """,
                note_id=note_id
            )
            
            for record in result:
                nodes.append({
                    "id": record["id"],
                    "label": record["label"],
                    "shape": "box",
                    "color": {
                        "background": "#818CF8",
                        "border": "#6366F1"
                    },
                    "size": 20,
                    "group": "note"
                })
                
                edges.append({
                    "from": note_id,
                    "to": record["id"],
                    "label": "related",
                    "arrows": "to",
                    "color": "#9CA3AF",
                    "dashes": True
                })
        
        return nodes, edges
        
    except Exception as e:
        logger.error(f"Error getting related notes: {e}")
        return [], []
```

---

## Step 5-2: Graph API 라우터

파일 수정: `didymos-backend/app/api/routes_notes.py`

import 추가:

```python
from app.services.graph_service import get_note_graph
```

엔드포인트 추가:

```python
@router.get("/graph/{note_id}")
async def get_graph(note_id: str, user_token: str, hops: int = 1):
    """
    노트 그래프 조회
    """
    try:
        driver = get_neo4j_driver()
        user_id = get_user_id_from_token(user_token)
        
        logger.info(f"Getting graph for: {note_id}, hops: {hops}")
        
        graph = get_note_graph(driver, note_id, hops)
        
        return graph
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
```

---

## Step 5-3: API 테스트

서버 재시작 후 Swagger UI에서 테스트:

1. `/api/v1/notes/graph/{note_id}` 펼치기
2. `note_id`: 노트 ID
3. `user_token`: `test_user_001`
4. `hops`: `1` 또는 `2`
5. "Execute" 클릭

---

## ✅ 백엔드 완료 체크리스트

- [ ] `app/services/graph_service.py` 작성
- [ ] `/notes/graph/{note_id}` API 구현
- [ ] Swagger UI에서 테스트 성공

---

**다음 단계**: [Phase 5-2: Graph Panel UI (Frontend)](./phase-5-graph-frontend.md)

