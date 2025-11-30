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
- ✅ Phase 5: Graph Panel (5/5)
- ✅ Phase 6: Task 관리 (4/4)
- ✅ Phase 7: Weekly Review (4/4)
- ⬜ Phase 8: 배포 (7/11)

**전체 진행률**: 42/46 (91%)

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
- [ ] Render 배포 (MVP): 컨테이너 실행, Neo4j Aura Free(TLS) 연동, US West 리전, 환경변수/헬스체크 적용
- [ ] Fly.io 배포 플랜: 멀티 리전·프라이빗 네트워크 구성, 퍼시스턴트 볼륨/배포 스크립트 정리

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
