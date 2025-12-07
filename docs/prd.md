# 📘 Didymos - PRD (Product Requirement Document)

> AI-Powered 2nd Brain for Obsidian - 시간 인식 지식 그래프 + GraphRAG 검색 엔진

**최종 업데이트**: 2025-12-07
**현재 단계**: Phase 16 완료 (PKM Core Ontology v2 - 8개 타입)
**비즈니스 모델**: Obsidian 플러그인 구독 ($7-15/월)
**핵심 기술**: Graphiti (저장/추출) + neo4j-graphrag (검색/질의)

---

## 🎯 Executive Summary

### 제품 비전
**"Smart Connections를 넘어선 구조화된 2nd Brain"**

Didymos는 Obsidian 사용자에게 단순한 유사도 검색을 넘어 **의미론적 계층 구조**와 **AI 인사이트**를 제공하는 지식 관리 시스템입니다.

### 핵심 차별점

| 기능 | Smart Connections | InfraNodus | Didymos |
|------|-------------------|------------|---------|
| **검색** | 유사 노트 찾기 | 단어 빈도 기반 | ✅ GraphRAG 하이브리드 |
| **그래프 단위** | 노트 | **단어** (co-occurrence) | ✅ **개념** (ontology) |
| **관계 추출** | 없음 | 동시 출현만 | ✅ Subject-Relation-Object |
| **의미 구조** | 평면적 | 단어 네트워크 | ✅ SKOS 계층 구조 |
| **시간 추적** | 없음 | 없음 | ✅ Bi-temporal |
| **가격** | 무료 | $9/월 | $7-15/월 |

### 왜 "단어 기반 그래프"가 아닌 "개념 기반 온톨로지"인가?

**InfraNodus의 구조적 한계**:

InfraNodus는 **단어 단위 Co-occurrence 그래프**를 사용합니다:
1. 문장을 토큰으로 분리
2. 같은 문장에 등장한 단어를 연결
3. Betweenness centrality로 중심 단어 찾기

이 방식은 빠르지만 **치명적인 정보 손실**이 있습니다:

```
❌ 문제 1: 의미는 관계에서 발생
   "학생이 교사를 평가했다" vs "교사가 학생을 평가했다"
   → 단어는 동일, 의미는 완전히 다름
   → InfraNodus는 동일한 그래프를 그림

❌ 문제 2: Co-occurrence는 노이즈가 큼
   "커피를 마시며 논문을 쓰다가 비가 와서 집에 갔다"
   → 커피-논문-비-집 모두 연결됨
   → 의미적 관계가 아닌 우연한 동시 출현

❌ 문제 3: 핵심 개념 식별 불가
   "모델", "연구", "것" 같은 빈약한 단어가 높은 중심성
   → 실제 핵심 개념(AI, Raman Scattering) 파악 어려움
```

**Didymos의 개념 기반 접근**:

```
✅ 개념 추출 (Concept Extraction)
   단어가 아닌 의미 있는 개념 목록 추출
   예: "Digital Twin", "Ontology Schema", "Raman Scattering"

✅ 관계 추출 (Relation Extraction)
   Subject-Relation-Object 트리플로 저장
   예: (Digital Twin)-[USES]->(Ontology Schema)

✅ SKOS 온톨로지 자동 생성
   BROADER/NARROWER/RELATED 계층 구조
   예: (Machine Learning)-[BROADER]->(AI)

✅ 지식 구조화
   단어 그래프가 아닌 진짜 지식 그래프
   연구자/지식노동자를 위한 의미 있는 구조
```

**결론**: 단어 연결성은 "언어의 껍데기", 개념 연결성이 "지식의 구조"

### 시장 기회

- **PKM 시장**: $500M (2020) → $3B (2025 예상)
- **Obsidian 사용자**: 1M+ (빠르게 성장)
- **타겟**: 연구자, 개발자, PKM 실천가
- **목표**: 2년차 500명 유료 사용자 ($5.7K/월 = $68K/년)

---

## 1. 비즈니스 모델

### 1.1 요금제 구조

#### 🆓 Free Tier
```
✅ 노트 싱크 (월 100회)
✅ 기본 그래프 시각화
✅ 엔티티 추출
❌ 클러스터링
❌ AI 인사이트
❌ 고급 분석
```

#### 💎 Pro - $7/월 ($70/년)
```
✅ 모든 Free 기능
✅ 스마트 클러스터링
✅ AI 요약 (월 100회)
✅ 주간 리뷰 자동화
✅ 우선 지원
✅ 무제한 노트 싱크
```

#### 🔬 Research - $15/월 ($150/년)
```
✅ 모든 Pro 기능
✅ 무제한 AI 쿼리
✅ 커스텀 분석
✅ API 접근
✅ 팀 공유 (5명)
✅ 우선 처리 큐
```

### 1.2 수익 시뮬레이션

**Year 1 (보수적)**
- 무료: 5,000명
- Pro (3%): 150명 × $7 = $1,050/월
- Research (0.5%): 25명 × $15 = $375/월
- **총**: $17K/년

**Year 2 (현실적)**
- 무료: 20,000명
- Pro (3%): 600명 × $7 = $4,200/월
- Research (0.5%): 100명 × $15 = $1,500/월
- **총**: $68K/년

**Year 3 (낙관적)**
- 무료: 50,000명
- Pro (4%): 2,000명 × $7 = $14,000/월
- Research (1%): 500명 × $15 = $7,500/월
- **총**: $258K/년

### 1.3 비용 구조

**사용자당 비용**:
- Neo4j: $0.50/월 (shared infrastructure)
- LLM API: $1.50/월 (caching + batching)
- 인프라: $0.30/월
- **총**: $2.30/월

**마진**:
- Pro: $7 - $2.30 = $4.70 (67%)
- Research: $15 - $2.30 = $12.70 (85%)

---

## 2. 제품 핵심 가치

### 2.1 문제 정의

| 문제 | 현재 솔루션 (Smart Connections) | Didymos 솔루션 |
|------|-------------------------------|---------------|
| 노트가 쌓이지만 정리 안 됨 | 유사 노트 추천만 | **자동 계층 구조 생성** |
| 큰 그림을 못 봄 | 개별 노트만 볼 수 있음 | **지식 클러스터 시각화** |
| 의사결정 지원 없음 | 검색만 가능 | **AI 인사이트 & 추천** |
| 지식 진화 추적 불가 | 정적 스냅샷 | **시간대별 변화 분석** |

### 2.2 타겟 사용자

**Primary**:
1. **연구자/대학원생** (40%)
   - 논문 작성, 문헌 관리
   - 실험 노트 구조화
   - 가격: $15/월도 OK

2. **개발자/기획자** (35%)
   - 프로젝트 관리
   - 회의록 → Task 자동화
   - 가격: $7/월 선호

3. **PKM 파워유저** (25%)
   - Zettelkasten, PARA 실천
   - 고급 기능 필요
   - 가격: $15/월 지불 의향 높음

---

## 3. MVP 기능 범위 (2주 Sprint) - ✅ 완료

### 3.1 핵심 기능 (Must Have) - ✅ 구현 완료

#### ✅ Temporal Knowledge Graph (Graphiti 기반)

**핵심 원리**: Zep AI의 [Graphiti](https://github.com/getzep/graphiti) 프레임워크를 활용한 **시간 인식 지식 그래프**

```python
# Graphiti Bi-Temporal Model
# 모든 엣지에 4개의 시간 필드 추적
edge_properties = {
    "valid_at": "2024-01-15",      # 관계가 실제로 시작된 시점
    "invalid_at": None,            # 관계가 종료된 시점 (None = 현재 유효)
    "created_at": "2024-12-02",    # 시스템에 기록된 시점
    "expired_at": None,            # 시스템에서 만료된 시점
}

# Episode 기반 처리
# 노트 수정 → Episode 생성 → 자동 엔티티 추출 + 시간 정보 기록
await graphiti.add_episode(
    name=f"note_update_{note_id}",
    episode_body=note_content,
    source_description="Obsidian note",
    reference_time=note.updated_at,  # 노트 수정 시간
)
```

**왜 Graphiti인가?**
- **시간 지식 그래프**: 지식의 변화를 추적 ("작년에는 A였지만 지금은 B")
- **자동 엔티티 해결**: 중복 엔티티 자동 병합 + 요약 생성
- **하이브리드 검색**: 시맨틱 + BM25 + 그래프 순회 (300ms P95 지연)
- **DMR 벤치마크 94.8%**: MemGPT(93.4%) 대비 우수한 성능
- **영감**: [Zep Temporal KG Paper (arXiv 2501.13956)](https://arxiv.org/abs/2501.13956)

```
# Graphiti 데이터 흐름
Obsidian 노트 수정
  ↓
Episode 생성 (reference_time = 노트 수정 시간)
  ↓
Graphiti 자동 처리:
├── Entity 추출 + 요약 생성
├── Relation 추출 (RELATED_TO, PART_OF)
├── 기존 Entity와 병합/업데이트
└── Bi-temporal 시간 정보 기록
  ↓
Neo4j 저장 (valid_at, invalid_at, created_at, expired_at)
  ↓
시간 기반 쿼리 가능 ("2024년 1월에 내가 관심 있었던 주제는?")
```

#### ✅ 의미론적 클러스터링
```
현재 상태:
- 471 notes → 보이지 않음

MVP 후:
- 471 notes → 3-10 클러스터
- 임베딩 기반 유사도
- LLM 요약 포함
```
- 알고리즘: UMAP + HDBSCAN (샘플 부족/노이즈 시 `umap_hdbscan_fallback:*`로 타입 기반 폴백)
- API: `/graph/vault/clustered?method=semantic|type_based|auto&include_llm=true&force_recompute=true` (캐시 무시 옵션 포함)
- 메타데이터: mention 기반 중요도 + 최근 7일 업데이트 보너스, 샘플 엔티티/노트, 자동 인사이트/Next Action
- 관계: 클러스터 간 공유 엔티티 기반 RELATED_TO 엣지(weight=공유 개수)
- 캐시: TTL 12h, 최신 노트 업데이트보다 오래된 캐시는 자동 무효화
- UI: Obsidian Graph View에서 Semantic/Type 전환, LLM Summary 토글, Recompute 버튼, 상태바 + 클러스터 상세 패널(요약/인사이트/샘플/최근 업데이트/액션) + 샘플 노트 열기 버튼

#### ✅ LLM 통합 (실제 구현)
```python
# cluster_service.py
def generate_llm_summaries(clusters):
    for cluster in clusters:
        prompt = f"""
        이 클러스터의 노트들을 분석해주세요:
        {cluster.notes[:5]}

        1. 공통 주제는?
        2. 최근 변화는?
        3. 다음 액션은?
        """
        cluster.summary = claude.messages.create(prompt)
        cluster.key_insights = extract_insights(cluster.summary)
```

#### ✅ Obsidian 플러그인 UI
```
Control Panel:
├── Dashboard (현재 상태 요약)
├── Graph View (클러스터 시각화)
│   ├── Vault Mode (전체 그래프)
│   └── Note Mode (현재 노트)
├── Context Panel (관련 정보)
├── Task Manager (자동 추출 Task)
└── Weekly Review
```

#### ✅ 잊혀진 지식 리마인더 (Spaced Repetition)
```
30일 이상 미접근 지식 자동 발견 → 리마인더 표시 → 확인 시 last_accessed 갱신

API:
- GET /temporal/insights/stale?days=30&limit=20
- POST /temporal/insights/mark-reviewed
- POST /temporal/insights/mark-reviewed-batch

UI:
- "💡 Forgotten" 버튼 (Graph View)
- 30일 / 60일 필터 탭
- 개별/일괄 확인 기능
```

### 3.2 Phase 12: GraphRAG 검색 강화 (neo4j-graphrag 통합)

**목표**: Graphiti 저장 + neo4j-graphrag 검색 병용으로 "내 2nd brain에게 묻는 챗봇" 구현

#### 아키텍처
```
[Obsidian] → [Graphiti] → [Neo4j] ← [neo4j-graphrag Retrievers] → [LLM 답변]
            (저장/추출)              (검색/질의)
```

- **Graphiti 역할**: 노트 저장, 엔티티 추출, 시간 관리, 자동 요약
- **neo4j-graphrag 역할**: 검색 레이어 (Vector, Cypher, Hybrid)

#### neo4j-graphrag Retriever 전략

| Retriever | 용도 | 예시 질의 |
|-----------|------|----------|
| `VectorRetriever` | 의미 검색 | "온톨로지 관련 아이디어 보여줘" |
| `VectorCypherRetriever` | 그래프+벡터 복합 | "온톨로지와 연결된 프로젝트/사람 한 번에" |
| `Text2CypherRetriever` | 조건 필터 | "2024년 3월 이후 연구 노트만" |
| `ToolsRetriever` | LLM 자동 선택 | 위 3개를 상황에 맞게 자동 선택 |

```python
# neo4j-graphrag 검색 레이어 (예정)
from neo4j_graphrag.retrievers import (
    VectorRetriever, VectorCypherRetriever,
    Text2CypherRetriever, ToolsRetriever
)

tools = [
    vector_retriever.convert_to_tool(name="semantic_note_search"),
    vector_cypher_retriever.convert_to_tool(name="graph_context_search"),
    text2cypher_retriever.convert_to_tool(name="structured_graph_query"),
]

tools_retriever = ToolsRetriever(tools=tools, llm=OpenAILLM())
# → 사용자는 자연어로 질문, LLM이 적절한 검색 전략 자동 선택
```

### 3.3 Phase 13: SKOS 온톨로지 자동 생성 (MVP 핵심)

> ⚠️ **MVP 필수**: BROADER/NARROWER 계층 구조 없이는 InfraNodus의 "단어 그래프"와 차별화 불가

**목표**: 개념 간 계층 관계 자동 추출 → 진정한 온톨로지 구현

```
InfraNodus: 단어 동시출현 → 평면적 네트워크
Didymos without SKOS: 개념 추출 → 여전히 평면적
Didymos with SKOS: 개념 + 계층 구조 → 진정한 온톨로지 ✅
```

**구현 계획**:
- LLM 프롬프트로 BROADER/NARROWER/RELATED 관계 추출
- 예: "Machine Learning" → BROADER → "AI"
- 클러스터링 시 계층 구조 활용
- Graph View에 상위/하위 개념 시각화

### 3.4 Phase 14: ToolsRetriever 통합 (MVP 핵심) ✅

> ✅ **완료**: 자연어 질의 → 자동 검색 전략 선택이 "내 2nd brain에게 묻기"의 핵심 UX

**목표**: 사용자가 자연어로 질문하면 LLM이 적절한 검색 도구 자동 선택

```
현재: 사용자가 수동으로 검색 방법 선택
목표: "최근 AI 관련 프로젝트 알려줘" → LLM이 자동으로 적절한 검색 조합
```

**구현 완료**:
- ToolsRetriever 설정 (Vector + Cypher + Temporal 조합)
- 자연어 질의 UI (Chat 형태 또는 Command Palette)
- LLM이 질의 분석 → 적절한 Retriever 자동 선택

### 3.5 Phase 15: Thinking Insights & 2nd Brain 강화 (진행 중)

> 🚧 **진행 중**: Palantir Foundry 스타일의 지식 분석 인사이트 제공

**목표**: 지식 그래프에서 실행 가능한 인사이트 도출 + 2nd Brain 뷰 개선

#### 3.5.1 Thinking Insights API (Palantir Foundry 스타일)

```
기존: 클러스터만 시각화
목표: 집중 영역, 연결 개념, 고립 영역, 탐구 제안 + 시간 트렌드 + 건강도 점수
```

**완료된 기능**:
- ✅ Entity-Note Graph API (`/vault/entity-note-graph`)
  - 노트 간 연결성을 공유 엔티티 기반으로 시각화
  - vis-network 포맷 (nodes[], edges[])

- ✅ Thinking Insights API (`/vault/thinking-insights`)
  - **Focus Areas**: 가장 많이 언급된 집중 영역
  - **Bridge Concepts**: 여러 영역을 연결하는 핵심 개념
  - **Isolated Areas**: 연결이 부족한 고립 영역
  - **Exploration Suggestions**: AI 기반 탐구 제안

**구현 예정**:
- [ ] **Time-based Trends** (시간 기반 트렌드)
  ```json
  {
    "time_trends": {
      "recent_topics": ["AI Ethics", "RAG"],      // 최근 7일
      "declining_topics": ["Web3", "NFT"],        // 30일 전 대비 감소
      "emerging_topics": ["LLM Fine-tuning"],     // 새로 등장
      "trend_period": "7d vs 30d"
    }
  }
  ```

- [ ] **Knowledge Health Score** (지식 건강도)
  ```json
  {
    "health_score": {
      "overall": 78,
      "connection_density": 0.65,    // 연결 밀도 (0~1)
      "isolation_ratio": 0.12,       // 고립 노트 비율 (낮을수록 좋음)
      "completeness_score": 0.82,    // 완성도 (태그/링크 충실도)
      "recommendations": [
        "고립 노트 15개를 연결하세요",
        "Research 클러스터에 더 집중하세요"
      ]
    }
  }
  ```

#### 3.5.2 2nd Brain UI 개선

| 기능 | 상태 | 설명 |
|------|------|------|
| Insights 패널 | ✅ 완료 | Focus Areas, Bridge Concepts 표시 |
| 노트 직접 열기 | 📋 예정 | 클릭 시 Obsidian에서 노트 열기 |
| Entity-Note Graph 토글 | 📋 예정 | Clusters ↔ Entity-Note 뷰 전환 |
| Insights 캐싱 | 📋 예정 | TTL 5분, 반응성 개선 |
| 탐구 제안 액션 | 📋 예정 | "이 영역 연결하기" 버튼 |

**UI 구현 계획**:
```typescript
// 노트 직접 열기
onFocusAreaClick(area: FocusArea) {
  const notePath = area.sample_notes[0];
  this.app.workspace.openLinkText(notePath, '');
}

// Entity-Note Graph 토글
toggleGraphMode() {
  this.graphMode = this.graphMode === 'clusters' ? 'entity-note' : 'clusters';
  this.loadGraph();
}

// Insights 캐싱
private insightsCache: { data: ThinkingInsights; timestamp: number } | null;
private INSIGHTS_CACHE_TTL = 5 * 60 * 1000; // 5분
```

### 3.6 Phase 16: PKM Core Ontology v2 (8 노드 확장)

> 🚀 **다음 단계**: 현재 4개 타입(Topic, Project, Task, Person)에서 8개 Core 타입으로 확장

#### 3.6.1 Core Ontology v2 노드 정의

| 노드 타입 | 설명 | 주요 속성 | 예시 |
|-----------|------|----------|------|
| **Goal** | 최상위 목표 (OKR의 O) | name, description, deadline, status | "PhD 논문 완성", "창업 준비" |
| **Project** | Goal을 달성하기 위한 중간 단위 | name, status, deadline, goal_id | "Chapter 3 작성", "MVP 개발" |
| **Task** | 실행 가능한 최소 단위 | title, status, priority, due_date | "서론 작성", "API 구현" |
| **Topic** | 주제/개념 카테고리 | name, summary, importance_score | "Machine Learning", "PKM" |
| **Concept** | 구체적 개념/용어 | name, definition, skos_broader | "Transformer", "Zettelkasten" |
| **Question** | 연구 질문 또는 미해결 의문 | text, status, priority | "RAG가 hallucination을 줄이나?" |
| **Insight** | 발견/통찰/결론 | text, evidence_notes[], confidence | "HDBSCAN이 K-means보다 효과적" |
| **Resource** | 외부 자료 참조 | name, type, url, doi | 논문, 책, 웹페이지 |

#### 3.6.2 Core Ontology v2 관계 정의

```cypher
// Goal-Project-Task 계층
(:Goal)-[:REALIZED_BY]->(:Project)
(:Project)-[:HAS_TASK]->(:Task)

// Topic-Concept 의미 구조 (SKOS)
(:Topic)-[:HAS_CONCEPT]->(:Concept)
(:Concept)-[:BROADER]->(:Concept)
(:Concept)-[:NARROWER]->(:Concept)
(:Concept)-[:RELATED]->(:Concept)

// Question-Insight 지식 순환
(:Topic)-[:HAS_QUESTION]->(:Question)
(:Question)-[:ADDRESSED_BY]->(:Insight)
(:Note)-[:RAISES_QUESTION]->(:Question)
(:Note)-[:EVIDENCES_INSIGHT]->(:Insight)

// Resource 참조
(:Note)-[:REFERS_TO_RESOURCE]->(:Resource)
(:Insight)-[:SUPPORTED_BY]->(:Resource)
```

#### 3.6.3 LLM 추출 프롬프트 (Core v2)

```python
CORE_V2_EXTRACTION_PROMPT = """
당신은 PKM(Personal Knowledge Management) 전문가입니다.
아래 노트에서 8가지 엔티티 타입과 관계를 추출하세요.

## 엔티티 타입
1. Goal: 장기 목표 (OKR의 O, 예: "PhD 완성")
2. Project: 중간 단위 프로젝트 (예: "Chapter 3 작성")
3. Task: 실행 가능한 작업 (예: "서론 초안 작성")
4. Topic: 주제 카테고리 (예: "Machine Learning")
5. Concept: 구체적 개념 (예: "Transformer Architecture")
6. Question: 연구 질문 (예: "RAG가 hallucination을 줄이나?")
7. Insight: 발견/결론 (예: "HDBSCAN이 K-means보다 효과적")
8. Resource: 외부 자료 (예: "Attention Is All You Need 논문")

## 관계 타입
- REALIZED_BY: Goal→Project
- HAS_TASK: Project→Task
- HAS_CONCEPT: Topic→Concept
- BROADER/NARROWER: Concept 계층
- HAS_QUESTION: Topic→Question
- ADDRESSED_BY: Question→Insight
- RAISES_QUESTION: Note→Question
- EVIDENCES_INSIGHT: Note→Insight
- REFERS_TO_RESOURCE: Note→Resource

## 노트 내용
{note_content}

## 출력 (JSON)
{
  "entities": [
    {"name": "...", "type": "Goal|Project|Task|Topic|Concept|Question|Insight|Resource", "properties": {...}}
  ],
  "relationships": [
    {"source": "...", "target": "...", "type": "REALIZED_BY|HAS_TASK|...", "properties": {...}}
  ]
}
"""
```

### 3.7 🎯 폴더 기반 Core 8 전략 (권장)

> **결론**: Research Pack, Solo Maker Pack은 Core 8으로 충분히 표현 가능.
> Obsidian 폴더 구조가 자연스러운 컨텍스트 분리 역할을 함.

#### 폴더별 Core 8 적용

```
Obsidian Vault/
├── 1-Research/          → Core 8 (Question, Insight 중심)
├── 2-Business/          → Core 8 (Goal, Project, Task 중심)
├── 3-Creative/          → Core 8 (Topic, Concept 중심)
└── 4-Resources/         → Core 8 (Resource 중심)
```

#### Core 8 → Research/Maker 매핑

| Research 개념 | Core 8 | Maker 개념 | Core 8 |
|--------------|--------|-----------|--------|
| ResearchQuestion | Question | Idea | Concept |
| Hypothesis | Concept | Feature | Topic |
| Experiment | Project | Feedback | Insight |
| Result | Insight | Product | Project |
| Paper | Resource | Channel | Resource |

### 3.8 Phase 17: Research Pack (🔸 Optional - Deferred)

> ⚠️ **상태**: Core 8으로 대부분 커버 가능, 베타 피드백 기반 결정

<details>
<summary>📚 Research Pack 상세 (클릭하여 펼치기)</summary>

| 노드 타입 | 설명 | Core 8 대안 |
|-----------|------|------------|
| **ResearchQuestion** | 핵심 연구 질문 | Question |
| **Hypothesis** | 검증 가능한 가설 | Concept |
| **Experiment** | 실험/연구 설계 | Project |
| **Result** | 실험 결과 | Insight |
| **Paper** | 논문 | Resource |

</details>

### 3.10 Phase 18: Solo Maker Pack (🔸 Optional - Deferred)

> ⚠️ **상태**: Core 8으로 대부분 커버 가능, 베타 피드백 기반 결정

<details>
<summary>🚀 Solo Maker Pack 상세 (클릭하여 펼치기)</summary>

| 노드 타입 | 설명 | Core 8 대안 |
|-----------|------|------------|
| **Idea** | 초기 아이디어 | Concept |
| **Feature** | 기능 명세 | Topic |
| **Feedback** | 사용자 피드백 | Insight |
| **Product** | 제품/서비스 | Project |
| **Channel** | 배포 채널 | Resource |

</details>

### 3.11 🔄 Sync 전략 (현재 및 향후 개선)

#### 현재 방식: Reset & Resync (전체)

개발 및 초기 베타 단계에서 사용하는 단순한 동기화 방식:

```
현재 동작:
1. "Reset & Resync" 버튼 클릭
2. 해당 vault의 모든 엔티티 삭제 (DELETE FROM Entity WHERE vault_id = ...)
3. 전체 노트에서 엔티티 재추출 (Sync All)

Settings 구조:
settings.lastBulkSyncTime: number  // 전체 vault 기준 하나의 타임스탬프
```

**장점**: 구현 단순, 데이터 정합성 보장, 디버깅 용이
**단점**: 전체 재처리로 시간/비용 소모, 대형 vault에서 비효율적

#### 향후 개선: 폴더 기반 증분 Sync (Deferred)

> 🔸 **상태**: 베타 이후 구현 예정. 대형 vault 사용자 피드백 기반으로 우선순위 결정.

**개선 방향**:

1. **폴더별 Sync**: 특정 폴더만 reset/resync
2. **증분 Sync**: 변경된 노트만 재처리 (`mtime > folderSyncTime`)
3. **선택적 Reset**: 폴더별 엔티티 삭제 및 재추출

```typescript
// 향후 Settings 구조
interface DidymosSettings {
  // 현재
  lastBulkSyncTime: number;  // 전체 vault 기준

  // 개선 후
  folderSyncTimes: {
    [folderPath: string]: number;  // 폴더별 sync 타임스탬프
  };
  // 예시:
  // folderSyncTimes: {
  //   "1_프로젝트/": 1733567890123,
  //   "2_영역/": 1733567890456,
  //   "3_자료/": 1733567890789,
  // }
}
```

**향후 UI 개선**:
```
Sync Settings:
├── [Dropdown] 폴더 선택 (전체 / 1_프로젝트 / 2_영역 / ...)
├── [Button] Sync Selected Folder
├── [Button] Reset & Resync Selected Folder
└── [Status] 폴더별 마지막 sync 시간 표시
```

**구현 시 고려사항**:
- 폴더 간 엔티티 참조 관계 처리 (cross-folder references)
- 폴더 삭제/이름 변경 시 기존 sync 정보 마이그레이션
- 폴더 깊이 설정 (상위 폴더만 vs 모든 하위 폴더)

### 3.12 Phase 19+: 향후 로드맵

| Phase | 기능 | 설명 |
|-------|------|------|
| **19** | PROV-O Activity | 아이디어 계보 추적 (Reading → Summarizing → Brainstorming) |
| **20** | 팀 공유 기능 | 멀티 사용자 지원, Collaborative KG |
| **21** | AI Agent 통합 | 자율 리서치 에이전트 |
| **22** | 폴더 기반 증분 Sync | 변경된 노트만 재처리, 폴더별 sync 관리 |

---

## 4. 기술 아키텍처

### 4.1 시스템 구조 (Graphiti + neo4j-graphrag 병용)

```
┌─────────────────────┐
│  Obsidian Plugin    │ TypeScript
│  (Frontend)         │
└──────────┬──────────┘
           │ REST API (HTTPS)
           │
┌──────────▼──────────────────────────────────────┐
│  FastAPI Server (Python 3.11)                   │
│  ┌────────────────┐  ┌────────────────────────┐ │
│  │ Graphiti       │  │ neo4j-graphrag         │ │
│  │ (저장/추출)     │  │ (검색/질의)            │ │
│  │ - Episode 처리  │  │ - VectorRetriever     │ │
│  │ - Entity 해결   │  │ - Text2CypherRetriever│ │
│  │ - 시간 관리     │  │ - ToolsRetriever      │ │
│  └───────┬────────┘  └───────────┬────────────┘ │
│          │                       │              │
│          └───────────┬───────────┘              │
└──────────────────────┼──────────────────────────┘
                       │
          ┌────────────┼────────────┐
          │            │            │
     ┌────▼────┐  ┌────▼────┐  ┌───▼──────┐
     │ Neo4j   │  │ OpenAI  │  │ Claude   │
     │ AuraDB  │  │ (임베딩) │  │ (요약)   │
     └─────────┘  └─────────┘  └──────────┘
```

**레이어 역할 분담**:
| 레이어 | 라이브러리 | 역할 |
|--------|-----------|------|
| **저장** | Graphiti | Episode → Entity 추출, Bi-temporal 관계, 자동 요약 |
| **검색** | neo4j-graphrag | Vector/Cypher/Hybrid 검색, LLM 기반 툴 선택 |
| **DB** | Neo4j | 그래프 저장소, 벡터 인덱스 |
| **LLM** | OpenAI + Claude | 임베딩, 클러스터 요약, 검색 전략 선택 |

### 4.2 데이터 모델 (PKM 온톨로지 v1 + Graphiti Temporal)

**온톨로지 설계 기반**:
- [SKOS](https://www.w3.org/TR/skos-reference/) - 개념/주제 계층 구조 (BROADER, NARROWER, RELATED)
- [FOAF](https://en.wikipedia.org/wiki/FOAF) - 사람/관계 표현
- [PROV-O](https://www.w3.org/TR/prov-o/) - 지식 출처/과정 추적

```cypher
// ==========================================
// 핵심 노드 (PKM Ontology v1)
// ==========================================

// 기본 노드
(:User {id, created_at})
(:Vault {id, name})
(:Note {note_id, title, path, content_hash, updated_at, last_accessed})

// Concept (SKOS 기반) - 주제/키워드/태그
(:Concept {
  id, name,
  summary,              // Graphiti 자동 생성 요약
  importance_score,
  created_at,
  last_accessed         // 잊혀진 지식 리마인더용
})

// Person (FOAF 기반) - 사람/저자/협력자
(:Person {
  id, name,
  summary,
  created_at
})

// Source (출처) - 책/논문/URL/영상
(:Source {
  id, name, type,       // type: book, paper, url, video
  url, doi,
  created_at
})

// Project/Task (생산성)
(:Project {id, name, status, summary, created_at})
(:Task {id, title, status, priority, due_date, summary, created_at})

// Cluster (의미론적 그룹)
(:Cluster {id, name, level, summary, key_insights[]})

// Activity (PROV-O 기반, Phase 16 예정) - 아이디어 생성 과정
// (:Activity {id, type, timestamp})  // type: Reading, Summarizing, Brainstorming

// ==========================================
// 관계 (Bi-Temporal + SKOS/FOAF/PROV-O)
// ==========================================

// Graphiti Bi-Temporal 엣지 속성 (모든 관계에 적용)
// valid_at: 관계가 실제로 시작된 시점 (사용자 관점)
// invalid_at: 관계가 종료된 시점 (NULL = 현재 유효)
// created_at: 시스템에 기록된 시점
// expired_at: 시스템에서 만료된 시점

// 기본 관계
(:User)-[:OWNS]->(:Vault)
(:Vault)-[:HAS_NOTE]->(:Note)

// Note → Entity 관계
(:Note)-[:MENTIONS {valid_at, invalid_at, fact}]->(:Concept)
(:Note)-[:AUTHORED_BY {valid_at, invalid_at}]->(:Person)
(:Note)-[:DERIVED_FROM {valid_at, invalid_at}]->(:Source)
(:Note)-[:PART_OF {valid_at, invalid_at}]->(:Project)
(:Note)-[:CONTAINS {valid_at, invalid_at}]->(:Task)
(:Note)-[:LINKED_TO]->(:Note)  // Obsidian [[wikilink]]

// SKOS 계층 관계 (Concept 간)
(:Concept)-[:BROADER]->(:Concept)   // 상위 개념 (예: Machine Learning → AI)
(:Concept)-[:NARROWER]->(:Concept)  // 하위 개념 (예: AI → Machine Learning)
(:Concept)-[:RELATED]->(:Concept)   // 연관 개념 (예: AI ↔ Data Science)

// FOAF 관계 (Person 간)
(:Person)-[:KNOWS]->(:Person)
(:Person)-[:INTERESTED_IN]->(:Concept)
(:Person)-[:INFLUENCED]->(:Note)

// PROV-O 관계 (Phase 16 예정)
// (:Activity)-[:USED]->(:Source|:Note)
// (:Activity)-[:GENERATED]->(:Note)
// (:Activity)-[:ASSOCIATED_WITH]->(:Person)

// 클러스터 관계
(:Cluster)-[:CONTAINS]->(:Note|:Concept)
(:Cluster)-[:SUB_CLUSTER]->(:Cluster)
(:Cluster)-[:RELATED_TO {weight}]->(:Cluster)  // 공유 엔티티 수 기반
```

**시간 쿼리 예시**:
```cypher
// 2024년 1월에 관심 있었던 주제들
MATCH (n:Note)-[m:MENTIONS]->(t:Topic)
WHERE m.valid_at <= date('2024-01-31')
  AND (m.invalid_at IS NULL OR m.invalid_at >= date('2024-01-01'))
RETURN t.name, count(n) as mentions
ORDER BY mentions DESC

// 최근 한 달간 변화된 관계
MATCH (e1)-[r]->(e2)
WHERE r.created_at >= datetime() - duration('P30D')
RETURN type(r), e1.name, e2.name, r.fact
```

### 4.3 Neo4j 독립성 전략

**현재 (MVP)**: Neo4j Aura 사용
- 빠른 개발
- 무료 티어 활용
- 비용: 사용자당 $0.50/월

**Phase 2 (1000명 후)**: 옵션 추가
```python
# abstraction layer
class GraphBackend:
    @staticmethod
    def create(backend_type):
        if backend_type == "neo4j":
            return Neo4jEngine()
        elif backend_type == "local":
            return NetworkXEngine()  # SQLite + NetworkX
```

**Phase 3 (수익 안정 후)**: 완전 독립
- 자체 그래프 엔진
- Neo4j는 premium 옵션

---

## 5. MVP 개발 계획 (2주)

### Week 1: 기능 완성

**Day 1-2: LLM 통합** ✅
```python
# app/services/llm_client.py
class ClaudeLLMClient:
    def summarize_cluster(self, notes):
        # 실제 Claude API 호출
        # 요약 + 인사이트 생성
```

**Day 3-4: 의미론적 클러스터링** ✅
```python
# app/services/cluster_service.py
def compute_clusters_semantic(vault_id):
    # 1. 임베딩 가져오기
    # 2. UMAP 차원 축소
    # 3. HDBSCAN 클러스터링
    # 4. 실패/노이즈 시 타입 기반 클러스터링으로 폴백
```
- API: `/graph/vault/clustered?method=semantic|type_based|auto&include_llm=true&force_recompute=true`
- UI: Graph View에서 Semantic/Type 토글, LLM Summary 토글, Recompute 버튼/상태바 추가

**Day 5-7: 버그 수정 & 테스트**
- 엣지 케이스 처리
- 성능 최적화
- 사용자 경험 다듬기

### Week 2: 베타 런칭

**Day 8-9: 문서화**
- README 업데이트
- 사용 가이드 작성
- 1분 데모 영상

**Day 10-11: 배포 준비**
- Railway 설정 확인
- 모니터링 구축
- 베타 키 시스템

**Day 12-14: 커뮤니티 런칭**
- Reddit r/ObsidianMD 포스트
- Discord 공지
- 첫 10명 베타 테스터 모집

---

## 6. 성공 지표

### 6.1 MVP 검증 (2주 후)

✅ **진행 신호**:
- 5명 이상 "돈 낼게요" 코멘트
- 10명 이상 적극 사용
- 구체적 피드백 많음

⚠️ **피봇 신호**:
- 특정 기능 불만 집중
- "이것만 있으면" 코멘트
→ 해당 기능 우선 구현

❌ **중단 신호**:
- 3명 미만 관심
- 조회수 < 100
→ 다른 아이디어 찾기

### 6.2 비즈니스 지표

**3개월 후**:
- 50명 유료 사용자
- $350/월 수익
- Churn < 10%

**6개월 후**:
- 200명 유료 사용자
- $1,400/월 수익
- NPS > 40

**1년 후**:
- 500명 유료 사용자
- $3,500/월 수익
- 유료 전환율 > 3%

---

## 7. 마케팅 전략

### 7.1 런칭 계획

**Week 1-2 (베타)**:
- Reddit AMA
- Discord 공지
- Twitter 스레드

**Month 1 (Early Access)**:
- YouTube 튜토리얼
- 블로그 포스트 (SEO)
- PKM 인플루언서 협업

**Month 2-3 (Public Launch)**:
- Product Hunt 런칭
- Obsidian 포럼 핀
- 할인 프로모션

### 7.2 메시지

**헤드라인**:
> "Smart Connections를 넘어선 구조화된 2nd Brain"

**피치**:
```
Obsidian 노트가 많아질수록 정리는 어려워집니다.

Didymos는:
✅ 자동으로 지식을 구조화하고
✅ AI가 놓친 연결을 찾아주며
✅ 의사결정을 지원하는 인사이트를 제공합니다.

Smart Connections: "비슷한 노트 찾기"
Didymos: "지식의 큰 그림 보기"

첫 달 무료, 14일 환불 보장
```

---

## 8. 리스크 & 대응

| 리스크 | 확률 | 대응책 |
|--------|------|--------|
| 시장 반응 없음 | 40% | 2주 안에 검증, 빠른 피봇 |
| Neo4j 비용 증가 | 10% | NetworkX 마이그레이션 준비 |
| 경쟁자 등장 | 30% | First mover + 커뮤니티 구축 |
| LLM API 비용 폭발 | 15% | 캐싱 + 배칭 최적화 |

---

## 9. API 명세

### 9.1 핵심 엔드포인트

```
# 노트 동기화
POST   /notes/sync
       노트 동기화 및 Graphiti Episode 처리

# 그래프 시각화
GET    /graph/vault/clustered?vault_id={id}&user_token={token}
       클러스터링된 Vault 그래프
       Response: {clusters[], edges[], summary}

POST   /graph/vault/clustered/invalidate
       클러스터 캐시 무효화

GET    /notes/context/{note_id}
       노트 컨텍스트 (관련 topics, projects, tasks)

# 주간 리뷰
GET    /review/weekly?vault_id={id}
       주간 리뷰 데이터
```

### 9.2 Temporal Knowledge Graph API (✅ 구현 완료)

```
# Graphiti 상태 확인
GET    /temporal/status
       Response: {graphiti_enabled, connection, neo4j_uri}

# 시간 인식 검색
POST   /temporal/search
       Body: {query, start_date?, end_date?, num_results}
       Graphiti 하이브리드 검색 (시맨틱 + BM25 + 그래프 순회)

# 엔티티 시간 변화 추적
GET    /temporal/evolution/{entity_name}?start_date=&end_date=
       "2024년 1월에 관심 있었던 주제" 같은 쿼리 지원

# 잊혀진 지식 리마인더
GET    /temporal/insights/stale?days=30&limit=20
       N일 이상 미접근 지식 조회

POST   /temporal/insights/mark-reviewed
       Body: {uuid}
       지식 확인 완료 → last_accessed 갱신

POST   /temporal/insights/mark-reviewed-batch
       Body: [uuid1, uuid2, ...]
       일괄 확인 완료

# 최근 변화
GET    /temporal/insights/recent?days=7
       최근 N일간 추가/변경된 엔티티/관계
```

### 9.3 Thinking Insights API (✅ 구현 완료)

```
# Entity-Note Graph (노트 연결성 시각화)
GET    /vault/entity-note-graph?vault_id={id}&user_token={token}&min_connections=1
       Response: {
         nodes: [{id, label, title, group, path?}],
         edges: [{from, to, label, title}]
       }

# Thinking Insights (Palantir Foundry 스타일 분석)
GET    /vault/thinking-insights?vault_id={id}&user_token={token}
       Response: {
         focus_areas: [{name, mention_count, sample_notes[], description}],
         bridge_concepts: [{name, connected_areas[], bridge_strength}],
         isolated_areas: [{name, note_count, suggestion}],
         exploration_suggestions: [{title, description, related_concepts[], action_type}],
         time_trends: {...},        // 예정
         health_score: {...}        // 예정
       }
```

**응답 형식 예시**:
```json
{
  "focus_areas": [
    {
      "name": "Machine Learning",
      "mention_count": 45,
      "sample_notes": ["ML-basics.md", "Neural-Networks.md"],
      "description": "기계학습 관련 핵심 연구 영역"
    }
  ],
  "bridge_concepts": [
    {
      "name": "Data Pipeline",
      "connected_areas": ["Machine Learning", "Data Engineering"],
      "bridge_strength": 8.5
    }
  ],
  "isolated_areas": [
    {
      "name": "Quantum Computing",
      "note_count": 3,
      "suggestion": "Machine Learning 영역과 연결 가능성 탐색"
    }
  ],
  "exploration_suggestions": [
    {
      "title": "AI Ethics와 ML 연결",
      "description": "두 영역 간 공통점 탐구",
      "related_concepts": ["AI Ethics", "Machine Learning"],
      "action_type": "connect_areas"
    }
  ]
}
```

### 9.4 클러스터 API 응답 형식

```json
{
  "status": "success",
  "level": 1,
  "cluster_count": 8,
  "total_nodes": 471,
  "clusters": [
    {
      "id": "cluster_1",
      "name": "Research Methodology",
      "node_count": 67,
      "summary": "Mixed-methods research approaches with focus on qualitative coding...",
      "key_insights": [
        "3주간 15개 노트 추가 (활발)",
        "Qualitative coding 집중 중",
        "실제 실험 진행 0개 → 액션 필요"
      ],
      "importance_score": 8.5,
      "last_updated": "2024-12-01T10:00:00Z",
      "contains_types": {
        "topic": 12,
        "note": 55
      }
    }
  ],
  "edges": [],
  "last_computed": "2024-12-01T15:30:00Z",
  "computation_method": "semantic_embedding"
}
```

---

## 10. 프라이버시 & 보안

### 10.1 데이터 처리

```
사용자 노트 → 로컬에서 YAML 추출 → API 전송 → Neo4j 저장
           └→ LLM API (Claude) → 즉시 폐기
```

### 10.2 프라이버시 모드

| 모드 | 전송 데이터 | 정확도 |
|------|------------|--------|
| 🔵 Full | 전체 본문 | 최고 (95%) |
| 🟡 Summary | 요약만 | 중간 (80%) |
| 🔴 Metadata | 제목/태그만 | 낮음 (60%) |

### 10.3 보안

- HTTPS 강제
- JWT 인증
- Vault별 데이터 격리
- 토큰 암호화 저장
- GDPR 준수 (삭제 요청 처리)

---

## 11. 배포 전략

### 11.1 Backend (FastAPI)

**Platform**: Railway
- Docker 자동 빌드
- 환경변수: `NEO4J_URI`, `CLAUDE_API_KEY`, `STRIPE_SECRET_KEY`
- Health check: `/health`
- Auto-scaling: 2-4 instances

### 11.2 Frontend (Obsidian Plugin)

**Distribution**:
1. Community Plugins (승인 후)
2. BRAT (베타 기간)
3. GitHub Releases

**Update 전략**:
- Semantic versioning
- 자동 업데이트 체크
- 변경사항 알림

---

## 12. 다음 단계 (Post-MVP)

### Phase 2 (Month 2-3)
- 계층적 드릴다운 (조건부)
- 시간대별 분석
- 커스텀 쿼리 API

### Phase 3 (Month 4-6)
- 팀 공유 기능
- 모바일 앱
- Zapier 통합

### Phase 4 (Year 2)
- 자체 그래프 엔진
- 오픈 소스 코어
- 엔터프라이즈 플랜

---

## 부록 A: 경쟁 분석

| 제품 | 장점 | 단점 | 가격 |
|------|------|------|------|
| **Smart Connections** | 무료, 빠름 | 구조 없음 | Free |
| **Copilot** | 무료, 로컬 | 기본 기능만 | Free |
| **Mem.ai** | AI 네이티브 | 락인, 비쌈 | $15/월 |
| **Reflect** | 깔끔, 빠름 | 비쌈 | $10/월 |
| **Didymos** | 구조 + AI | 유료 | $7-15/월 |

---

## 부록 B: LLM 프롬프트 템플릿

```python
CLUSTER_SUMMARY_PROMPT = """
다음은 사용자의 지식 그래프에서 발견된 클러스터입니다.

클러스터 이름: {cluster_name}
포함 노트 수: {node_count}
노트 샘플:
{note_samples}

다음 질문에 답해주세요:
1. 이 클러스터의 공통 주제는 무엇인가?
2. 최근 3주간 어떤 변화가 있었나?
3. 사용자가 고민하는 핵심 질문은?
4. 다음에 취해야 할 구체적 액션 3가지는?

응답 형식:
SUMMARY: [2-3문장 요약]
INSIGHTS:
- [인사이트 1]
- [인사이트 2]
- [인사이트 3]
"""
```

---

**문서 버전**: 4.0
**최종 검토**: 2025-12-03
**주요 변경**:
- Graphiti + neo4j-graphrag 병용 아키텍처 추가
- PKM 온톨로지 v1 (SKOS/FOAF/PROV-O 기반) 설계
- 잊혀진 지식 리마인더 기능 추가
- Phase 12-14 완료 (GraphRAG, SKOS, ToolsRetriever)
- Phase 15: Thinking Insights & 2nd Brain 강화 추가
  - Entity-Note Graph API
  - Thinking Insights API (Focus Areas, Bridge Concepts, Exploration Suggestions)
  - Time-based Trends & Knowledge Health Score (예정)
  - UI 개선: 노트 직접 열기, Graph 뷰 토글, 캐싱, 액션 버튼
**다음 리뷰**: Phase 15 완료 후
