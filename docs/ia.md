# Didymos - 정보 아키텍처

> 시스템 데이터 모델, Neo4j 스키마, API 명세

**최종 수정**: 2025-12-08

---

## 1. 시스템 아키텍처

```
┌──────────────────────────────────────────┐
│          Obsidian 클라이언트              │
│  ┌────────────────────────────────────┐  │
│  │      Didymos 플러그인 (TypeScript) │  │
│  │  - Vault Graph View (8 클러스터)   │  │
│  │  - Context View                    │  │
│  │  - Thinking Insights               │  │
│  │  - Settings                        │  │
│  └────────────────────────────────────┘  │
└──────────────┬───────────────────────────┘
               │ HTTPS/REST
┌──────────────▼───────────────────────────┐
│          FastAPI 백엔드                   │
│  ┌────────────────────────────────────┐  │
│  │  Routes                            │  │
│  │  - /notes/sync                     │  │
│  │  - /vault/entity-clusters          │  │
│  │  - /vault/thinking-insights        │  │
│  │  - /temporal/*                     │  │
│  ├────────────────────────────────────┤  │
│  │  Services                          │  │
│  │  - hybrid_graphiti_service.py      │  │
│  │  - entity_cluster_service.py       │  │
│  │  - graphiti_service.py             │  │
│  │  - ontology_service.py             │  │
│  └────────────────────────────────────┘  │
└──────────────┬───────────────────────────┘
               │ Bolt/Cypher
┌──────────────▼───────────────────────────┐
│         Neo4j AuraDB + Graphiti           │
│  - Entity 노드 (8 PKM Types)              │
│  - Episodic 노드 (Graphiti)               │
│  - 이중 시간 엣지                          │
│  - 벡터 임베딩                             │
└───────────────────────────────────────────┘
```

---

## 2. 데이터 모델 (Neo4j 그래프 스키마)

### 2.1 PKM Core 온톨로지 - 8가지 타입

모든 엔티티는 8가지 PKM 타입 중 정확히 하나로 분류됩니다:

| 타입 | 설명 | 예시 |
|------|------|------|
| **Goal** | 최상위 목표 | "박사 졸업", "스타트업 런칭" |
| **Project** | Goal 달성을 위한 중간 단위 | "3장 작성", "MVP 개발" |
| **Task** | 실행 가능한 최소 단위 | "서론 작성", "API 구현" |
| **Topic** | 주제/카테고리 | "머신러닝", "PKM" |
| **Concept** | Topic 하위의 구체적 개념 | "Transformer", "Zettelkasten" |
| **Question** | 연구 질문 / 미해결 이슈 | "RAG가 환각을 줄이나?" |
| **Insight** | 발견 / 결론 | "HDBSCAN이 K-means보다 우수" |
| **Resource** | 외부 참조 자료 | 논문, 책, URL |

### 2.2 노드 타입

#### Entity (핵심 PKM 노드)
```cypher
(:Entity {
  uuid: String,           // Graphiti 생성 UUID
  name: String,           // 엔티티 이름
  summary: String,        // LLM 생성 요약
  pkm_type: String,       // 8가지 PKM 타입 중 하나
  name_embedding: List<Float>,  // 벡터 임베딩
  created_at: DateTime,
  labels: List<String>    // 추가 Graphiti 라벨
})
```

#### Note
```cypher
(:Note {
  note_id: String,        // 파일 경로 (볼트당 유니크)
  title: String,          // 노트 제목
  path: String,           // 파일 경로
  content_hash: String,   // 변경 감지용 콘텐츠 해시
  tags: List<String>,     // Obsidian 태그
  created_at: DateTime,
  updated_at: DateTime
})
```

#### Episodic (Graphiti)
```cypher
(:Episodic {
  uuid: String,           // Graphiti episode UUID
  name: String,           // Episode 이름
  content: String,        // Episode 콘텐츠
  source_description: String,
  reference_time: DateTime,  // 지식이 유효했던 시점
  created_at: DateTime
})
```

#### User & Vault
```cypher
(:User {
  id: String,
  email: String,
  created_at: DateTime,
  subscription: String    // "free" | "pro" | "research"
})

(:Vault {
  id: String,
  name: String,
  created_at: DateTime,
  last_synced: DateTime
})
```

---

### 2.3 관계

#### 핵심 Graphiti 관계

```cypher
// Entity 간 관계 (이중 시간)
(e1:Entity)-[:RELATES_TO {
  uuid: String,
  fact: String,           // 관계 설명
  valid_at: DateTime,     // 관계 시작 시점
  invalid_at: DateTime,   // 관계 종료 시점 (null = 현재)
  created_at: DateTime,   // 시스템 기록 시점
  expired_at: DateTime    // 대체된 시점
}]->(e2:Entity)
```

#### Note 관계

```cypher
// Note가 Entity 언급
(:Note)-[:MENTIONS {
  source: String,
  valid_at: DateTime
}]->(:Entity)

// 노트 간 내부 링크
(:Note)-[:LINKS_TO {
  link_text: String,
  created_at: DateTime
}]->(:Note)
```

#### Episode 관계

```cypher
(:Episodic)-[:MENTIONS]->(:Entity)
(:Note)-[:HAS_EPISODE]->(:Episodic)
```

#### 소유 관계

```cypher
(:User)-[:OWNS]->(:Vault)
(:Vault)-[:HAS_NOTE]->(:Note)
```

---

### 2.4 시맨틱 엣지 타입 매트릭스

PKM 타입 조합 기반으로 50+ 시맨틱 엣지 타입이 자동 추론됩니다:

```python
PKM_EDGE_TYPE_MATRIX = {
    # Goal 관계
    ("Goal", "Project"): ("ACHIEVED_BY", "달성 수단", "이 목표는 이 프로젝트로 달성"),
    ("Goal", "Task"): ("REQUIRES", "필요 태스크", "목표에 직접 필요한 태스크"),
    ("Goal", "Topic"): ("FOCUSES_ON", "집중 영역", "목표의 주제 영역"),
    ("Goal", "Insight"): ("INFORMED_BY", "전략적 통찰", "목표에 영향을 주는 인사이트"),

    # Project 관계
    ("Project", "Task"): ("REQUIRES", "필요 작업", "프로젝트에 필요한 태스크"),
    ("Project", "Topic"): ("INVOLVES", "관련 분야", "프로젝트 관련 주제"),
    ("Project", "Concept"): ("USES", "사용 개념", "프로젝트에서 사용하는 개념"),
    ("Project", "Insight"): ("PRODUCES", "도출 인사이트", "프로젝트에서 도출된 통찰"),
    ("Project", "Resource"): ("REFERENCES", "참고 자료", "프로젝트에서 사용한 자료"),

    # Question → Answer 사이클
    ("Question", "Insight"): ("ANSWERED_BY", "답변", "질문에 대한 답변 인사이트"),
    ("Question", "Resource"): ("RESEARCHED_IN", "연구 출처", "질문이 탐구된 자료"),
    ("Question", "Topic"): ("ABOUT", "주제", "질문의 주제"),

    # Insight 관계
    ("Insight", "Resource"): ("DERIVED_FROM", "출처", "인사이트의 출처 자료"),
    ("Insight", "Concept"): ("CLARIFIES", "명확화", "인사이트가 명확히 하는 개념"),
    ("Insight", "Topic"): ("CONTRIBUTES_TO", "기여", "인사이트가 기여하는 주제"),

    # Topic → Concept 계층
    ("Topic", "Concept"): ("CONTAINS", "포함 개념", "주제에 포함된 개념"),
    ("Topic", "Topic"): ("RELATED_TO", "관련 주제", "연관된 주제"),
    ("Concept", "Concept"): ("RELATES_TO", "관련 개념", "연관된 개념"),

    # Resource 관계
    ("Resource", "Topic"): ("COVERS", "다루는 주제", "자료가 다루는 주제"),
    ("Resource", "Concept"): ("EXPLAINS", "설명", "자료가 설명하는 개념"),

    # Task 관계
    ("Task", "Task"): ("BLOCKS", "의존성", "이 태스크가 다른 태스크를 블록"),
    ("Task", "Resource"): ("NEEDS", "필요 자료", "태스크에 필요한 자료"),

    # ... 총 50+ 조합
}
```

---

## 3. API 명세

### 3.1 핵심 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
|------------|--------|------|
| `/health` | GET | 헬스 체크 |
| `/notes/sync` | POST | 노트를 지식 그래프에 동기화 |
| `/vault/entity-clusters` | GET | 8 PKM 클러스터 + 시맨틱 엣지 조회 |
| `/vault/entity-clusters/detail` | GET | 모든 엣지가 포함된 상세 클러스터 |
| `/vault/thinking-insights` | GET | 집중 영역, 브릿지 개념 |
| `/temporal/insights/stale` | GET | 잊혀진 지식 (30일 이상) |

### 3.2 Note 동기화 API

#### POST `/notes/sync`

**요청**
```json
{
  "user_token": "jwt_token",
  "vault_id": "vault_001",
  "note": {
    "note_id": "research/ml-clustering.md",
    "title": "ML 클러스터링 방법론",
    "path": "research/ml-clustering.md",
    "content": "# ML 클러스터링 방법론\n...",
    "yaml": {
      "date": "2024-01-15",
      "tags": ["ml", "clustering"]
    },
    "tags": ["ml", "clustering"],
    "links": ["research/hdbscan.md"],
    "created_at": "2024-01-15T10:00:00Z",
    "updated_at": "2024-01-15T15:30:00Z"
  }
}
```

**응답**
```json
{
  "status": "ok",
  "note_id": "research/ml-clustering.md",
  "entities_extracted": {
    "nodes": 5,
    "edges": 3
  },
  "graphiti_episode_id": "ep_abc123"
}
```

### 3.3 Entity Clusters API

#### GET `/vault/entity-clusters`

**파라미터**
- `vault_id` (필수): Vault 식별자
- `user_token` (필수): 인증 토큰
- `folder_prefix` (선택): 폴더 필터 (예: "1-Research/")

**응답**
```json
{
  "clusters": [
    {
      "id": "Goal",
      "label": "Goal",
      "color": "#E74C3C",
      "entities": [
        {
          "uuid": "uuid-001",
          "name": "박사 졸업",
          "summary": "2025년 Q4까지 박사 논문 완료"
        }
      ],
      "count": 5
    },
    {
      "id": "Project",
      "label": "Project",
      "color": "#E67E22",
      "entities": [...],
      "count": 12
    }
    // ... 총 8개 클러스터
  ],
  "edges": [
    {
      "from": "uuid-001",
      "from_name": "박사 졸업",
      "from_type": "Goal",
      "to": "uuid-002",
      "to_name": "3장 작성",
      "to_type": "Project",
      "semantic_type": "ACHIEVED_BY",
      "semantic_label": "달성 수단",
      "semantic_description": "이 목표는 이 프로젝트로 달성"
    }
  ],
  "semantic_edge_stats": {
    "total": 605,
    "unique_types": 15,
    "type_distribution": {
      "ACHIEVED_BY": 45,
      "REQUIRES": 120,
      "CONTAINS": 89
    }
  }
}
```

### 3.4 Thinking Insights API

#### GET `/vault/thinking-insights`

**응답**
```json
{
  "focus_areas": [
    {
      "name": "Machine Learning",
      "mention_count": 45,
      "sample_notes": ["research/ml-paper.md", "projects/ml-pipeline.md"]
    }
  ],
  "bridge_concepts": [
    {
      "name": "Data Pipeline",
      "connected_areas": ["ML", "Engineering"],
      "strength": 8.5
    }
  ],
  "isolated_areas": [
    {
      "name": "Quantum Computing",
      "note_count": 3,
      "suggestion": "ML 또는 Physics 주제에 연결 권장"
    }
  ],
  "time_trends": {
    "emerging": ["LLM Fine-tuning", "RAG"],
    "declining": ["Web3"]
  },
  "health_score": {
    "overall": 78,
    "connection_density": 0.65,
    "isolation_ratio": 0.12
  }
}
```

### 3.5 Temporal API

#### GET `/temporal/insights/stale`

**파라미터**
- `days` (선택, 기본값: 30): 일수 기준

**응답**
```json
{
  "stale_entities": [
    {
      "uuid": "uuid-123",
      "name": "Docker 배포",
      "pkm_type": "Topic",
      "last_mentioned": "2024-10-15T00:00:00Z",
      "days_since_mention": 54,
      "related_notes_count": 5
    }
  ],
  "total_stale": 12,
  "recommendation": "이 잊혀진 주제들을 검토하고 업데이트하세요"
}
```

---

## 4. 데이터 플로우

### 4.1 Note 동기화 플로우

```
1. 사용자가 Obsidian에서 노트 저장
       ↓
2. 플러그인이 POST /notes/sync 전송
       ↓
3. 백엔드가 Graphiti로 처리
   - Episode 생성
   - Entity 자동 추출
   - 이중 시간 타임스탬프
       ↓
4. Hybrid Service가 PKM 라벨 추가
   - 규칙 기반 분류 (~95%)
   - GPT-5-Mini fallback (~5%)
       ↓
5. Entity가 Neo4j에 저장:
   - name, summary
   - pkm_type 라벨
   - name_embedding 벡터
       ↓
6. 플러그인에 응답 반환
```

### 4.2 Vault Graph 데이터 플로우

```
1. 플러그인이 GET /vault/entity-clusters 요청
       ↓
2. 백엔드가 Neo4j에서 엔티티 조회
   MATCH (e:Entity)
   WHERE e.group_id = $vault_id
   RETURN e
       ↓
3. pkm_type으로 엔티티 그룹화 (8 클러스터)
       ↓
4. 엔티티 간 RELATES_TO 엣지 조회
       ↓
5. 각 엣지에 대해 시맨틱 타입 추론:
   (from_type, to_type) → PKM_EDGE_TYPE_MATRIX → semantic_type
       ↓
6. 클러스터 + 시맨틱 엣지를 플러그인에 반환
       ↓
7. 플러그인이 vis-network로 렌더링
```

---

## 5. 인덱스 및 제약조건

### 5.1 Neo4j 인덱스

```cypher
// 시맨틱 검색용 벡터 인덱스
CREATE VECTOR INDEX entity_embedding FOR (e:Entity) ON e.name_embedding
OPTIONS {indexConfig: {
  `vector.dimensions`: 1536,
  `vector.similarity_function`: 'cosine'
}}

// 유니크 제약조건
CREATE CONSTRAINT entity_uuid FOR (e:Entity) REQUIRE e.uuid IS UNIQUE
CREATE CONSTRAINT note_id FOR (n:Note) REQUIRE n.note_id IS UNIQUE

// 성능 인덱스
CREATE INDEX entity_pkm_type FOR (e:Entity) ON (e.pkm_type)
CREATE INDEX entity_group_id FOR (e:Entity) ON (e.group_id)
CREATE INDEX note_updated FOR (n:Note) ON (n.updated_at)
```

### 5.2 Graphiti 인덱스

Graphiti가 자동 생성:
- `entity_name_idx` - Entity 이름 풀텍스트 검색
- `episodic_reference_time_idx` - 시간 쿼리
- `edge_valid_at_idx` - 이중 시간 엣지 쿼리

---

## 6. PKM 타입 색상 스키마

| PKM 타입 | 색상 | Hex |
|----------|------|-----|
| Goal | 빨강 | `#E74C3C` |
| Project | 주황 | `#E67E22` |
| Task | 노랑 | `#F1C40F` |
| Topic | 초록 | `#2ECC71` |
| Concept | 청록 | `#1ABC9C` |
| Question | 파랑 | `#3498DB` |
| Insight | 보라 | `#9B59B6` |
| Resource | 회색 | `#95A5A6` |

---

## 7. 보안 & 프라이버시

### 7.1 인증
- API 인증용 JWT 토큰
- 만료 시 토큰 갱신

### 7.2 데이터 격리
- 모든 쿼리가 `vault_id`로 필터링
- 사용자는 자신의 볼트만 접근 가능

### 7.3 프라이버시 옵션
- **Full 모드**: 전체 콘텐츠 전송
- **Summary 모드**: 요약만 전송
- **Metadata 모드**: 태그와 링크만
- **제외 폴더**: 비공개 폴더 건너뛰기

---

**문서 버전**: 4.0
**최종 검토**: 2025-12-08
