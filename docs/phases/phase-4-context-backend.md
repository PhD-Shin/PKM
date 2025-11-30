# Phase 4-1: Context API 구현 (Backend)

> 벡터(Vector) + 그래프(Graph) 하이브리드 검색 구현

**예상 시간**: 2~3시간  
**난이도**: ⭐⭐⭐⭐☆

---

## 목표

- **LangChain `Neo4jVector`** 도입 (벡터 검색)
- 노트 본문 임베딩 및 인덱스 생성
- 의미 기반(Semantic) 유사 노트 추천 구현
- Context API 엔드포인트 구현

---

## Step 4-1: Context 스키마 정의

파일 생성: `didymos-backend/app/schemas/context.py`

```python
"""
Context 관련 Pydantic 스키마
"""
from typing import List
from pydantic import BaseModel


class TopicOut(BaseModel):
    id: str
    name: str
    importance_score: float = 0.0
    mention_count: int = 0


class ProjectOut(BaseModel):
    id: str
    name: str
    status: str
    updated_at: str


class TaskOut(BaseModel):
    id: str
    title: str
    status: str
    priority: str


class RelatedNoteOut(BaseModel):
    note_id: str
    title: str
    path: str
    similarity: float  # 0.0-1.0
    reason: str = "semantic" # semantic(의미) or structural(구조)


class NoteContextResponse(BaseModel):
    topics: List[TopicOut]
    projects: List[ProjectOut]
    tasks: List[TaskOut]
    related_notes: List[RelatedNoteOut]
```

---

## Step 4-2: 벡터 서비스 (Vector Service) 작성

`Neo4jVector`를 사용하여 노트 본문을 벡터화하고 저장/검색하는 서비스를 만듭니다.

파일 생성: `didymos-backend/app/services/vector_service.py`

```python
"""
LangChain Neo4jVector 서비스
"""
from langchain_neo4j import Neo4jVector
from langchain_openai import OpenAIEmbeddings
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# 임베딩 모델 (비용 효율적인 text-embedding-3-small 추천)
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=settings.openai_api_key
)

def get_vector_store():
    """
    Neo4jVector 스토어 객체 반환
    """
    return Neo4jVector.from_existing_graph(
        embedding=embeddings,
        url=settings.neo4j_uri,
        username=settings.neo4j_user,
        password=settings.neo4j_password,
        index_name="note_vector_index",
        node_label="Note",
        text_node_properties=["content", "title"], # 벡터화할 속성
        embedding_node_property="embedding",       # 임베딩 저장 속성
    )

def index_note_content(note_id: str, content: str):
    """
    (Phase 3에서 호출) 노트 내용을 벡터화하여 저장
    주의: Neo4jVector.from_documents 등을 써도 되지만, 
    기존 노드에 업데이트하는 방식이므로 Cypher나 from_existing_graph 활용이 유리
    """
    # LangChain Neo4jVector는 주로 '검색' 용도.
    # 데이터 삽입은 LLMGraphTransformer가 만든 노드에 
    # 임베딩만 추가하는 방식이 깔끔함.
    # 여기서는 간단히 검색을 위해 인덱스가 존재함을 보장.
    pass 

def find_semantically_similar_notes(query: str, limit: int = 5) -> List[dict]:
    """
    벡터 유사도 검색 (의미 기반 추천)
    """
    try:
        vector_store = get_vector_store()
        
        # 유사도 검색 실행
        results = vector_store.similarity_search_with_score(query, k=limit)
        
        notes = []
        for doc, score in results:
            metadata = doc.metadata
            notes.append({
                "note_id": metadata.get("note_id") or metadata.get("id"), # 메타데이터 키 확인 필요
                "title": metadata.get("title", "Untitled"),
                "path": metadata.get("path", ""),
                "similarity": score,
                "reason": "semantic"
            })
            
        return notes
        
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        return []
```

---

## Step 4-3: Context 서비스 (Hybrid) 작성

기존 그래프 검색과 벡터 검색을 결합합니다.

파일 생성: `didymos-backend/app/services/context_service.py`

```python
"""
Context 생성 서비스 (Hybrid)
"""
from neo4j import Driver
from typing import List, Dict, Any
from app.services.vector_service import find_semantically_similar_notes
import logging

logger = logging.getLogger(__name__)

def get_note_context(driver: Driver, note_id: str, content_preview: str = "") -> Dict[str, Any]:
    """
    노트의 전체 컨텍스트 반환
    """
    # 1. 구조적 데이터 (Graph)
    topics = get_topics_for_note(driver, note_id)
    projects = get_projects_for_note(driver, note_id)
    tasks = get_tasks_in_note(driver, note_id)
    
    # 2. 추천 (Hybrid: Graph + Vector)
    # Graph: 공통 토픽 기반
    graph_related = find_structurally_related_notes(driver, note_id)
    
    # Vector: 내용 의미 기반 (노트 내용 일부를 쿼리로 사용)
    # 현재 노트가 없다면 제목이라도 쿼리로 사용
    query = content_preview if content_preview else note_id 
    vector_related = find_semantically_similar_notes(query, limit=3)
    
    # 중복 제거 및 병합
    related_notes = merge_related_notes(graph_related, vector_related, current_note_id=note_id)
    
    return {
        "topics": topics,
        "projects": projects,
        "tasks": tasks,
        "related_notes": related_notes
    }

def merge_related_notes(graph_list, vector_list, current_note_id):
    """
    두 리스트 병합 (중복 제거)
    """
    seen = {current_note_id}
    merged = []
    
    # Graph 우선
    for note in graph_list:
        if note["note_id"] not in seen:
            merged.append(note)
            seen.add(note["note_id"])
            
    # Vector 추가
    for note in vector_list:
        if note["note_id"] not in seen:
            merged.append(note)
            seen.add(note["note_id"])
            
    return merged[:5] # 최대 5개

# ... (get_topics_for_note, get_projects_for_note 등 기존 함수들 유지) ...

def find_structurally_related_notes(driver: Driver, note_id: str, limit: int = 3) -> List[Dict]:
    """
    공통 Topic 기반 유사 노트 찾기 (Graph)
    """
    try:
        with driver.session() as session:
            result = session.run(
                """
                MATCH (n:Note {note_id: $note_id})-[:MENTIONS]->(t:Topic)
                <-[:MENTIONS]-(related:Note)
                WHERE n <> related
                WITH related, COUNT(DISTINCT t) AS common_topics
                ORDER BY common_topics DESC
                LIMIT $limit
                RETURN 
                    related.note_id AS note_id,
                    related.title AS title,
                    related.path AS path,
                    common_topics
                """,
                note_id=note_id,
                limit=limit
            )
            
            notes = []
            for record in result:
                similarity = min(record["common_topics"] / 5.0, 1.0)
                notes.append({
                    "note_id": record["note_id"],
                    "title": record["title"],
                    "path": record["path"],
                    "similarity": round(similarity, 2),
                    "reason": "structural"
                })
            return notes
    except Exception as e:
        logger.error(f"Graph search error: {e}")
        return []
```

---

## Step 4-4: API 라우터 수정

API에서 노트 본문(content)을 받아올 수 없으므로(Context 조회 시점), 저장된 데이터를 쓰거나 쿼리로 받아야 합니다. 여기서는 간편하게 **노트 제목을 쿼리로 사용**하거나, DB에서 본문을 조회합니다.

파일 수정: `didymos-backend/app/api/routes_notes.py`

```python
@router.get("/context/{note_id}", response_model=NoteContextResponse)
async def get_context(note_id: str, user_token: str):
    try:
        driver = get_neo4j_driver()
        
        # 노트 본문이나 제목을 가져오기 위한 간단한 조회
        # (실제로는 노트 저장 시점에 임베딩이 되어 있어야 함)
        # 여기서는 note_id(보통 파일명/제목 포함)를 쿼리로 사용
        context = get_note_context(driver, note_id, content_preview=note_id)
        
        return NoteContextResponse(**context)
    # ...
```

---

## ✅ 완료 체크리스트

- [ ] `requirements.txt`에 `langchain-openai` 확인
- [ ] `app/services/vector_service.py` 작성
- [ ] `app/services/context_service.py`에 하이브리드 로직 구현
- [ ] Swagger UI 테스트

---

**다음 단계**: [Phase 4-2: Context Panel UI (Frontend)](./phase-4-context-frontend.md)
