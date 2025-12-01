# 🚀 Didymos - 개발 프로세스 및 진행 상황

> LangChain + LangGraph 기반 모던 아키텍처

---

## 📊 전체 진행 상황

### 현재 상태
- ✅ Phase 0: 환경 설정 (6/6)
- ✅ Phase 1: 백엔드 인프라 (LangChain) (3/3)
- ✅ Phase 2: 노트 동기화 (6/6)
- ✅ Phase 3: AI 온톨로지 (Text2Graph) (4/4)
- ✅ Phase 4: Context Panel (3/3) - Bolt 전환 완료, Obsidian Context UI 구현
- ✅ Phase 5: Graph Panel (5/5) - Vault 모드 + Sync All Notes 추가
- ✅ Phase 6: Task 관리 (4/4)
- ✅ Phase 7: Weekly Review (4/4)
- 🔄 Phase 8: 배포 (10/14) - Railway 프로덕션 배포 완료
- ✅ Phase 9: 패턴 분석 & 추천 (6/6) - PageRank, Community Detection, 의사결정 추천
- 🔄 **Phase 10: 제품 개선 & UX 강화 (2/13)** - PRD/UseCase 문서화 완료

**MVP 완성도**: 51/55 (93%)
**제품 완성도**: 53/68 (78%)

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

### Phase 11: 계층적 지식 그래프 (향후 계획)
**예상 시간**: 6~8시간 | **목표**: Palantir Foundry 스타일 계층적 온톨로지

#### 현재 상태 (2025-12-01)
- ✅ **1단계 클러스터링**: Topic별로 연결된 노트들을 클러스터로 묶기
  - 500개 노트 → ~10-20개 Topic 클러스터로 축소
  - 25-50배 시각적 복잡도 감소
  - 더블클릭으로 클러스터 펼치기/접기

#### 향후 개선 방향 (사용자 피드백 후 결정)
- [ ] **2-3단계 계층 구조** (Palantir 방식)
  ```
  Level 1: Knowledge Domain (5-10개 큰 덩어리)
    └─ Level 2: Topic Cluster (주제별 묶음)
        └─ Level 3: Individual Notes (세부 노트들)
  ```

- [ ] **백엔드 계층 정보 제공**
  - Domain/Topic/Note 명시적 구분
  - API에서 hierarchy level 메타데이터 추가

- [ ] **프론트엔드 다단계 클러스터링**
  - Project → Topic → Note 자동 그룹화
  - 1번 클릭: Domain 펼치기 → Topics 표시
  - 2번 클릭: Topic 펼치기 → Notes 표시
  - Zoom/Pan 네비게이션

#### 결정 기준
**1주일 실사용 후 평가 항목**:
1. 현재 1단계 클러스터링으로 충분한가?
2. 500개 노트 환경에서 탐색이 불편한가?
3. 추가 계층이 실제로 도움이 되는가?

**판단 기준**:
- 불편함 없음 → 현재 유지
- 탐색 어려움 → 2-3단계 계층 구현
- Premature optimization 회피 원칙

---

## 🛠️ 기술 스택 (Updated)

- **Backend**: FastAPI, **LangChain**, **LangGraph**
- **Database**: Neo4j AuraDB
- **AI**: GPT-5 mini / GPT-4o-mini
- **Frontend**: Obsidian API, TypeScript, **vis-network**

---

## 🚀 시작하기

**첫 시작**:
```bash
cd docs
open phases/phase-0-setup.md
```
