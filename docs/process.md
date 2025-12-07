# Didymos - 개발 프로세스 및 진행 상황

> "Smart Connections를 넘어선 구조화된 2nd Brain"
> Obsidian 플러그인 구독 모델 - MVP 2주 스프린트

**Last Updated**: 2025-12-03
**Status**: Phase 15 완료 (MVP 100%), 베타 테스트 준비
**핵심 기술**: Graphiti (저장/추출) + neo4j-graphrag (검색/질의) 병용 아키텍처

---

## 프로젝트 개요

### 제품 포지셔닝

| 기능 | Smart Connections | InfraNodus | Didymos |
|------|-------------------|------------|---------|
| **검색** | 유사 노트 찾기 | 단어 빈도 기반 | GraphRAG 하이브리드 |
| **그래프 단위** | 노트 | 단어 (co-occurrence) | **개념** (ontology) |
| **구조** | 평면적 | 단어 네트워크 | **계층적 지식 그래프 (SKOS)** |
| **분석** | 없음 | 단어 중심성 | 의사결정 인사이트 |
| **LLM** | 임베딩만 | 없음 | 개념 추출 + 클러스터 요약 |
| **관계 추출** | 없음 | 동시 출현만 | **주어-술어-목적어** |
| **시간 추론** | 없음 | 없음 | **Bi-temporal (Graphiti)** |

> **왜 단어가 아닌 개념인가?**
> InfraNodus는 단어 동시출현(co-occurrence)으로 그래프를 만들지만, 이는 "언어의 껍데기"만 캡처합니다.
> Didymos는 LLM으로 **개념(Concept)**을 추출하고 **관계(Relation)**를 명시적으로 추출하여 진정한 지식 구조를 형성합니다.

### 타겟 사용자
1. **PhD/연구자**: 논문 리뷰, 문헌 정리
2. **PKM 파워유저**: 1000+ 노트, Zettelkasten 실천
3. **의사결정자**: 프로젝트 관리, 전략적 사고

---

## 비즈니스 모델

### 요금제

| 티어 | 가격 | 기능 | 타겟 |
|------|------|------|------|
| **Free** | $0 | 100 노트, 주 1회 sync | 일반 사용자 |
| **Pro** | $7/월 | 무제한 노트, 실시간 sync | 파워유저 |
| **Research** | $15/월 | + 고급 분석, API | 연구자 |

### 비용 구조 (사용자당/월)
- Neo4j Aura: ~$0.50
- Claude API: ~$1.50
- 인프라: ~$0.30
- **총**: ~$2.30/user/month
- **마진**: $4.70 (Pro), $12.70 (Research)

---

## 기술 아키텍처

### 스택
- **Backend**: FastAPI, LangChain, LangGraph
- **Database**: Neo4j AuraDB
- **AI**: Claude 3.5 Sonnet (클러스터 요약), OpenAI Embeddings (클러스터링), GPT-5 Mini (엔티티 추출)
- **Storage Layer**: Graphiti (Zep AI) - Bi-temporal 지식 그래프, 엔티티 추출/저장
- **Query Layer**: neo4j-graphrag - GraphRAG 검색 (Vector, Text2Cypher, VectorCypher, Tools)
- **Frontend**: Obsidian Plugin (TypeScript), vis-network
- **Clustering**: UMAP + HDBSCAN
- **Ontology**: PKM Ontology v1 (SKOS, FOAF, PROV-O 기반)

### 데이터 흐름

```
┌─────────────────────────────────────────────────────────────┐
│                    STORAGE LAYER (Graphiti)                  │
└─────────────────────────────────────────────────────────────┘

Obsidian 노트 수정 → 플러그인 감지 → FastAPI /notes/sync
    ↓
┌─────────────────────────────────────┐
│ Graphiti 자동 처리                  │
│ 1. Entity 추출 + 요약 생성          │
│ 2. Relation 추출 (SKOS 계층 포함)   │
│ 3. 기존 Entity와 병합/업데이트      │
│ 4. Bi-temporal 시간 정보 기록       │
└─────────────────────────────────────┘
    ↓
Neo4j 저장 (PKM Ontology v1 스키마)

┌─────────────────────────────────────────────────────────────┐
│                    QUERY LAYER (neo4j-graphrag)              │
└─────────────────────────────────────────────────────────────┘

사용자 질의 → Retriever 선택 (Vector/Text2Cypher/Hybrid/Agentic)
    ↓
GraphRAG 하이브리드 검색 → UMAP + HDBSCAN 클러스터링
    ↓
Claude 클러스터 요약 → vis-network 시각화
```

---

## 전체 진행 상황

### 현재 상태 (2025-12-03)

| Phase | 상태 | 설명 |
|-------|------|------|
| 0-8 | ✅ 완료 | 기본 MVP |
| 9 | ✅ 완료 | 패턴 분석 & 의사결정 추천 |
| 10 | ✅ 완료 | 비즈니스 모델 정립 & 재기획 |
| 11 | ✅ 완료 | 의미론적 클러스터링 MVP |
| 12 | ✅ 완료 | GraphRAG 검색 강화 |
| 13 | ✅ 완료 | SKOS 온톨로지 자동 생성 |
| 14 | ✅ 완료 | ToolsRetriever 통합 |
| 15 | ✅ 완료 | Thinking Insights & 2nd Brain 강화 |
| 16 | ✅ 완료 | PKM Core Ontology v2 (8 노드) |
| 17-18 | 🔸 Optional | Research Pack / Solo Maker Pack (Deferred) |

**기술 MVP 완성도**: 100%
**제품 시장 적합성**: 재정의 완료, 베타 테스트 준비

---

## Phase별 체크리스트

### Phase 0: 환경 설정
**예상 시간**: 1~2시간 | [📖 상세 가이드](phases/phase-0-setup.md)

- [x] Python 3.11+, Node.js 18+ 설치
- [x] Neo4j AuraDB 생성
- [x] OpenAI API 키 발급
- [x] 프로젝트 디렉토리 구조 생성
- [x] Git 초기화 및 환경 변수 설정

### Phase 1: 백엔드 인프라
**예상 시간**: 2~3시간 | [📖 상세 가이드](phases/phase-1-infra.md)

- [x] requirements.txt (langchain, langchain-neo4j, langgraph 포함)
- [x] Neo4j 연결 모듈 (HTTP API)
- [x] FastAPI 서버 실행 확인

### Phase 2: 노트 동기화 파이프라인
**예상 시간**: 4~5시간 | [📖 Backend](phases/phase-2-sync-backend.md) | [📖 Frontend](phases/phase-2-sync-frontend.md)

- [x] NotePayload / NoteSyncRequest 스키마 정의
- [x] upsert_note() (User/Vault/Note MERGE)
- [x] /notes/sync FastAPI 엔드포인트
- [x] Obsidian 플러그인 초기화 (TypeScript + esbuild)
- [x] 노트 저장 시 자동 동기화 및 알림

### Phase 3: AI 온톨로지 추출
**예상 시간**: 2~3시간 | [📖 상세 가이드](phases/phase-3-ai.md)

- [x] LangChain LLMGraphTransformer 도입
- [x] allowed_nodes (Topic, Project, Task, Person) 설정
- [x] Graph-based Entity Resolution (2단계 추출)
- [ ] Graphiti 통합 (진행 중)

### Phase 4: Context Panel (Hybrid Search)
**예상 시간**: 4~5시간 | [📖 Backend](phases/phase-4-context-backend.md) | [📖 Frontend](phases/phase-4-context-frontend.md)

- [x] 벡터 임베딩 생성 및 저장 (OpenAI Embeddings)
- [x] 구조적(Graph) + 의미적(Vector) 하이브리드 추천 알고리즘
- [x] Obsidian UI: Context View

### Phase 5: Graph Panel (Visualization)
**예상 시간**: 5~6시간 | [📖 Backend](phases/phase-5-graph-backend.md) | [📖 Frontend](phases/phase-5-graph-frontend.md)

- [x] Graph API: vis-network 포맷
- [x] 노드 클릭/더블클릭 인터랙션
- [x] 노드 필터/레이블/레이아웃 옵션
- [x] Note/Vault 모드 전환
- [x] Sync All Notes 버튼
- [x] Control Panel, Auto-Hop 시스템
- [x] Topic 클러스터링, 증분 동기화

### Phase 6: Task 관리
**예상 시간**: 3~4시간 | [📖 상세 가이드](phases/phase-6-tasks.md)

- [x] Task CRUD API
- [x] Task 상태 관리 (todo/in_progress/done)
- [x] Obsidian UI: Task Panel

### Phase 7: Weekly Review
**예상 시간**: 3~4시간 | [📖 상세 가이드](phases/phase-7-review.md)

- [x] 주간 리뷰 API
- [x] 새 토픽/잊힌 프로젝트/미완료 태스크/활성 노트 쿼리
- [x] Obsidian UI: Review Panel

### Phase 8: 배포 및 최적화
**예상 시간**: 4~5시간 | [📖 상세 가이드](phases/phase-8-deploy.md)

- [x] 프라이버시 모드/폴더 제외 옵션
- [x] 핵심 제약/인덱스 추가
- [x] Docker 컨테이너화
- [x] API 속도 최적화 (캐싱/GZip)
- [x] Railway 배포 완료

### Phase 9: 패턴 분석 & 의사결정 추천 ✅
**완료일**: 2025-12-01 | [📖 상세 가이드](phases/phase-9-patterns.md)

- [x] PageRank, Community Detection, Orphan Detection
- [x] Task Prioritization, Missing Connections
- [x] API 엔드포인트 (`/patterns/analyze`, `/patterns/recommendations`)
- [x] Insights View UI

### Phase 10: 제품 개선 & 사용자 경험 강화
**시작일**: 2025-12-01 | [📖 상세 가이드](phases/phase-10-product.md)

- [x] PRD/UseCase/Process 문서 업데이트
- [ ] 온보딩 경험 (예정)
- [ ] Automation Recipes MVP (예정)
- [ ] Feedback Loop UI (예정)

### Phase 11: 의미론적 계층 클러스터링 MVP ✅
**완료일**: 2025-12-02 | [📖 상세 가이드](phases/phase-11-clustering.md)

- [x] GPT-5 Mini API 통합
- [x] UMAP + HDBSCAN 의미론적 클러스터링
- [x] 클러스터 메타데이터 (중요도, 인사이트, 샘플)
- [x] 캐싱 & 성능 최적화 (TTL 12h, 병렬 처리)
- [x] 계층적 탐색 UI (애니메이션, 상세 패널)
- [ ] 내부 테스트 (Day 12-13)
- [ ] 베타 준비 (Day 14)

### Phase 12: GraphRAG 검색 강화 ✅
**완료일**: 2025-12-02 | [📖 상세 가이드](phases/phase-12-graphrag.md)

- [x] VectorRetriever (`/search/vector`)
- [x] Text2CypherRetriever (`/search/text2cypher`)
- [x] VectorCypherRetriever (`/search/hybrid`)
- [x] 통합 검색 API (`POST /search`)

### Phase 13: SKOS 온톨로지 자동 생성 ✅
**완료일**: 2025-12-02 | [📖 상세 가이드](phases/phase-13-skos.md)

- [x] LLM 프롬프트 수정 (BROADER/NARROWER 계층 관계)
- [x] allowed_relationships 확장
- [x] SKOS 양방향성 보장 (`_ensure_skos_inverse()`)
- [x] 맥락 중심 추출 프롬프트

### Phase 14: ToolsRetriever 통합 ✅
**완료일**: 2025-12-02 | [📖 상세 가이드](phases/phase-14-agentic.md)

- [x] ToolsRetriever 구현 (semantic_search, structured_query, hybrid_search)
- [x] Agentic Search API (`/search/agentic`)
- [x] Fallback 메커니즘
- [x] 통합 검색 API 확장 (mode: "agentic")

### Phase 15: Thinking Insights & 2nd Brain 강화 ✅
**완료일**: 2025-12-03 | [📖 상세 가이드](phases/phase-15-insights.md)

#### 15.1 Thinking Insights API (Palantir Foundry 스타일)
- [x] Entity-Note Graph API (`/vault/entity-note-graph`)
- [x] Thinking Insights API (`/vault/thinking-insights`)
  - [x] Focus Areas (집중 영역)
  - [x] Bridge Concepts (연결 개념)
  - [x] Isolated Areas (고립 영역)
  - [x] Exploration Suggestions (탐구 제안)
- [x] Time-based Trends (시간 기반 트렌드)
  - [x] 최근 7일 vs 30일 토픽 비교
  - [x] Emerging/Growing/Declining/Stable 분류
- [x] Knowledge Health Score (지식 건강도)
  - [x] 연결 밀도 (connection_density)
  - [x] 고립 노트 비율 (isolation_ratio)
  - [x] 종합 점수 (overall score)
  - [x] 개선 추천 (recommendations)

#### 15.2 2nd Brain UI 개선
- [x] Insights 패널 기본 UI
- [x] 노트 직접 열기 - Focus Areas 클릭 시 관련 노트 열기
- [x] Entity-Note Graph 뷰 토글 - Clusters ↔ Note Links 전환
- [x] Insights 데이터 캐싱 (TTL 5분)
- [x] Exploration Suggestions 액션 버튼 - 연결 노트 자동 생성

---

## 향후 로드맵 (Post-MVP)

### Phase 16: PKM Core Ontology v2 (8 노드 확장) ✅
**완료일**: 2025-12-07

#### 16.1 Core 노드 확장 ✅
- [x] Goal 노드 추가 (최상위 목표, OKR의 O)
- [x] Concept 노드 추가 (구체적 개념, Topic의 하위)
- [x] Question 노드 추가 (연구 질문, 미해결 의문)
- [x] Insight 노드 추가 (발견, 결론, 통찰)
- [x] Resource 노드 추가 (외부 자료: 논문, 책, URL)

#### 16.2 Neo4j 스키마 업데이트 ✅
- [x] 8개 Core 타입 Unique Constraint 추가 (`neo4j.py`)
- [x] PKM_TYPES 정의 (`hybrid_graphiti_service.py`)

#### 16.3 LLM 추출 프롬프트 개선 ✅
- [x] `hybrid_graphiti_service.py` PKM_TYPES 8개로 확장
- [x] 8개 타입 분류 규칙 업데이트 (CLASSIFICATION_RULES)
- [x] 우선순위 기반 분류 로직 구현

#### 16.4 API 업데이트 ✅
- [x] entity-note-graph API 8개 타입 CASE문
- [x] thinking-insights API 8개 타입 CASE문
- [x] 타입별 분포 API 8개 타입 지원
- [x] 8개 타입 색상 정의 (type_colors)

#### 16.5 폴더 기반 필터링 ✅
- [x] folder_prefix 파라미터로 볼트 전체/폴더별 조회 지원
- [x] 연구/비즈니스/크리에이티브 폴더별 컨텍스트 분리

### 🎯 폴더 기반 Core 8 전략 (권장)

> **결론**: Research Pack, Solo Maker Pack은 Core 8으로 충분히 표현 가능.
> Obsidian 폴더 구조가 자연스러운 컨텍스트 분리 역할을 함.

#### 폴더별 Core 8 적용 예시

```
Obsidian Vault/
├── 1-Research/          → Core 8 (Question, Insight 중심)
│   └── 연구질문 = Question, 가설 = Concept, 결과 = Insight
├── 2-Business/          → Core 8 (Goal, Project, Task 중심)
│   └── 사업목표 = Goal, 제품기능 = Topic, 피드백 = Insight
├── 3-Creative/          → Core 8 (Topic, Concept 중심)
│   └── 콘텐츠아이디어 = Concept, 채널 = Resource
└── 4-Resources/         → Core 8 (Resource 중심)
    └── 논문/책/URL = Resource
```

#### Core 8 → Research/Maker 개념 매핑

| Research Pack 개념 | Core 8 표현 |
|-------------------|-------------|
| ResearchQuestion | Question |
| Hypothesis | Concept (가설적 개념) |
| Experiment | Project (실험 프로젝트) |
| Result | Insight (실험 결과/발견) |
| Paper | Resource (논문 자료) |

| Solo Maker Pack 개념 | Core 8 표현 |
|---------------------|-------------|
| Idea | Concept (아이디어) |
| Feature | Topic (기능 영역) |
| Feedback | Insight (사용자 발견) |
| Product | Project (제품 프로젝트) |
| Channel | Resource (배포 채널) |

---

### Phase 17: Research Pack (🔸 Optional - Deferred)
**상태**: Core 8으로 대부분 커버 가능, 사용자 피드백 기반 결정

> ⚠️ **결정**: 베타 사용자 피드백에서 명확한 니즈가 있을 때만 구현

#### 17.1 Research 노드 추가 (9개) - DEFERRED
- [ ] ResearchQuestion, Hypothesis, Experiment
- [ ] Dataset, Variable, Method
- [ ] Instrument, Result, Paper

#### 17.2 대안: folder_prefix 기반 연구 모드
- [x] 기존 folder_prefix 파라미터로 연구 폴더 필터링
- [ ] UI에서 "Research Mode" 토글 (연구 폴더만 표시)

### Phase 18: Solo Maker Pack (🔸 Optional - Deferred)
**상태**: Core 8으로 대부분 커버 가능, 사용자 피드백 기반 결정

> ⚠️ **결정**: 베타 사용자 피드백에서 명확한 니즈가 있을 때만 구현

#### 18.1 Maker 노드 추가 (8개) - DEFERRED
- [ ] Idea, Feature, ContentItem, Channel
- [ ] Metric, Feedback, Audience, Product

#### 18.2 대안: folder_prefix 기반 메이커 모드
- [x] 기존 folder_prefix 파라미터로 비즈니스 폴더 필터링
- [ ] UI에서 "Maker Mode" 토글 (비즈니스 폴더만 표시)

### Phase 19+: 추가 확장

| Phase | 기능 | 목표 |
|-------|------|------|
| **19** | PROV-O Activity | 아이디어 계보 추적 |
| **20** | Multi-Vault 지원 | 여러 Vault 간 지식 연결 |
| **21** | Collaborative KG | 팀 지식 그래프 공유 |
| **22** | AI Agent 통합 | 자율 리서치 에이전트 |

---

## 시작하기

```bash
cd docs
open phases/phase-0-setup.md
```
