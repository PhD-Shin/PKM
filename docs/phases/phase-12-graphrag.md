# Phase 12: GraphRAG 검색 강화 (neo4j-graphrag 도입)

**완료일**: 2025-12-02
**목표**: 하이브리드 검색 고도화

---

## 아키텍처 결정

**Graphiti + neo4j-graphrag 병용**:

| 레이어 | 라이브러리 | 역할 |
|--------|-----------|------|
| **Storage** | Graphiti (Zep AI) | Episode 처리, Entity 해결, Bi-temporal |
| **Query** | neo4j-graphrag | Retriever 전략 |

---

## neo4j-graphrag Retriever 전략

| Retriever | 용도 | Didymos 적용 |
|-----------|------|--------------|
| **VectorRetriever** | 유사도 기반 노트 검색 | Context Panel 유사 노트 |
| **VectorCypherRetriever** | 벡터 + 그래프 순회 | 클러스터 내 탐색 |
| **Text2CypherRetriever** | 자연어 → Cypher | "최근 프로젝트 목록", "관련 태스크" |
| **HybridRetriever** | 벡터 + 키워드(BM25) | 전체 Vault 검색 |

---

## 구현 상세

### VectorRetriever 구현

**파일**: `graphrag_retriever.py`

노트 임베딩 기반 시맨틱 유사도 검색

```python
from neo4j_graphrag.retrievers import VectorRetriever

retriever = VectorRetriever(
    driver=driver,
    index_name="note_embeddings",  # Neo4j 벡터 인덱스
    embedder=embedder,
    return_properties=["note_id", "title", "path", "content", "updated_at"]
)
```

**API**: `GET /search/vector`

### Text2CypherRetriever 구현

자연어 → Cypher 자동 변환

```python
from neo4j_graphrag.retrievers import Text2CypherRetriever

retriever = Text2CypherRetriever(
    driver=driver,
    llm=llm,
    neo4j_schema=schema  # 그래프 스키마 설명
)
```

**API**: `GET /search/text2cypher`

**예시**:
- "Machine Learning 관련 노트 찾아줘"
- "Didymos 프로젝트의 할일 목록"
- "최근 일주일간 수정된 노트"
- "Transformer 주제의 상위 개념은?"

### VectorCypherRetriever 구현

벡터 검색 + SKOS 계층 관계 확장

```python
from neo4j_graphrag.retrievers import VectorCypherRetriever

retriever = VectorCypherRetriever(
    driver=driver,
    index_name="note_embeddings",
    embedder=embedder,
    retrieval_query="""
        MATCH (n)-[:MENTIONS]->(e:Entity)
        OPTIONAL MATCH (e)-[:BROADER]->(parent)
        OPTIONAL MATCH (e)-[:NARROWER]->(child)
        RETURN n, e, parent, child
    """
)
```

**API**: `GET /search/hybrid`

---

## API 엔드포인트

### 통합 검색 API

**파일**: `routes_search.py`

```
POST /search
{
  "query": "검색어",
  "mode": "vector|hybrid|text2cypher|agentic",
  "top_k": 10,
  "vault_id": "optional"
}
```

### 개별 검색 API

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/search/vector` | GET | 벡터 유사도 검색 |
| `/search/hybrid` | GET | 벡터 + 그래프 컨텍스트 |
| `/search/text2cypher` | GET | 자연어 → Cypher |
| `/search/agentic` | GET | LLM이 최적 retriever 선택 |
| `/search/status` | GET | 서비스 상태 확인 |

---

## 체크리스트

- [x] VectorRetriever 구현
- [x] Text2CypherRetriever 구현
- [x] VectorCypherRetriever 구현
- [x] 통합 검색 API (`routes_search.py`)
- [x] 서비스 상태 확인 API
