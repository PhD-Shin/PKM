# Didymos - PRD (제품 요구사항 문서)

> AI 기반 Obsidian 2nd Brain - PKM 시맨틱 온톨로지 + 시간 지식 그래프

**최종 수정**: 2025-12-08
**현재 상태**: Phase 17 완료 (Refactoring & Graph Visualization Polish)
**비즈니스 모델**: Obsidian 플러그인 구독 ($7-15/월)
**핵심 기술**: Graphiti (저장/추출) + PKM 시맨틱 엣지 타입

---

## 제품 요약

### 제품 비전

**"당신의 사고를 실행 가능한 온톨로지로 시각화"**

Didymos는 Obsidian 볼트를 실행 가능한 온톨로지로 변환합니다. 단순한 노트 그래프가 아닌, 의사결정을 지원하는 시맨틱 관계를 가진 구조화된 지식 시스템입니다.

### 핵심 차별점

| 기능 | Smart Connections | InfraNodus | Didymos |
|------|-------------------|------------|---------|
| **그래프 단위** | 노트 | 단어 (동시 출현) | **개념** (PKM Types) |
| **엣지 의미** | 유사도 % | 동시 출현 가중치 | **시맨틱 타입** (ACHIEVED_BY, REQUIRES 등) |
| **구조** | 평면적 유사도 | 단어 네트워크 | **8타입 온톨로지** (Goal, Project, Task 등) |
| **실행 가능성** | 유사 노트 찾기 | 중심 단어 찾기 | **"Goal X는 Project Y로 달성"** |
| **시간 추적** | 없음 | 없음 | 이중 시간 (Graphiti) |

### PKM 시맨틱 온톨로지의 필요성

**단어 기반 그래프의 문제 (InfraNodus)**:
```
"학생이 교수를 평가한다" vs "교수가 학생을 평가한다"
→ 같은 단어, 완전히 다른 의미
→ 단어 동시 출현 그래프는 이를 동일하게 처리
```

**유사도 기반 그래프의 문제 (Smart Connections)**:
```
"노트 A가 노트 B와 78% 유사"
→ 그래서 관계가 뭔데?
→ 실행 가능한 인사이트 없음, 숫자만 있음
```

**Didymos 솔루션 - PKM 시맨틱 엣지 타입**:
```
Goal: "박사 졸업"
  └─ ACHIEVED_BY → Project: "3장 작성"
                      └─ REQUIRES → Task: "문헌 조사"

Question: "RAG가 환각을 줄이나?"
  └─ ANSWERED_BY → Insight: "RAG는 사실 정확도 40% 향상"
                      └─ DERIVED_FROM → Resource: "Stanford 논문 2024"
```

모든 엣지가 PKM 타입 조합에서 파생된 **시맨틱 의미**를 가짐.

---

## 1. PKM Core Ontology v2

### 1.1 8가지 핵심 타입

| 타입 | 설명 | 예시 |
|------|------|------|
| **Goal** | 최상위 목표 (OKR의 O) | "박사 졸업", "스타트업 런칭" |
| **Project** | Goal 달성을 위한 중간 단위 | "3장 작성", "MVP 개발" |
| **Task** | 실행 가능한 최소 단위 | "서론 작성", "API 구현" |
| **Topic** | 주제/카테고리 | "머신러닝", "PKM" |
| **Concept** | Topic 하위의 구체적 개념 | "Transformer", "Zettelkasten" |
| **Question** | 연구 질문 / 미해결 이슈 | "RAG가 환각을 줄이나?" |
| **Insight** | 발견 / 결론 | "HDBSCAN이 K-means보다 우수" |
| **Resource** | 외부 참조 자료 | 논문, 책, URL |

### 1.2 시맨틱 엣지 타입 매트릭스

PKM 타입 조합에서 자동 추론되는 50+ 시맨틱 엣지 타입:

```python
PKM_EDGE_TYPE_MATRIX = {
    # Goal 관계
    ("Goal", "Project"): ("ACHIEVED_BY", "달성 수단", "이 목표는 이 프로젝트로 달성"),
    ("Goal", "Task"): ("REQUIRES", "필요 태스크", "목표에 필요한 태스크"),

    # Project 관계
    ("Project", "Task"): ("REQUIRES", "필요 작업", "프로젝트에 필요한 작업"),
    ("Project", "Concept"): ("USES", "사용 개념", "프로젝트에서 사용하는 개념"),
    ("Project", "Insight"): ("PRODUCES", "도출 인사이트", "프로젝트에서 도출된 통찰"),

    # Question → Insight (지식 사이클)
    ("Question", "Insight"): ("ANSWERED_BY", "답변", "질문에 대한 답변 인사이트"),
    ("Insight", "Resource"): ("DERIVED_FROM", "출처", "인사이트의 출처 자료"),

    # Topic → Concept (시맨틱 계층)
    ("Topic", "Concept"): ("CONTAINS", "포함 개념", "주제에 포함된 개념"),
    ("Concept", "Concept"): ("RELATES_TO", "관련 개념", "연관된 개념"),

    # ... 50+ 조합
}
```

### 1.3 실행 가능한 온톨로지 시각화

일반적인 "RELATES_TO" 엣지와의 차이:

```
Before (일반):
  [ML] ──RELATES_TO── [Neural Network] ──RELATES_TO── [Transformer]

After (시맨틱):
  [Topic: ML] ──CONTAINS── [Concept: Neural Network] ──BROADER── [Concept: Transformer]
```

사용자가 즉시 이해 가능:
- **무엇이** 존재하는지 (8 PKM Types)
- **어떻게** 연결되는지 (시맨틱 엣지 타입)
- **무엇을 해야 하는지** (Goal → Project → Task 계층)

### 1.4 인터랙티브 시각화 (New)

- **엔티티 클릭**: 상세 패널(Modal) 표시 (요약, 타입, 멘션 수, 연결된 노트)
- **노드 간격**: 물리학(Physics) 기반으로 노드 간 충분한 간격 확보 (Sticky 현상 제거)
- **라벨 가시성**: `inter_cluster` 등 기계적 라벨 제거, 의미 있는 관계만 표시

---

## 2. 기술 아키텍처

### 2.1 시스템 개요

```
┌─────────────────────────────────────────────────────────────┐
│                    Obsidian 플러그인 (TypeScript)            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ Vault Graph  │  │ Note Context │  │ Thinking Insights│   │
│  │ (8 클러스터) │  │    Panel     │  │     Panel        │   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
└─────────────────────────┬───────────────────────────────────┘
                          │ REST API (HTTPS)
┌─────────────────────────▼───────────────────────────────────┐
│                 FastAPI 서버 (Python 3.11)                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Hybrid Graphiti Service                    │ │
│  │  ┌─────────────────┐    ┌────────────────────────────┐ │ │
│  │  │ Graphiti Core   │    │ PKM Type Classification    │ │ │
│  │  │ - Episode →     │    │ - 8 Types (CLASSIFICATION  │ │ │
│  │  │   Entity Extract│    │   _RULES)                  │ │ │
│  │  │ - Bi-temporal   │    │ - GPT-5-Mini fallback      │ │ │
│  │  └─────────────────┘    └────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │           Entity Cluster Service                        │ │
│  │  ┌─────────────────┐    ┌────────────────────────────┐ │ │
│  │  │ PKM 8-Type      │    │ Semantic Edge Inference    │ │ │
│  │  │ Clustering      │    │ (PKM_EDGE_TYPE_MATRIX)     │ │ │
│  │  └─────────────────┘    └────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
     ┌────▼────┐     ┌────▼────┐     ┌───▼──────┐
     │ Neo4j   │     │ OpenAI  │     │ GPT-5    │
     │ AuraDB  │     │Embeddings│    │ Mini     │
     └─────────┘     └─────────┘     └──────────┘
```

### 2.2 데이터 플로우

```
1. Obsidian에서 노트 저장
       ↓
2. 플러그인이 /notes/sync로 전송
       ↓
3. Graphiti가 Episode로 처리
   - Entity 자동 추출
   - 이중 시간 타임스탬프 (valid_at, created_at)
   - RELATES_TO 엣지 생성
       ↓
4. Hybrid Service가 PKM 라벨 추가
   - 규칙 기반 분류 (빠름)
   - GPT-5-Mini fallback (정확)
       ↓
5. Entity Cluster Service
   - PKM Type으로 엔티티 그룹화 (8 클러스터)
   - 타입 쌍에서 시맨틱 엣지 타입 추론
       ↓
6. Vault Graph API 응답
   - 8개 PKM Type 클러스터 + 엔티티
   - semantic_type, semantic_label이 포함된 엣지
   - 실행 가능한 시각화 준비 완료
```

### 2.3 핵심 서비스

| 서비스 | 파일 | 책임 |
|--------|------|------|
| `hybrid_graphiti_service.py` | PKM Type 분류 | Graphiti 엔티티에 8 PKM 라벨 추가 |
| `entity_cluster_service.py` | 시맨틱 엣지 추론 | PKM 타입 쌍에서 엣지 타입 추론 |
| `graphiti_service.py` | 코어 저장소 | Graphiti Episode 처리, 이중 시간 |
| `cluster_service.py` | 클러스터 계산 | UMAP + HDBSCAN, LLM 요약 |
| `note_service.py` | 노트 관리 | (Refactored) 노트 동기화 및 생명주기 관리 |
| `sync_service.ts` | Obsidian Sync | (Frontend) 노트 변경사항 감지 및 동기화 담당 |
| `ontology_service.ts` | 온톨로지 | (Frontend) 온톨로지 데이터 관리 및 내보내기 |

---

## 3. API 명세

### 3.1 Vault Graph API

```
GET /vault/entity-clusters
    ?vault_id={id}
    &folder_prefix={optional, e.g., "1-Research/"}

응답:
{
  "clusters": [
    {
      "id": "Goal",
      "label": "Goal",
      "color": "#E74C3C",
      "entities": [
        {"uuid": "...", "name": "박사 졸업", "summary": "..."}
      ],
      "count": 5
    },
    // ... 7개 더 (총 8개 PKM Types)
  ],
  "edges": [
    {
      "from": "uuid1",
      "from_name": "박사 졸업",
      "from_type": "Goal",
      "to": "uuid2",
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

### 3.2 Thinking Insights API

```
GET /vault/thinking-insights
    ?vault_id={id}

응답:
{
  "focus_areas": [
    {"name": "Machine Learning", "mention_count": 45, "sample_notes": [...]}
  ],
  "bridge_concepts": [
    {"name": "Data Pipeline", "connected_areas": ["ML", "Engineering"], "strength": 8.5}
  ],
  "isolated_areas": [
    {"name": "Quantum Computing", "note_count": 3, "suggestion": "ML에 연결 권장"}
  ],
  "time_trends": {
    "emerging": ["LLM Fine-tuning"],
    "declining": ["Web3"]
  },
  "health_score": {
    "overall": 78,
    "connection_density": 0.65,
    "isolation_ratio": 0.12
  }
}
```

### 3.3 Temporal API

```
GET /temporal/insights/stale?days=30
    → 잊혀진 지식 리마인더

POST /temporal/search
    Body: {query, start_date, end_date}
    → 시간 인식 하이브리드 검색
```

---

## 4. 비즈니스 모델

### 4.1 가격 티어

| 티어 | 가격 | 기능 |
|------|------|------|
| **Free** | $0 | 100 노트, 기본 그래프, 주간 동기화 |
| **Pro** | $7/월 | 무제한 노트, 실시간 동기화, 8타입 클러스터링 |
| **Research** | $15/월 | + 시맨틱 엣지, API 접근, 팀 공유 (5명) |

### 4.2 비용 구조 (사용자/월 당)

- Neo4j AuraDB: ~$0.50
- GPT-5-Mini API: ~$1.00
- OpenAI Embeddings: ~$0.50
- 인프라: ~$0.30
- **총계**: ~$2.30
- **마진**: $4.70 (Pro), $12.70 (Research)

---

## 5. 구현 현황

### 5.1 완료된 기능

| Phase | 기능 | 상태 |
|-------|------|------|
| 1-8 | Core MVP (동기화, 그래프, 태스크) | ✅ 완료 |
| 9-11 | 시맨틱 클러스터링 (UMAP + HDBSCAN) | ✅ 완료 |
| 12-14 | GraphRAG + SKOS + ToolsRetriever | ✅ 완료 |
| 15 | Thinking Insights (집중, 브릿지, 고립) | ✅ 완료 |
| 16 | PKM Core Ontology v2 (8 Types) | ✅ 완료 |
| 16+ | **시맨틱 엣지 타입** | ✅ 완료 |

### 5.2 현재 상태 (2025-12-08)

- **635개 엔티티** - 8 PKM Types로 분류됨
- **605개 엣지** - 시맨틱 타입 추론 적용
- **50+ 시맨틱 엣지 타입** (ACHIEVED_BY, REQUIRES, CONTAINS 등)
- **폴더 기반 필터링** - 컨텍스트 분리
- **개선된 UX** - 인터랙티브 엔티티 클릭, 최적화된 그래프 레이아웃
- **안정성** - 주요 로직을 독립적인 Service로 리팩토링 (`NoteService`, `SyncService` 등)

### 5.3 향후 로드맵

| Phase | 기능 | 설명 |
|-------|------|------|
| 17-18 | Research/Maker 팩 | 선택적 도메인 확장 |
| 19 | PROV-O Activity | 아이디어 계보 추적 |
| 20 | 증분 동기화 | 폴더 기반 델타 동기화 |
| 21 | 팀 협업 | 다중 사용자 지식 그래프 |

---

## 6. 배포

### 6.1 인프라

- **백엔드**: Railway (FastAPI Docker)
- **데이터베이스**: Neo4j AuraDB
- **플러그인**: Obsidian Community Plugins / BRAT

### 6.2 URL

- Production API: `https://didymos-backend-production.up.railway.app`
- Health Check: `/health`

---

## 부록 A: PKM 엣지 타입 참조

| From Type | To Type | 시맨틱 엣지 | 설명 |
|-----------|---------|-------------|------|
| Goal | Project | ACHIEVED_BY | 이 목표는 이 프로젝트로 달성 |
| Goal | Task | REQUIRES | 목표에 필요한 태스크 |
| Project | Task | REQUIRES | 프로젝트에 필요한 작업 |
| Project | Concept | USES | 프로젝트에서 사용하는 개념 |
| Question | Insight | ANSWERED_BY | 질문에 대한 답변 인사이트 |
| Insight | Resource | DERIVED_FROM | 인사이트의 출처 자료 |
| Topic | Concept | CONTAINS | 주제에 포함된 개념 |
| Concept | Concept | RELATES_TO | 연관된 개념 |

전체 매트릭스: `entity_cluster_service.py`에 50+ 조합

---

**문서 버전**: 5.0
**최종 검토**: 2025-12-08
**변경 사항**:
- PKM 시맨틱 엣지 타입 (50+ 매핑) 추가
- PKM Core Ontology v2 (8 Types) 업데이트
- 아키텍처 문서 간소화
- 한글화
