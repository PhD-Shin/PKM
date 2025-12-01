# 💻 Didymos - Developer Guide

> 백엔드 & 프론트엔드 개발 가이드
> **제품 포지셔닝**: "Smart Connections를 넘어선 구조화된 2nd Brain"

**Last Updated**: 2025-12-02

---

## 1. 개발 환경 설정

### 1.1 필수 요구사항
- **Python**: 3.11+
- **Node.js**: 18+
- **Neo4j**: AuraDB (무료 티어)
- **Claude API Key**: Anthropic
- **OpenAI API Key**: Embeddings

### 1.2 프로젝트 구조
```text
PKM/
├─ didymos-backend/         # FastAPI 백엔드
│   ├─ app/
│   │   ├─ main.py
│   │   ├─ config.py
│   │   ├─ api/
│   │   │   ├─ routes_notes.py
│   │   │   ├─ routes_graph.py    # 클러스터링 API
│   │   │   └─ routes_review.py
│   │   ├─ services/
│   │   │   ├─ cluster_service.py # UMAP + HDBSCAN 클러스터링
│   │   │   ├─ llm_client.py      # Claude API (Phase 11 구현 예정)
│   │   │   └─ ontology.py
│   │   ├─ db/
│   │   │   ├─ neo4j_bolt.py      # Neo4j Bolt 드라이버
│   │   └─ schemas/
│   │       └─ cluster.py          # 클러스터 스키마
│   └─ requirements.txt
│
├─ didymos-obsidian/        # Obsidian 플러그인
│   ├─ src/
│   │   ├─ main.ts
│   │   ├─ settings.ts
│   │   ├─ api/
│   │   │   └─ client.ts           # API 클라이언트
│   │   └─ views/
│   │       ├─ graphView.ts        # 그래프 시각화 (vis-network)
│   │       └─ contextView.ts
│   └─ manifest.json
│
└─ docs/
    ├─ prd.md                       # 제품 요구사항 (v2.0)
    ├─ process.md                   # 개발 프로세스 (Phase 0-11)
    ├─ design.md                    # UI/UX 설계
    └─ usecase.md                   # 사용자 시나리오
```

---

## 2. 백엔드 개발 (FastAPI)

### 2.1 환경 변수 설정 (`.env`)

```bash
# Neo4j
NEO4J_URI=neo4j+s://xxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password

# OpenAI (임베딩)
OPENAI_API_KEY=sk-...

# Anthropic (Claude API for clustering)
ANTHROPIC_API_KEY=sk-ant-...

# FastAPI
APP_ENV=development
```

### 2.2 백엔드 실행

```bash
cd didymos-backend

# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# Phase 11: UMAP + HDBSCAN 추가
pip install umap-learn hdbscan scikit-learn anthropic

# 서버 실행
uvicorn app.main:app --reload --port 8000
```

### 2.3 핵심 API 엔드포인트

#### Phase 11 핵심: 클러스터링 API

**GET `/graph/vault/clustered`**
```python
# 의미론적 클러스터링 + LLM 요약
params = {
    "vault_id": "your-vault-id",
    "user_token": "your-token",
    "force_recompute": False,      # 캐시 무시
    "target_clusters": 10,          # 목표 클러스터 개수
    "include_llm": True,            # LLM 요약 포함
    "method": "semantic"            # semantic | type_based | auto
}

response = {
    "status": "success",
    "level": 1,
    "cluster_count": 8,
    "total_nodes": 471,
    "clusters": [
        {
            "id": "cluster_1",
            "name": "Research & Papers",
            "node_count": 145,
            "summary": "이 클러스터는 Raman scattering 관련 연구 논문들로 구성...", # Claude 생성
            "key_insights": [
                "최근 7일간 15개 노트 업데이트",
                "HeII line 분석이 핵심",
                "RR Tel 관측 데이터 추가 분석 필요"
            ],
            "importance_score": 8.5,
            "recent_updates": 15,
            "contains_types": {"topic": 80, "note": 65}
        },
        # ... 7개 더
    ],
    "edges": [
        {
            "from": "cluster_1",
            "to": "cluster_2",
            "relation_type": "RELATED_TO",
            "weight": 3.0
        }
    ],
    "last_computed": "2025-12-02T10:00:00",
    "computation_method": "umap_hdbscan"
}
```
- 캐시: TTL 12h, 최신 노트 업데이트보다 캐시가 오래되면 자동 재계산
- 메타데이터: recent_updates(7d), sample_entities/notes, note_ids 샘플, mention 기반 중요도 + recency 보너스

**POST `/graph/vault/clustered/invalidate`**
- 노트 업데이트 시 클러스터 캐시 무효화

---

## 3. 프론트엔드 개발 (Obsidian Plugin)

### 3.1 개발 환경 설정

```bash
cd didymos-obsidian

# 의존성 설치
npm install

# 개발 모드 (자동 빌드)
npm run dev

# 프로덕션 빌드
npm run build
```

### 3.2 Obsidian 플러그인 테스트

```bash
# 플러그인을 Obsidian Vault로 심볼릭 링크
ln -s $(pwd) /path/to/your/vault/.obsidian/plugins/didymos

# Obsidian 재시작 후 Settings > Community Plugins에서 Didymos 활성화
```

### 3.3 Graph View 클러스터링 (Phase 11)

**파일**: `didymos-obsidian/src/views/graphView.ts`

```typescript
// 클러스터링 데이터 가져오기
const clusteredData: ClusteredGraphData = await this.api.fetchClusteredGraph(
  this.settings.vaultId,
  { targetClusters: 10, includeLLM: true }
);

// 클러스터 노드 렌더링
const clusterNodes = clusteredData.clusters.map(cluster => ({
  id: cluster.id,
  label: `${cluster.name}\n(${cluster.node_count} nodes)`,
  shape: 'box',
  size: 30 + (cluster.importance_score * 5),
  color: { background: this.getClusterColor(cluster.contains_types) },
  cluster_data: cluster
}));

// vis-network에 추가
this.network.setData({ nodes: clusterNodes, edges: clusterEdges });

// 더블클릭으로 클러스터 펼치기
this.network.on('doubleClick', (params) => {
  if (params.nodes.length > 0) {
    const clusterId = params.nodes[0];
    this.expandCluster(clusterId);
  }
});
```

---

## 4. Phase 11 구현 체크리스트 (2주 스프린트)

### Week 1: 백엔드 - LLM 통합 & 의미론적 클러스터링

#### Day 1-2: Claude API 통합
- [ ] `app/services/llm_client.py` 작성
  ```python
  import anthropic

  class ClaudeClient:
      def __init__(self, api_key: str):
          self.client = anthropic.Anthropic(api_key=api_key)

      def generate_cluster_summary(self, cluster_data: dict) -> dict:
          prompt = f"""
          다음은 지식 그래프의 클러스터 정보입니다:
          - 클러스터 이름: {cluster_data['name']}
          - 포함된 노드 수: {cluster_data['node_count']}
          - 노드 타입: {cluster_data['contains_types']}

          이 클러스터의 핵심 주제를 2-3문장으로 요약하고,
          사용자가 주목해야 할 인사이트 3가지를 제시해주세요.
          """

          response = self.client.messages.create(
              model="claude-3-5-sonnet-20241022",
              max_tokens=500,
              messages=[{"role": "user", "content": prompt}]
          )

          return {
              "summary": response.content[0].text,
              "key_insights": self.parse_insights(response.content[0].text)
          }
  ```

- [ ] `cluster_service.py`의 `generate_llm_summaries()` 실제 구현
- [ ] 테스트: 3-5개 클러스터에 대해 요약 생성

#### Day 3-4: 의미론적 클러스터링
- [ ] UMAP + HDBSCAN 구현
  ```python
  import umap
  import hdbscan
  import numpy as np

  def compute_clusters_semantic(embeddings: np.ndarray, min_cluster_size=10):
      # Step 1: UMAP 차원 축소 (1536 → 5)
      reducer = umap.UMAP(
          n_components=5,
          n_neighbors=15,
          min_dist=0.1,
          metric='cosine'
      )
      reduced = reducer.fit_transform(embeddings)

      # Step 2: HDBSCAN 클러스터링
      clusterer = hdbscan.HDBSCAN(
          min_cluster_size=min_cluster_size,
          min_samples=3,
          cluster_selection_epsilon=0.5
      )
      labels = clusterer.fit_predict(reduced)

      return labels  # -1은 노이즈
  ```

- [ ] 타입별 그룹화 → 의미 기반 그룹화로 전환
- [ ] 테스트: 471개 노트 → 8-12개 클러스터

#### Day 5-6: 클러스터 메타데이터 강화
- [ ] 중요도 점수 계산
  ```python
  importance = (
      mention_count * 0.4 +
      recency_score * 0.3 +
      connection_density * 0.3
  )
  ```

- [ ] 최근 업데이트 통계 (7일 이내)
- [ ] 클러스터 간 관계 분석

#### Day 7: 성능 최적화
- [ ] 캐싱 TTL 조정 (24시간 → 7일)
- [ ] 증분 업데이트 로직
- [ ] API 응답 < 2초 보장

### Week 2: 프론트엔드 - UI 개선 & 테스트

#### Day 8-9: 계층적 탐색 UI
- [ ] 클러스터 펼치기/접기 구현
- [ ] 클러스터 상세 패널 (요약 + 인사이트)

#### Day 10-11: 의사결정 인사이트
- [ ] "주목해야 할 것" LLM 생성
- [ ] "최근 7일간 변화" 통계
- [ ] "다음 행동 제안"

#### Day 12-13: 내부 테스트
- [ ] 본인 Vault (471개 노트) 테스트
- [ ] 클러스터 품질 평가 (≥ 8/10)
- [ ] UX 버그 수정

#### Day 14: 베타 준비
- [ ] 데모 비디오 녹화 (1분)
- [ ] README 업데이트 (스크린샷)
- [ ] Beta 키 시스템 설정

---

## 5. 테스트 및 디버깅

### 5.1 백엔드 테스트

```bash
# 단위 테스트
pytest tests/

# API 테스트 (Swagger)
open http://localhost:8000/docs

# Claude API 테스트
curl -X GET "http://localhost:8000/graph/vault/clustered?vault_id=test&user_token=test&include_llm=true"
```

### 5.2 프론트엔드 테스트

- Obsidian Developer Console: `Ctrl+Shift+I` (Windows) / `Cmd+Option+I` (Mac)
- 에러 로그 확인: `console.log()` 사용

---

## 6. 배포

### 6.1 백엔드 배포 (Railway)

```bash
# Railway CLI 설치
npm install -g @railway/cli

# 로그인
railway login

# 배포
railway up
```

### 6.2 Obsidian 플러그인 배포

```bash
# 빌드
npm run build

# manifest.json 버전 업데이트
# main.js, manifest.json, styles.css를 GitHub Release에 업로드
```

---

## 7. 개발 팁

### 7.1 Neo4j 쿼리 디버깅

```cypher
// 클러스터 캐시 확인
MATCH (v:Vault {id: "your-vault"})-[:HAS_CLUSTER_CACHE]->(cache:ClusterCache)
RETURN cache.computed_at, cache.method

// 노트 임베딩 확인
MATCH (n:Note)
WHERE n.embedding IS NOT NULL
RETURN count(n) as notes_with_embeddings
```

### 7.2 Claude API 비용 모니터링

```python
import logging

logger.info(f"Claude API call: {response.usage.input_tokens} input, "
            f"{response.usage.output_tokens} output tokens, "
            f"cost: ${cost:.4f}")
```

### 7.3 성능 프로파일링

```python
import time

start = time.time()
result = compute_clusters_semantic(embeddings)
logger.info(f"Clustering took {time.time() - start:.2f}s")
```

---

## 8. 문제 해결 (Troubleshooting)

### 8.1 Claude API 429 Error
- Rate limiting 걸림
- 해결: 요청 간 1초 sleep 추가

### 8.2 클러스터링 품질 낮음
- UMAP/HDBSCAN 파라미터 튜닝
- `min_cluster_size`, `n_neighbors` 조정

### 8.3 API 응답 느림 (>5초)
- 캐싱 확인
- 임베딩 계산 병목 확인

---

**이 가이드는 Phase 11 MVP 개발을 위한 참고 자료입니다.**
**질문은 GitHub Issues에 남겨주세요!** 🚀
