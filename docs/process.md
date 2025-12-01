# 🚀 Didymos - 개발 프로세스 및 진행 상황

> "Smart Connections를 넘어선 구조화된 2nd Brain"
> Obsidian 플러그인 구독 모델 - MVP 2주 스프린트

**Last Updated**: 2025-12-02
**Status**: MVP Phase 11 - Day 11 완료 (의사결정 인사이트 강화), Day 12-13 테스트 진행 중

---

## 🎯 프로젝트 개요

### 제품 포지셔닝

| 기능 | Smart Connections | Didymos |
|------|-------------------|---------|
| **검색** | 유사 노트 찾기 | ✅ + 구조화된 맥락 |
| **구조** | 평면적 | ✅ 계층적 지식 그래프 |
| **분석** | 없음 | ✅ 의사결정 인사이트 |
| **LLM** | 임베딩만 | ✅ 클러스터 요약 |

### 타겟 사용자
1. **PhD/연구자**: 논문 리뷰, 문헌 정리
2. **PKM 파워유저**: 1000+ 노트, Zettelkasten 실천
3. **의사결정자**: 프로젝트 관리, 전략적 사고

### 시장 분석
- **PKM 시장**: $500M (2020) → $3B (2025)
- **Obsidian 사용자**: 1M+ (2024)
- **Smart Connections 구독자**: ~10K 추정
- **타겟 전환율**: 0.5-3% (연구자/파워유저)

---

## 💰 비즈니스 모델

### 요금제

| 티어 | 가격 | 기능 | 타겟 |
|------|------|------|------|
| **Free** | $0 | 100 노트, 주 1회 sync | 일반 사용자 |
| **Pro** | $7/월 | 무제한 노트, 실시간 sync | 파워유저 |
| **Research** | $15/월 | + 고급 분석, API | 연구자 |

### 수익 예측

**Year 1**: $10.2K/년 (100 Pro + 10 Research)
**Year 2**: $68K/년 (600 Pro + 100 Research)
**Year 3**: $300K/년 (2,500 Pro + 500 Research)

### 비용 구조 (사용자당/월)
- Neo4j Aura: ~$0.50
- Claude API: ~$1.50
- 인프라: ~$0.30
- **총**: ~$2.30/user/month
- **마진**: $4.70 (Pro), $12.70 (Research)

---

## 🏗️ 기술 아키텍처

### 스택
- **Backend**: FastAPI, LangChain, LangGraph
- **Database**: Neo4j AuraDB
- **AI**: Claude 3.5 Sonnet (클러스터 요약), OpenAI Embeddings (클러스터링)
- **Frontend**: Obsidian Plugin (TypeScript), vis-network
- **Clustering**: UMAP + HDBSCAN

### 데이터 흐름
```
Obsidian 노트 수정
  ↓
플러그인 자동 감지
  ↓
FastAPI /notes/sync
  ↓
LangChain LLMGraphTransformer
  ↓
Neo4j 저장 (Note, Topic, Project, Task)
  ↓
클러스터 캐시 무효화
  ↓
/graph/vault/clustered 호출
  ↓
UMAP + HDBSCAN 클러스터링
  ↓
Claude 클러스터 요약 생성
  ↓
vis-network 시각화
```

### Neo4j 독립성 전략

**Phase 1 (MVP)**: Neo4j Aura 무료 티어
**Phase 2 (1000명)**: 추상화 레이어 + NetworkX 옵션
**Phase 3 (5000명)**: 마이그레이션 또는 계속 사용 (비용 감당 가능)

---

## 📊 전체 진행 상황

### 현재 상태 (2025-12-02)
- ✅ Phase 0-9: 기본 MVP 완료 (93%)
- 🔄 **Phase 10: 비즈니스 모델 정립 & 재기획** (진행 중)
  - ✅ PRD v2.0 작성 (비즈니스 모델, MVP 범위)
  - ✅ 전략적 방향 확정 (Obsidian 플러그인 구독)
  - 🔄 문서 업데이트 중
- 🎯 **Phase 11: 의미론적 클러스터링 MVP** (2주 스프린트 진행 중)
  - 목표: 계층적 지식 그래프 시각화
  - 핵심: LLM 기반 클러스터 요약 + 의사결정 인사이트
  - 진행: Day 1-11 완료 (LLM 통합, 클러스터링, 메타데이터, UI 애니메이션, 인사이트), Day 12-13 테스트 진행 중

**기술 MVP 완성도**: 51/55 (93%)
**제품 시장 적합성**: 재정의 완료, 구현 시작 단계

---

## 📋 Phase별 상세 체크리스트

### Phase 0: 환경 설정
**예상 시간**: 1~2시간 | [📖 상세 가이드](./phases/phase-0-setup.md)

- [x] Python 3.11+, Node.js 18+ 설치 (Python 3.13, Node.js 20.19.6)
- [x] Neo4j AuraDB 생성 (AuraDB Professional - fece7c6e)
- [x] OpenAI API 키 발급
- [x] 프로젝트 디렉토리 구조 생성
- [x] Git 초기화 및 .gitignore 작성
- [x] 환경 변수 설정 (.env, .env.example)

### Phase 1: 백엔드 인프라 (LangChain 도입)
**예상 시간**: 2~3시간 | [📖 상세 가이드](./phases/phase-1-infra.md)

- [x] `requirements.txt` (langchain, langchain-neo4j, langgraph 포함)
- [x] Neo4j 연결 모듈 (`app/db/neo4j.py` - HTTP API 사용)
- [x] FastAPI 서버 실행 확인 (http://localhost:8000)

### Phase 2: 노트 동기화 파이프라인
**예상 시간**: 4~5시간 | [📖 Backend](./phases/phase-2-sync-backend.md) | [📖 Frontend](./phases/phase-2-sync-frontend.md)

#### Backend
- [x] `NotePayload / NoteSyncRequest` 스키마 정의
- [x] `upsert_note()` (User/Vault/Note MERGE)
- [x] `/notes/sync` FastAPI 엔드포인트 + Swagger 테스트

#### Frontend
- [x] Obsidian 플러그인 초기화 (TypeScript + esbuild)
- [x] Settings / API Client / Main Plugin 구현
- [x] 노트 저장 시 자동 동기화 및 알림

### Phase 3: AI 온톨로지 추출 (Text2Graph)
**예상 시간**: 2~3시간 | [📖 상세 가이드](./phases/phase-3-ai.md)

- [x] **LangChain `LLMGraphTransformer` 도입**
- [x] `allowed_nodes` (Topic, Project, Task, Person) 설정
- [x] `process_note_to_graph` 서비스 구현
- [x] Note 노드와 추출된 엔티티 연결 로직

### Phase 4: Context Panel (Hybrid Search)
**예상 시간**: 4~5시간 | [📖 Backend](./phases/phase-4-context-backend.md) | [📖 Frontend](./phases/phase-4-context-frontend.md)

- [x] **벡터 임베딩 생성 및 저장 (OpenAI Embeddings)**
- [x] 구조적(Graph) + 의미적(Vector) 하이브리드 추천 알고리즘 구현
- [x] Obsidian UI: Context View 구현 (Bolt 전환 후 UI 연동 완료)

**⚠️ 알려진 이슈**: AuraDB HTTP Query API의 벡터 검색 제약 → Bolt(SSC) 드라이버로 전환 완료.

### Phase 5: Graph Panel (Visualization)
**예상 시간**: 5~6시간 | [📖 Backend](./phases/phase-5-graph-backend.md) | [📖 Frontend](./phases/phase-5-graph-frontend.md)

- [x] Graph API: vis-network 포맷 노드/엣지 생성 (`/api/v1/notes/graph/{note_id}`)
- [x] Obsidian UI: `vis-network` 연동 (Graph Panel)
- [x] 노드 클릭/더블클릭 인터랙션 (하이라이트, 노트 열기)
- [x] 노드 필터/레이블 옵션 (토글)
- [x] 그래프 레이아웃/테마 튜닝 (Force/Hierarchical, 테마/간격 프리셋)
- [x] **Note/Vault 모드 전환** (개별 노트 vs 전체 Vault 그래프)
- [x] **🔄 Sync All Notes 버튼** (Vault 전체 온톨로지 일괄 추출)
- [x] **자동 업데이트**: 노트 수정 시 온톨로지 자동 재추출 (realtime/hourly 모드)
- [x] **Control Panel**: 13개 명령어 → 1개 통합 패널로 UX 개선
- [x] **Vault 우선 철학**: 기본 viewMode를 vault로 변경 (2nd brain 전사적 뷰)
- [x] **Auto-Hop 시스템**: 그래프 크기에 따라 자동 hop 조정 + 수동 오버라이드
- [x] **Topic 클러스터링 (1단계)**: Topic별로 연결된 노트들을 클러스터로 묶어 시각적 복잡도 25-50배 감소
- [x] **증분 동기화**: 마지막 sync 이후 수정된 파일만 재처리 (타임스탬프 기반)
- [x] **Progress 최적화**: Bulk sync 시 10개 단위로만 진행률 표시

### Phase 6: Task 관리
**예상 시간**: 3~4시간

- [x] Task 업데이트/조회 API (`/tasks/{id}`, `/tasks/list`)
- [x] Task 상태 관리 (todo/in_progress/done)
- [x] Obsidian UI: Task Panel 구현
- [x] Task와 Note 연결 관리 (MENTIONS 기반)

### Phase 7: Weekly Review
**예상 시간**: 3~4시간

- [x] 주간 리뷰 API (`/review/weekly`)
- [x] 새 토픽/잊힌 프로젝트/미완료 태스크/활성 노트 쿼리
- [x] Obsidian UI: Review Panel 구현
- [x] 리포트 저장 및 히스토리 관리

### Phase 8: 배포 및 최적화
**예상 시간**: 4~5시간

- [x] 프라이버시 모드/폴더 제외 옵션
- [x] 환경 변수 샘플 정리 (.env.example)
- [x] 핵심 제약/인덱스 추가 (Note/User/Vault/Topic/Project/Task)
- [x] Docker 컨테이너화 (FastAPI, Neo4j Aura 외부 사용)
- [x] API 속도 추가 최적화 (간단 캐싱/GZip)
- [ ] Obsidian 플러그인 릴리스 준비
- [x] 사용자 문서 작성 (Backend README, 플러그인 README 패키징)
- [x] 의사결정 지원: 온톨로지/리뷰 기반 Decision Note/Dashboard
- [ ] 프리미엄/요금제 UX (리얼타임/쿨다운 안내, 폴더별 배치 제한)
- [x] Render 배포 설정 파일 작성 (render.yaml)
- [x] Aura CLI 설정 완료 (credential 추가, 인스턴스 연결 확인)
- [x] Railway 배포 (prod) 완료, 도메인: https://didymos-backend-production.up.railway.app
- [ ] Render 프로젝트 생성 및 배포 (옵션, 필요 시)
- [ ] Fly.io 배포 플랜: 멀티 리전·프라이빗 네트워크 구성, 퍼시스턴트 볼륨/배포 스크립트 정리

### Phase 9: 패턴 분석 & 의사결정 추천
**예상 시간**: 6~8시간 | **완료일**: 2025-12-01

#### 백엔드 알고리즘
- [x] **PageRank 구현** (`pattern_service.py::calculate_pagerank`)
  - Google의 검색 알고리즘을 노트에 적용
  - 핵심 노트 자동 발견 (Top 10) - 사용자 용어로 표현

- [x] **Community Detection** (`pattern_service.py::detect_communities`)
  - DFS 기반 연결 요소 찾기
  - 지식 클러스터 자동 그룹화 (Top 5) - 사용자 용어로 표현

- [x] **Orphan Detection** (`pattern_service.py::find_orphan_notes`)
  - 고립된 노트 발견 (연결 없는 노트) - 사용자 용어로 표현

- [x] **Task Prioritization** (`recommendation_service.py::prioritize_tasks`)
  - 우선순위 = priority_weight + due_weight + connection_weight
  - Overdue, Due today, Due in Nd 자동 계산

- [x] **Missing Connections** (`recommendation_service.py::find_missing_connections`)
  - 같은 Topic 2개+ 공유하지만 연결 안 된 노트 쌍
  - "놓친 연결" 제안으로 표현

- [x] **API 엔드포인트**
  - `/patterns/analyze/{user_token}/{vault_id}` - 패턴 분석
  - `/patterns/recommendations/{user_token}/{vault_id}` - 의사결정 추천

#### 프론트엔드 UI
- [x] **Insights View** (`insightsView.ts`)
  - 🔍 Analyze Patterns 버튼
  - 💡 Get Recommendations 버튼

- [x] **패턴 분석 결과**
  - 📊 Overview (통계)
  - ⭐ Most Important Notes (핵심 노트 Top 10)
  - 🔗 Knowledge Clusters (지식 클러스터 Top 5)
  - 🏝️ Isolated Notes (고립된 노트)

- [x] **의사결정 추천**
  - 🎯 Priority Tasks (우선순위 Top 10)
  - 🔗 Suggested Connections (놓친 연결)

- [x] **명령 등록** (`main.ts`)
  - "Open Knowledge Insights" 명령 추가

#### 성과
- ✅ 자동 패턴 발견으로 사용자 인사이트 제공
- ✅ 과학적 알고리즘 (PageRank, Community Detection) 기반
- ✅ 의사결정 지원 (중요도 + 긴급도 + 연결성 고려)
- ✅ **UX 용어 매핑 적용**: 기술 용어 → 사용자 친화적 언어

---

### Phase 10: 제품 개선 & 사용자 경험 강화 (진행 중)
**예상 시간**: 8~10시간 | **시작일**: 2025-12-01

#### 문서화 개선
- [x] **PRD 업데이트**
  - 제품 포지셔닝 추가 ("Zettelkasten을 자동으로 해주는 두 번째 두뇌")
  - Core Loop 정의 (쓰기 → 제안 → 수락/거절 → 리뷰)
  - UX 용어 매핑 (Ontology → 자동 구조화된 지식)
  - Onboarding & 템플릿 섹션 추가
  - Insights Panel 행동 중심으로 강화
  - Offline/Degraded Mode 전략 추가
  - AI Feedback Loop 설계 추가
  - Automation Recipes 기능 명세 추가

- [x] **UseCase 업데이트**
  - 신규 사용자 온보딩 시나리오 추가 (템플릿 기반)
  - UX 용어 매핑 반영 (기술 용어 → 사용자 언어)
  - Automation Recipes 사용 사례 추가
  - Offline/Degraded Mode 사용 사례 추가

- [x] **Process 업데이트**
  - Phase 5 Graph Panel 기능 업데이트 (클러스터링, Control Panel)
  - Phase 10 추가 (현재 진행 중)
  - Phase 11 계층적 클러스터링 로드맵 추가

#### 프론트엔드 개선 (Phase 11 예정)
- [ ] **온보딩 경험**
  - 첫 실행 시 Welcome 화면
  - 템플릿 갤러리 UI
  - Quick Start 가이드

- [ ] **Automation Recipes MVP**
  - Meeting → Task 자동 추출
  - Auto-Linking 제안 UI
  - 설정 페이지에 자동화 토글 추가

- [ ] **Feedback Loop UI**
  - AI 제안에 Accept/Reject/Merge 버튼
  - Acceptance Rate 표시
  - 피드백 히스토리 패널

#### 백엔드 개선 (Phase 11 예정)
- [ ] **Feedback 노드 모델**
  - Neo4j Feedback 노드 스키마 추가
  - `/feedback/submit` API 엔드포인트
  - 피드백 기반 프롬프트 개선 로직

- [ ] **Automation Service**
  - Meeting → Task 추출 서비스
  - Auto-Linking 제안 알고리즘
  - Weekly Review 자동 생성 서비스

- [ ] **Offline Mode 지원**
  - 연결 실패 감지 및 fallback
  - 로컬 캐시 관리
  - 자동 재동기화 로직

#### 핵심 지표 (Phase 12 예정)
- [ ] **Acceptance Rate 추적**
  - 사용자별 수락률 측정
  - 개선 추이 대시보드
  - 목표: 60% → 85% (1개월) → 95% (6개월)

---

### Phase 11: 의미론적 계층 클러스터링 MVP (2주 스프린트)
**예상 시간**: 2주 (Day 1-14) | **목표**: 구독 가치 입증

#### 핵심 차별점 (Smart Connections vs Didymos)
```
Smart Connections:
- 유사 노트 검색 (평면적)
- 단순 임베딩 매칭

Didymos:
- ✅ 의미론적 계층 그래프
- ✅ LLM 기반 클러스터 요약
- ✅ 의사결정 인사이트
- ✅ 구조화된 2nd Brain
```

#### Week 1: LLM 통합 & 의미론적 클러스터링 (Day 1-7)
- [x] **Day 1-2: GPT-5 Mini API 통합** ✅ 2025-12-02 완료
  - LLM 클라이언트 설정 (`app/services/llm_client.py`)
  - 클러스터 요약 프롬프트 작성
  - `generate_llm_summaries()` 실제 구현
  - 모든 gpt-4o-mini → gpt-5-mini 마이그레이션
  - API 버그 수정 및 백엔드 테스트 완료

- [x] **Day 3-4: 의미론적 클러스터링 알고리즘** (2025-12-02 코드 반영)
  - 임베딩 기반 클러스터링 (UMAP + HDBSCAN) + 노이즈/샘플 부족 시 자동 폴백 (`umap_hdbscan_fallback:*`)
  - `compute_clusters_semantic()` 개선: 최소 샘플 가드, 클러스터 미생성 시 타입 기반 폴백
  - API `method` 파라미터 (`semantic`, `type_based`, `auto`) + 캐시 무시 옵션 반영
  - Obsidian Graph View: 클러스터링 방식/LLM 요약 토글 + Recompute 버튼 추가, 상태 표시바로 피드백 제공

- [x] **Day 5: 클러스터 메타데이터 & 관계 강화** ✅ 2025-12-02 완료
  - 클러스터 중요도 = mention 기반 + RECENCY 보너스 (최근 7일 업데이트 수)
  - 샘플 엔티티/노트, 자동 인사이트/Next Action 추가
  - 클러스터 간 공유 엔티티 기반 엣지 생성 (RELATED_TO, weight=공유 개수)
  - 캐시 TTL 12h, 최신 노트 업데이트보다 오래된 캐시는 자동 무효화
  - Obsidian Graph View: 클러스터 상세 패널(요약/인사이트/샘플/최근 업데이트/액션) + 샘플 노트 바로 열기 버튼 제공

- [x] **Day 5-6: 클러스터 메타데이터 강화** ✅ 2025-12-02 완료
  - 클러스터별 키 인사이트 추출 구현
  - 중요도 점수 계산 (mention_count + recency bonus)
  - 클러스터 간 관계 분석 (공유 노트 수 기반 엣지 생성)

- [x] **Day 7: 캐싱 & 성능 최적화** ✅ 2025-12-02 완료
  - 클러스터 캐시 TTL 12시간으로 최적화
  - 증분 업데이트 로직 (노트 변경 시 캐시 무효화)
  - LLM 병렬 처리 (ThreadPoolExecutor, 최대 3개 동시)
  - 백그라운드 캐시 워밍업 기능 추가 (warmup 파라미터)

#### Week 2: UI 개선 & 사용자 테스트 (Day 8-14)
- [x] **Day 8-9: 계층적 탐색 UI** ✅ 2025-12-02 완료
  - 클러스터 상세 패널 슬라이드 애니메이션 (slideInRight)
  - 인사이트/액션 hover 애니메이션 (translateX)
  - 샘플 노트 버튼 hover 효과 추가
  - 상태 바 hover 효과로 사용자 피드백 개선

- [x] **Day 10-11: 의사결정 인사이트 강화** ✅ 2025-12-02 완료
  - LLM 기반 "다음 행동 제안" (next_actions) 생성
  - 최근 7일간 업데이트 수 통계 표시
  - 클러스터별 샘플 노트 제공 (최대 5개)
  - 실행 가능한 인사이트 생성 프롬프트 개선

- [ ] **Day 12-13: 내부 테스트**
  - 본인 Vault (471개 노트)로 실전 테스트
  - 클러스터 품질 평가 (의미 있는 그룹화?)
  - UX 버그 수정
  - API 응답 시간 측정

- [ ] **Day 14: 베타 준비**
  - 데모 비디오 녹화 (1분)
  - README 업데이트 (스크린샷 포함)
  - Beta 키 시스템 설정

#### 성공 지표 (2주 후 평가)
1. **기술적 성공**
   - 471개 노트 → 8-12개 의미 클러스터로 축소
   - 클러스터 요약 생성 성공률 > 95%
   - API 응답 시간 < 2초

2. **사용자 가치**
   - "의미 있는 그룹화" 자가 평가 ≥ 8/10
   - LLM 인사이트가 실제로 유용함
   - Smart Connections 대비 우월성 체감

3. **비즈니스 준비**
   - 데모 가능한 상태
   - 구독 가치 명확히 설명 가능
   - 베타 런칭 준비 완료

---

## 🛠️ 기술 스택 (MVP Phase 11)

- **Backend**: FastAPI, **LangChain**, **LangGraph**
- **Database**: Neo4j AuraDB (무료 → Aura Professional 전환 예정)
- **AI**: **Claude 3.5 Sonnet** (클러스터 요약), OpenAI Embeddings (의미론적 클러스터링)
- **Frontend**: Obsidian API, TypeScript, **vis-network**
- **Clustering**: UMAP + HDBSCAN (의미론적 그룹화)
- **Business**: Freemium 구독 ($7 Pro, $15 Research/월)

---

## 🚀 시작하기

**첫 시작**:
```bash
cd docs
open phases/phase-0-setup.md
```
