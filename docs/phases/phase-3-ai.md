# Phase 3: AI 온톨로지 추출 (LangChain)

> LLMGraphTransformer를 이용한 자동 그래프 변환 (Text2Graph)

**예상 시간**: 2~3시간  
**난이도**: ⭐⭐⭐☆☆ (코드 양은 줄고, 개념은 깊어짐)

---

## 목표

- **LangChain `LLMGraphTransformer`** 도입 (수동 프롬프트 제거)
- 노트 내용을 자동으로 Node/Relationship으로 변환
- Neo4j 저장 로직 간소화

---

## Step 3-1: 그래프 변환 서비스 작성

`app/services/ontology_service.py`를 LangChain 기반으로 완전히 새로 작성합니다.

```python
"""
LangChain 기반 Text2Graph 서비스
"""
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from app.db.neo4j import get_graph
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# LLM 초기화 (GPT-5 mini or GPT-4o-mini)
llm = ChatOpenAI(
    model="gpt-4o-mini",  # 비용 효율적
    temperature=0,        # 추출은 결정적이어야 함
    api_key=settings.openai_api_key
)

# 그래프 변환기 설정
# 추출할 노드/엣지 타입을 제한하여 그래프 품질 유지
llm_transformer = LLMGraphTransformer(
    llm=llm,
    allowed_nodes=["Topic", "Project", "Task", "Person", "Note"],
    allowed_relationships=["MENTIONS", "RELATED_TO", "PART_OF", "ASSIGNED_TO", "HAS_TASK"],
    strict_mode=False  # 유연한 추출 허용
)

def process_note_to_graph(note_id: str, content: str, metadata: dict):
    """
    노트 텍스트를 그래프로 변환하여 저장
    """
    try:
        graph = get_graph()
        
        # 1. 문서 객체 생성
        # LangChain Document 형식으로 변환
        doc = Document(
            page_content=content,
            metadata={
                "id": note_id,
                **metadata  # tags, path 등 포함
            }
        )
        
        # 2. Text -> GraphDocument 변환 (LLM 호출)
        # LLM이 텍스트를 분석해 Node와 Relationship 객체 리스트를 반환함
        logger.info(f"Extracting graph from note: {note_id}")
        graph_documents = llm_transformer.convert_to_graph_documents([doc])
        
        # 3. 노트 노드와의 연결 추가 (후처리)
        # 추출된 모든 엔티티가 '현재 노트'와 연결되도록 명시적 관계 추가
        for graph_doc in graph_documents:
            # 원본 노트 노드 생성
            source_node = graph_doc.nodes[0] # Note node logic needs implementation based on schema
            # 이 부분은 LangChain이 자동 생성한 노드와 별개로
            # "Note" 노드와 추출된 "Topic" 등을 연결해주는 로직이 필요할 수 있음
            # LangChain의 add_graph_documents는 기본적으로 텍스트 내의 관계만 저장함.
            pass

        # 4. Neo4j 저장
        # add_graph_documents가 MERGE 로직을 내부적으로 처리함
        graph.add_graph_documents(
            graph_documents, 
            baseEntityLabel=True, # 모든 노드에 __Entity__ 라벨 추가 (검색 용이)
            include_source=True   # 소스 텍스트 정보 포함 여부
        )
        
        # 5. Note 메타데이터 노드와 연결 (커스텀 Cypher)
        # LLMGraphTransformer는 텍스트 내부 내용만 추출하므로,
        # Note 자체(파일)와 추출된 Concept 간의 연결은 별도로 맺어줘야 함.
        link_extracted_entities_to_note(graph, note_id, graph_documents)
        
        logger.info(f"✅ Successfully saved graph for {note_id}")
        return len(graph_documents[0].nodes) if graph_documents else 0

    except Exception as e:
        logger.error(f"Error converting note to graph: {e}")
        raise e

def link_extracted_entities_to_note(graph, note_id, graph_documents):
    """
    추출된 엔티티들을 Note 노드와 연결 (MENTIONS 관계)
    """
    if not graph_documents:
        return

    # 추출된 노드들의 ID 수집
    extracted_nodes = graph_documents[0].nodes
    
    # Note 노드가 이미 존재한다고 가정 (Phase 2에서 생성됨)
    # Note -> Topic/Project/etc 연결
    for node in extracted_nodes:
        # Note 자체는 제외
        if node.type == "Note": 
            continue
            
        cypher = f"""
        MATCH (n:Note {{note_id: $note_id}})
        MERGE (e:{node.type} {{id: $entity_id}})
        MERGE (n)-[:MENTIONS]->(e)
        """
        graph.query(cypher, params={"note_id": note_id, "entity_id": node.id})
```

---

## Step 3-2: 동기화 API 수정

`app/api/routes_notes.py`에서 수동 호출 부분을 위 서비스로 교체합니다.

```python
from app.services.ontology_service import process_note_to_graph

@router.post("/sync")
async def sync_note(payload: NoteSyncRequest):
    # ... (기본 노트 저장 로직 - Phase 2) ...
    
    # AI 그래프 추출 실행
    # (비동기 처리 또는 백그라운드 태스크로 돌리는 것 추천)
    node_count = process_note_to_graph(
        note_id=payload.note.note_id,
        content=payload.note.content,
        metadata={"tags": payload.note.tags}
    )
    
    return {
        "status": "success", 
        "extracted_nodes": node_count
    }
```

---

## 💡 LangGraph 활용 (Advanced)

만약 **복잡한 흐름**이 필요하다면 `LangGraph`를 도입할 수 있습니다. 예를 들어:
1. 추출 시도
2. 결과 검증 (형식 확인)
3. 실패 시 재시도 (Self-Correction)
4. 성공 시 저장

```python
# (참고용) LangGraph 구조 예시
from langgraph.graph import StateGraph, END

class GraphState(TypedDict):
    content: str
    graph_docs: List[GraphDocument]

def extract_node(state):
    # LLMGraphTransformer 호출
    return {"graph_docs": docs}

def save_node(state):
    # Neo4j 저장
    return state

workflow = StateGraph(GraphState)
workflow.add_node("extract", extract_node)
workflow.add_node("save", save_node)
workflow.set_entry_point("extract")
workflow.add_edge("extract", "save")
workflow.add_edge("save", END)

app = workflow.compile()
```
*MVP 단계에서는 `process_note_to_graph` 함수 하나로도 충분하므로 필수는 아닙니다.*

---

## ✅ 완료 체크리스트

- [ ] `LLMGraphTransformer` 서비스 구현
- [ ] `allowed_nodes` 및 `allowed_relationships` 정의 (스키마 통제)
- [ ] Note와 추출 엔티티 연결 로직 (`link_extracted_entities_to_note`) 구현
- [ ] Sync API 연동

---

**다음**: [Phase 4-1: Context API (Text2Cypher)](./phase-4-context-backend.md)
