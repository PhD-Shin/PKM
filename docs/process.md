# Didymos - 개발 프로세스 & 아키텍처

> Obsidian을 위한 PKM 시맨틱 온톨로지 시스템

**최종 수정**: 2025-12-08
**상태**: Phase 16 완료 - 프로덕션 준비 완료
**핵심 아키텍처**: Graphiti + PKM 8타입 온톨로지 + 시맨틱 엣지 타입

---

## 프로젝트 개요

### Didymos란?

Didymos는 Obsidian 볼트를 **실행 가능한 온톨로지**로 변환합니다 - 구조화된 지식 그래프로:

1. **엔티티**가 8 PKM Types로 분류됨 (Goal, Project, Task, Topic, Concept, Question, Insight, Resource)
2. **엣지**가 타입 조합 기반 시맨틱 의미를 가짐 (ACHIEVED_BY, REQUIRES, CONTAINS 등)
3. **시각화**가 유사도 점수가 아닌 실제 사고 구조를 보여줌

### 기술 스택

| 레이어 | 기술 | 목적 |
|--------|------|------|
| **프론트엔드** | Obsidian 플러그인 (TypeScript) | UI, 그래프 시각화 (vis-network) |
| **백엔드** | FastAPI (Python 3.11) | REST API, 비즈니스 로직 |
| **저장소** | Graphiti (Zep AI) | 시간 KG, 엔티티 추출 |
| **데이터베이스** | Neo4j AuraDB | 그래프 저장, 벡터 인덱스 |
| **AI** | GPT-5-Mini, OpenAI Embeddings | 타입 분류, 클러스터링 |
| **배포** | Railway | Docker 컨테이너화 |

---

## 코드베이스 구조

### 백엔드 (`didymos-backend/`)

```
didymos-backend/
├── app/
│   ├── main.py                     # FastAPI 앱 진입점
│   ├── config.py                   # 설정 (환경 변수)
│   │
│   ├── api/                        # REST 엔드포인트
│   │   ├── routes_notes.py         # /notes/sync
│   │   ├── routes_graph.py         # /vault/entity-clusters (메인)
│   │   ├── routes_temporal.py      # /temporal/* (stale, search)
│   │   ├── routes_search.py        # /search/* (GraphRAG)
│   │   ├── routes_context.py       # /notes/context
│   │   ├── routes_tasks.py         # /tasks/*
│   │   ├── routes_review.py        # /review/weekly
│   │   └── routes_pattern.py       # /patterns/*
│   │
│   ├── services/                   # 비즈니스 로직
│   │   ├── hybrid_graphiti_service.py   # PKM Type 분류 (8 types)
│   │   ├── entity_cluster_service.py    # 시맨틱 엣지 추론 (50+ types)
│   │   ├── graphiti_service.py          # 코어 Graphiti 통합
│   │   ├── cluster_service.py           # UMAP + HDBSCAN 클러스터링
│   │   ├── ontology_service.py          # LLM 엔티티 추출
│   │   ├── vector_service.py            # OpenAI 임베딩
│   │   ├── context_service.py           # 노트 컨텍스트
│   │   ├── llm_client.py                # Claude/OpenAI 클라이언트
│   │   └── graphrag_retriever.py        # neo4j-graphrag 통합
│   │
│   ├── db/
│   │   ├── neo4j.py                # Neo4j HTTP API 클라이언트
│   │   └── neo4j_bolt.py           # Bolt 드라이버 (Graphiti용)
│   │
│   └── schemas/                    # Pydantic 모델
│       ├── note.py
│       ├── cluster.py
│       └── ...
│
├── requirements.txt
├── Dockerfile
└── railway.json
```

### 프론트엔드 (`didymos-obsidian/`)

```
didymos-obsidian/
├── src/
│   ├── main.ts                     # 플러그인 진입점
│   ├── api/
│   │   └── client.ts               # API 클라이언트
│   ├── views/
│   │   ├── graphView.ts            # Vault Graph (8 클러스터)
│   │   ├── contextView.ts          # 노트 컨텍스트 패널
│   │   └── ...
│   └── settings.ts                 # 플러그인 설정
│
├── manifest.json
├── package.json
└── esbuild.config.mjs
```

---

## 핵심 서비스 상세

### 1. Hybrid Graphiti Service

**파일**: `app/services/hybrid_graphiti_service.py`

**목적**: Graphiti 엔티티를 8 PKM Types로 분류

```python
PKM_TYPES = ["Goal", "Project", "Task", "Topic", "Concept", "Question", "Insight", "Resource"]

CLASSIFICATION_RULES = {
    "Goal": [
        lambda name: "goal" in name.lower() or "objective" in name.lower()
    ],
    "Question": [
        lambda name: name.endswith("?")
    ],
    "Project": [
        lambda name: "project" in name.lower() or name.startswith("PKM")
    ],
    # ... 더 많은 규칙
}

# 매칭되지 않는 엔티티용 GPT-5-Mini 분류 fallback
```

**플로우**:
1. Graphiti가 노트에서 엔티티 추출
2. 규칙 기반 분류 (빠름, ~95% 정확도)
3. 나머지 엔티티는 GPT-5-Mini fallback
4. PKM Type 라벨이 Neo4j 노드에 추가됨

### 2. Entity Cluster Service

**파일**: `app/services/entity_cluster_service.py`

**목적**: PKM Type 쌍에서 시맨틱 엣지 타입 추론

```python
PKM_EDGE_TYPE_MATRIX = {
    ("Goal", "Project"): ("ACHIEVED_BY", "달성 수단", "이 목표는 이 프로젝트로 달성"),
    ("Project", "Task"): ("REQUIRES", "필요 작업", "프로젝트에 필요한 태스크"),
    ("Question", "Insight"): ("ANSWERED_BY", "답변", "질문에 대한 답변"),
    # ... 50+ 조합
}

def infer_semantic_edge_type(from_type: str, to_type: str) -> dict:
    edge_info = PKM_EDGE_TYPE_MATRIX.get((from_type, to_type))
    if edge_info:
        return {
            "edge_type": edge_info[0],
            "edge_label": edge_info[1],
            "description": edge_info[2]
        }
    return {"edge_type": "RELATES_TO", "edge_label": "관련", "description": "..."}
```

**핵심 함수**:
- `compute_entity_clusters_hybrid()`: 엔티티가 포함된 8 PKM 클러스터 반환
- `get_cluster_detail()`: 시맨틱 타입이 포함된 엔티티 + 엣지 반환
- `infer_semantic_edge_type()`: 타입 쌍 → 시맨틱 엣지

### 3. Graphiti Service

**파일**: `app/services/graphiti_service.py`

**목적**: 시간 지식 그래프를 위한 코어 Graphiti 통합

```python
# Graphiti 이중 시간 모델
await graphiti.add_episode(
    name=f"note_{note_id}",
    episode_body=content,
    reference_time=note.updated_at,  # 지식이 유효했던 시점
)

# 결과: 다음을 포함하는 Entity 노드
# - valid_at: 관계 시작 시점
# - invalid_at: 관계 종료 시점 (None = 현재)
# - created_at: 시스템에 기록된 시점
```

---

## API 엔드포인트 참조

### 주요 엔드포인트

| 엔드포인트 | 메서드 | 목적 |
|------------|--------|------|
| `/health` | GET | 헬스 체크 |
| `/notes/sync` | POST | 노트를 지식 그래프에 동기화 |
| `/vault/entity-clusters` | GET | 8 PKM 클러스터 + 시맨틱 엣지 조회 |
| `/vault/entity-clusters/detail` | GET | 엣지가 포함된 상세 클러스터 |
| `/vault/thinking-insights` | GET | 집중 영역, 브릿지 개념 |
| `/temporal/insights/stale` | GET | 잊혀진 지식 (30일 이상) |

### Vault Graph API 상세

```
GET /vault/entity-clusters?vault_id={id}&folder_prefix={optional}

응답:
{
  "clusters": [
    {
      "id": "Goal",
      "label": "Goal",
      "color": "#E74C3C",
      "entities": [...],
      "count": 5
    },
    // ... 7개 더
  ],
  "edges": [
    {
      "from": "uuid1",
      "to": "uuid2",
      "semantic_type": "ACHIEVED_BY",
      "semantic_label": "달성 수단"
    }
  ]
}
```

---

## 데이터 모델 (Neo4j)

### 노드 라벨

```cypher
// 코어 PKM Types (8개)
(:Entity {uuid, name, summary, name_embedding[], pkm_type})
  - pkm_type IN ["Goal", "Project", "Task", "Topic", "Concept", "Question", "Insight", "Resource"]

// Graphiti 표준
(:Episodic {uuid, name, content, source_description, reference_time})
(:Note {note_id, title, path, content_hash, updated_at})
(:User {id})
(:Vault {id, name})
```

### 관계

```cypher
// Graphiti 시간 엣지
(e1:Entity)-[:RELATES_TO {
  uuid,
  fact,
  valid_at,
  invalid_at,
  created_at
}]->(e2:Entity)

// 노트 언급
(:Note)-[:MENTIONS {source, valid_at}]->(:Entity)

// Episodic 링크
(:Episodic)-[:MENTIONS]->(:Entity)
(:Note)-[:HAS_EPISODE]->(:Episodic)
```

### 인덱스

```cypher
// 시맨틱 검색용 벡터 인덱스
CREATE VECTOR INDEX entity_embedding FOR (e:Entity) ON e.name_embedding

// 유니크 제약조건
CREATE CONSTRAINT FOR (e:Entity) REQUIRE e.uuid IS UNIQUE
CREATE CONSTRAINT FOR (n:Note) REQUIRE n.note_id IS UNIQUE
```

---

## 개발 Phase (완료)

| Phase | 기능 | 핵심 파일 |
|-------|------|----------|
| 1-8 | Core MVP | `routes_notes.py`, `routes_graph.py` |
| 9 | 패턴 분석 | `pattern_service.py` |
| 10 | 제품 개선 | 문서화 |
| 11 | 시맨틱 클러스터링 | `cluster_service.py` |
| 12 | GraphRAG 검색 | `graphrag_retriever.py` |
| 13 | SKOS 온톨로지 | `ontology_service.py` |
| 14 | ToolsRetriever | `routes_search.py` |
| 15 | Thinking Insights | `routes_graph.py` |
| 16 | PKM Core v2 (8 Types) | `hybrid_graphiti_service.py` |
| 16+ | 시맨틱 엣지 타입 | `entity_cluster_service.py` |

---

## 배포

### Railway 설정

```json
// railway.json
{
  "build": {
    "builder": "DOCKERFILE"
  },
  "deploy": {
    "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/health"
  }
}
```

### 환경 변수

```
NEO4J_URI=neo4j+s://xxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=xxx
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx
```

### 배포 명령어

```bash
# didymos-backend/에서
railway up --detach

# 로그 확인
railway logs

# 재배포
railway redeploy --yes
```

---

## 로컬 개발

### 백엔드 설정

```bash
cd didymos-backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 필수 환경 변수로 .env 생성
uvicorn app.main:app --reload --port 8000
```

### 프론트엔드 설정

```bash
cd didymos-obsidian
npm install
npm run dev

# 프로덕션 빌드
npm run build
```

### API 테스트

```bash
# 헬스 체크
curl http://localhost:8000/health

# 클러스터 조회
curl "http://localhost:8000/vault/entity-clusters?vault_id=test&user_token=xxx"
```

---

## 주요 결정 & 근거

### 왜 8 PKM Types인가 (4개 아니고)?

기존 4가지 타입 (Topic, Project, Task, Person)으로는 다음을 표현 불가:
- **Goal**: 최상위 목표 (OKR의 O)
- **Concept**: 넓은 Topic과 구별되는 구체적 개념
- **Question**: 탐구를 이끄는 연구 질문
- **Insight**: 발견과 결론
- **Resource**: 외부 참조

### 왜 시맨틱 엣지 타입인가 (단순 RELATES_TO 아니고)?

일반 엣지는 실행 가능한 의미를 제공하지 않음:
```
[ML] --RELATES_TO-- [Neural Network]  // 이게 무슨 의미?
```

시맨틱 엣지는 즉시 이해 가능:
```
[Topic: ML] --CONTAINS-- [Concept: Neural Network]  // ML 안의 개념이구나
```

### 왜 Graphiti인가 (단순 LangChain 아니고)?

- **이중 시간 추적**: 기록 시점이 아닌 지식이 유효했던 시점을 앎
- **자동 엔티티 해결**: 중복 엔티티 병합
- **Episode 기반**: 노트 업데이트를 Episode로 자연스럽게 처리

---

## 향후 로드맵

| 기능 | 설명 | 우선순위 |
|------|------|----------|
| 증분 동기화 | 폴더 기반 델타 동기화 | 높음 |
| PROV-O Activity | 아이디어 계보 추적 | 중간 |
| 팀 협업 | 다중 사용자 지식 그래프 | 중간 |
| 모바일 지원 | React Native 앱 | 낮음 |

---

**문서 버전**: 3.0
**최종 검토**: 2025-12-08
