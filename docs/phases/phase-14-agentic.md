# Phase 14: ToolsRetriever 통합 (MVP 핵심)

**완료일**: 2025-12-02
**목표**: "내 2nd brain에게 묻기" 완성

---

## 핵심 가치

| 상태 | 동작 |
|------|------|
| **이전** | 사용자가 수동으로 검색 방법 선택 |
| **현재** | "최근 AI 관련 프로젝트 알려줘" → LLM이 자동으로 적절한 검색 조합 ✅ |

---

## ToolsRetriever 구현

**파일**: `graphrag_retriever.py`

### 사용 가능한 도구

| 도구 | 설명 | 내부 Retriever |
|------|------|---------------|
| `semantic_search` | 의미적으로 유사한 노트 검색 | VectorRetriever |
| `structured_query` | 시간, 프로젝트, 태그 등 조건 기반 검색 | Text2CypherRetriever |
| `hybrid_search` | 벡터 + 그래프 컨텍스트 탐색 | VectorCypherRetriever |

### 구현 코드

```python
from neo4j_graphrag.retrievers import ToolsRetriever

tools = [
    Tool(
        name="semantic_search",
        description="Search for semantically similar notes",
        retriever=vector_retriever
    ),
    Tool(
        name="structured_query",
        description="Query based on time, project, tags, etc.",
        retriever=text2cypher_retriever
    ),
    Tool(
        name="hybrid_search",
        description="Vector search with graph context expansion",
        retriever=vector_cypher_retriever
    )
]

tools_retriever = ToolsRetriever(
    llm=llm,
    tools=tools
)
```

---

## Agentic Search API

**파일**: `routes_search.py`

### 엔드포인트

```
GET /search/agentic?query=자연어질문&vault_id=optional
```

### 응답 형식

```json
{
  "status": "success",
  "mode": "agentic",
  "query": "Machine Learning 관련 노트",
  "selected_retriever": "semantic_search",
  "reasoning": "This is a semantic similarity query...",
  "fallback": false,
  "count": 5,
  "results": [...]
}
```

---

## 사용 예시

### 시맨틱 검색 선택

**질의**: "Machine Learning 관련 노트"

```
→ LLM 분석: 시맨틱 유사도 질의
→ 선택: semantic_search (VectorRetriever)
→ 이유: "Looking for notes similar to the concept of Machine Learning"
```

### 구조화 검색 선택

**질의**: "우선순위 높은 태스크 목록"

```
→ LLM 분석: 구조화된 필터 질의
→ 선택: structured_query (Text2CypherRetriever)
→ 이유: "Need to filter tasks by priority property"
```

### 하이브리드 검색 선택

**질의**: "Transformer 관련 노트와 그 주제들"

```
→ LLM 분석: 시맨틱 + 그래프 컨텍스트 필요
→ 선택: hybrid_search (VectorCypherRetriever)
→ 이유: "Need both semantic match and graph traversal for topics"
```

---

## Fallback 메커니즘

### ToolsRetriever 미설치 시

```python
if not TOOLS_RETRIEVER_AVAILABLE:
    # hybrid 검색으로 자동 fallback
    return await self.search_hybrid(query, top_k, vault_id)
```

### 에러 발생 시

```python
try:
    result = await tools_retriever.search(query)
except Exception as e:
    logger.warning(f"Agentic search failed, falling back: {e}")
    return await self.search_hybrid(query, top_k, vault_id)
```

---

## 통합 검색 API 확장

### mode 파라미터

```python
class SearchRequest(BaseModel):
    query: str
    mode: Literal["vector", "hybrid", "text2cypher", "agentic"] = "hybrid"
    top_k: int = 10
    vault_id: Optional[str] = None
```

### 상태 확인 API

```
GET /search/status
```

```json
{
  "status": "available",
  "available_modes": ["vector", "hybrid", "text2cypher", "agentic"],
  "tools_retriever_available": true
}
```

---

## 체크리스트

- [x] ToolsRetriever 구현
- [x] semantic_search 도구
- [x] structured_query 도구
- [x] hybrid_search 도구
- [x] Agentic Search API (`/search/agentic`)
- [x] Fallback 메커니즘
- [x] 통합 검색 API 확장 (mode: "agentic")
- [x] 상태 확인 API에 agentic 지원 여부 추가
