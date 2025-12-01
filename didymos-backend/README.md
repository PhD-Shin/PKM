# Didymos Backend (FastAPI + Neo4j)

> **"Smart Connections를 넘어선 구조화된 2nd Brain"**
> Obsidian 플러그인을 위한 의미론적 클러스터링 백엔드

**Status**: MVP Phase 11 - Day 11 완료 (의사결정 인사이트 강화), Day 12-13 테스트 진행 중

---

## 개요

Didymos는 Obsidian 사용자를 위한 AI 기반 지식 그래프 백엔드입니다. Smart Connections와 달리, 단순히 유사 노트를 찾는 것이 아니라 **의미론적 계층 구조**를 제공하고, **GPT-5 Mini가 각 클러스터를 요약**하여 의사결정을 지원합니다.

### 핵심 차별점

| 기능 | Smart Connections | Didymos |
|------|-------------------|---------|
| **검색** | 유사 노트 검색 | ✅ + 구조화된 맥락 |
| **구조** | 평면적 | ✅ 계층적 클러스터 |
| **분석** | 없음 | ✅ 의사결정 인사이트 |
| **LLM** | 임베딩만 | ✅ Claude 클러스터 요약 |

---

## 준비사항

### 1. 필수 소프트웨어
- **Python**: 3.11+ (venv 사용 권장)
- **Neo4j AuraDB**: 무료 티어로 시작 가능
- **OpenAI API Key**: 임베딩 생성용
- **Anthropic API Key**: Claude 클러스터 요약용 (Phase 11)

### 2. 환경 변수 설정

`.env.example`를 복사하여 실제 값을 입력하세요:
```bash
cp .env.example .env
```

필수 값:
```bash
# Neo4j
NEO4J_URI=neo4j+s://<your-instance>.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password

# OpenAI (임베딩)
OPENAI_API_KEY=sk-...

# Anthropic (Phase 11: Claude 클러스터 요약)
ANTHROPIC_API_KEY=sk-ant-...

# FastAPI
APP_ENV=development
```

## 설치 & 실행

### 로컬 개발 환경

```bash
# 가상환경 생성
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# Phase 11: 의미론적 클러스터링 라이브러리 추가
pip install umap-learn hdbscan scikit-learn anthropic

# 서버 실행
uvicorn app.main:app --reload --port 8000
```

서버가 실행되면 다음 URL에서 접속 가능합니다:
- **API Docs (Swagger)**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Docker 실행

```bash
# 빌드
docker build -t didymos-api .

# 실행 (로컬 8000 포트 매핑)
docker run --env-file .env -p 8000:8000 didymos-api
```

#### docker-compose

```bash
docker-compose up --build -d
```

*참고: Neo4j AuraDB를 외부 서비스로 사용하므로 DB 컨테이너는 포함하지 않습니다.*

---

## 주요 기능

### Phase 0-10 (완료)
- ✅ **노트 동기화**: `/api/v1/notes/sync` (privacy_mode: full/summary/metadata)
- ✅ **AI 온톨로지 추출**: Topic, Project, Task 자동 추출
- ✅ **그래프 시각화**: `/api/v1/graph/note/{note_id}`
- ✅ **패턴 분석**: PageRank, Community Detection
- ✅ **주간 리뷰**: `/api/v1/review/weekly`

### Phase 11 (Week 1 완료, Week 2 진행 중)
- ✅ **의미론적 클러스터링**: UMAP + HDBSCAN 기반 (자동 폴백 지원)
- ✅ **GPT-5 Mini 클러스터 요약**: 각 클러스터의 핵심 인사이트 + 다음 행동 제안
- ✅ **계층적 지식 그래프**: 8-12개 클러스터로 471개 노트 구조화
- ✅ **성능 최적화**: 병렬 LLM 처리, 백그라운드 캐시 워밍업, 12시간 TTL
- ✅ **의사결정 지원**: 최근 업데이트 통계, 실행 가능한 인사이트

### 핵심 API 엔드포인트

#### 1. 노트 동기화
```bash
POST /api/v1/notes/sync
```

#### 2. 클러스터링 그래프 (Phase 11 핵심!)
```bash
GET /api/v1/graph/vault/clustered?vault_id=xxx&user_token=xxx&include_llm=true&method=semantic
```

**파라미터**:
- `vault_id`: Vault ID
- `user_token`: 사용자 토큰
- `include_llm`: LLM 요약 생성 여부 (default: false)
- `method`: 클러스터링 방법 (`semantic`, `type_based`, `auto`)
- `force_recompute`: 캐시 무시 강제 재계산 (default: false)
- `warmup`: 백그라운드 워밍업 모드 (default: false)

**응답 예시**:
```json
{
  "status": "success",
  "cluster_count": 8,
  "total_nodes": 471,
  "clusters": [
    {
      "id": "cluster_1",
      "name": "Research & Papers",
      "node_count": 145,
      "summary": "이 클러스터는 Raman scattering 관련 연구...",
      "key_insights": [
        "최근 7일간 15개 노트 업데이트",
        "HeII line 분석이 핵심 주제입니다",
        "대부분 관측 데이터 중심으로 활발한 작업 중입니다"
      ],
      "next_actions": [
        "RR Tel 관측 데이터를 하나의 프로젝트로 통합하세요",
        "HeII line 분석 결과를 문서화하고 다른 노트와 연결하세요"
      ],
      "importance_score": 8.5,
      "recent_updates": 15,
      "sample_entities": ["Raman scattering", "HeII line", "RR Tel"],
      "sample_notes": ["Observation Log 2024-11", "HeII Analysis", "Raman Data"]
    }
  ],
  "edges": [
    {
      "from": "cluster_1",
      "to": "cluster_2",
      "relation_type": "RELATED_TO",
      "weight": 12.0
    }
  ],
  "computation_method": "umap_hdbscan"
}
```

#### 3. 클러스터 캐시 무효화
```bash
POST /api/v1/graph/vault/clustered/invalidate
```

---

## 아키텍처

### 기술 스택
- **FastAPI**: 백엔드 프레임워크
- **Neo4j AuraDB**: 그래프 데이터베이스
- **LangChain**: AI 온톨로지 추출
- **GPT-5 Mini**: 클러스터 요약 및 인사이트 생성 (Phase 11)
- **OpenAI Embeddings**: 의미론적 클러스터링 (Phase 11)
- **UMAP + HDBSCAN**: 차원 축소 & 클러스터링 (Phase 11)
- **ThreadPoolExecutor**: 병렬 LLM 처리 (최대 3개 동시)

### 데이터 흐름
```
Obsidian 노트 수정
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
UMAP + HDBSCAN 클러스터링 (자동 폴백)
  ↓
GPT-5 Mini가 병렬로 각 클러스터 요약 생성
  ↓
응답 반환 (캐시 저장, TTL 12시간)
```

## 테스트용 샘플
- `test_note_sync.json`을 활용해 간단한 sync 호출을 할 수 있습니다:
```bash
curl -X POST -H "Content-Type: application/json" \
  -d @test_note_sync.json \
  http://localhost:8000/api/v1/notes/sync
```

## 기타
- 프라이버시 모드: summary(요약 후 처리), metadata(본문 제외) 지원
- 제외된 배포 작업(Docker 등)은 현재 스코프 밖입니다.
