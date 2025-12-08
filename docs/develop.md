# Didymos - 개발자 가이드

> 백엔드 & 프론트엔드 개발 가이드

**최종 수정**: 2025-12-08

---

## 1. 개발 환경

### 1.1 요구사항

- **Python**: 3.11+
- **Node.js**: 18+
- **Neo4j**: AuraDB (무료 티어)
- **API Keys**: OpenAI, Anthropic (선택)

### 1.2 프로젝트 구조

```
PKM/
├── didymos-backend/              # FastAPI 백엔드
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/
│   │   │   ├── routes_notes.py       # 노트 동기화
│   │   │   ├── routes_graph.py       # Vault Graph + Clusters
│   │   │   ├── routes_temporal.py    # 시간 인사이트
│   │   │   └── routes_search.py      # GraphRAG 검색
│   │   ├── services/
│   │   │   ├── hybrid_graphiti_service.py   # PKM Type 분류
│   │   │   ├── entity_cluster_service.py    # 시맨틱 엣지 추론
│   │   │   ├── graphiti_service.py          # 코어 Graphiti
│   │   │   ├── cluster_service.py           # UMAP + HDBSCAN
│   │   │   └── llm_client.py                # Claude API
│   │   ├── db/
│   │   │   ├── neo4j.py              # HTTP API 클라이언트
│   │   │   └── neo4j_bolt.py         # Bolt 드라이버
│   │   └── schemas/
│   │       └── cluster.py
│   └── requirements.txt
│
├── didymos-obsidian/             # Obsidian 플러그인
│   ├── src/
│   │   ├── main.ts
│   │   ├── settings.ts
│   │   ├── api/client.ts
│   │   └── views/
│   │       ├── graphView.ts      # Vault Graph (8 클러스터)
│   │       └── contextView.ts
│   └── manifest.json
│
└── docs/
    ├── prd.md                    # 제품 요구사항
    ├── process.md                # 아키텍처 & 프로세스
    ├── develop.md                # 이 파일
    └── design.md                 # UI/UX 디자인
```

---

## 2. 백엔드 개발 (FastAPI)

### 2.1 환경 변수 (.env)

```bash
# Neo4j
NEO4J_URI=neo4j+s://xxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password

# OpenAI (임베딩 + GPT-5-Mini)
OPENAI_API_KEY=sk-...

# Anthropic (요약용 Claude)
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

# 서버 실행
uvicorn app.main:app --reload --port 8000
```

### 2.3 주요 API 엔드포인트

#### Entity Clusters API (메인)

**GET `/vault/entity-clusters`**

시맨틱 엣지가 포함된 8 PKM Type 클러스터를 반환합니다.

```python
params = {
    "vault_id": "your-vault-id",
    "user_token": "your-token",
    "folder_prefix": "1-Research/"  # 선택적 필터
}

response = {
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
        # ... 7개 더 PKM Types
    ],
    "edges": [
        {
            "from": "uuid1",
            "to": "uuid2",
            "semantic_type": "ACHIEVED_BY",
            "semantic_label": "달성 수단"
        }
    ],
    "semantic_edge_stats": {
        "total": 605,
        "unique_types": 15
    }
}
```

#### Thinking Insights API

**GET `/vault/thinking-insights`**

집중 영역, 브릿지 개념, 고립 영역을 반환합니다.

```python
response = {
    "focus_areas": [
        {"name": "Machine Learning", "mention_count": 45}
    ],
    "bridge_concepts": [...],
    "isolated_areas": [...],
    "health_score": {"overall": 78}
}
```

---

## 3. 프론트엔드 개발 (Obsidian 플러그인)

### 3.1 개발 환경 설정

```bash
cd didymos-obsidian

# 의존성 설치
npm install

# 개발 모드 (자동 리빌드)
npm run dev

# 프로덕션 빌드
npm run build
```

### 3.2 Obsidian에서 테스트

```bash
# 플러그인을 Obsidian 볼트에 심링크
ln -s $(pwd) /path/to/your/vault/.obsidian/plugins/didymos-pkm

# Obsidian 재시작 후 플러그인 활성화
```

### 3.3 Graph View 구현

**파일**: `src/views/graphView.ts`

```typescript
// 8 PKM 클러스터 가져오기
const clusterData = await this.api.fetchEntityClusters(
    this.settings.vaultId,
    { folderPrefix: this.folderFilter }
);

// 클러스터 노드 렌더링
const clusterNodes = clusterData.clusters.map(cluster => ({
    id: cluster.id,
    label: `${cluster.label}\n(${cluster.count})`,
    shape: 'box',
    color: { background: cluster.color }
}));

// 시맨틱 엣지 렌더링
const edges = clusterData.edges.map(edge => ({
    from: edge.from,
    to: edge.to,
    label: edge.semantic_label,
    title: edge.semantic_description
}));

// vis-network 업데이트
this.network.setData({ nodes: clusterNodes, edges });
```

---

## 4. 핵심 서비스

### 4.1 PKM Type 분류

**파일**: `app/services/hybrid_graphiti_service.py`

```python
PKM_TYPES = ["Goal", "Project", "Task", "Topic", "Concept", "Question", "Insight", "Resource"]

# 규칙 기반 분류 (빠름)
CLASSIFICATION_RULES = {
    "Goal": [lambda name: "goal" in name.lower()],
    "Question": [lambda name: name.endswith("?")],
    "Project": [lambda name: "project" in name.lower()],
    # ...
}

# 매칭되지 않는 엔티티용 GPT-5-Mini fallback
async def classify_with_llm(entity_name: str) -> str:
    response = await openai.chat.completions.create(
        model="gpt-5-mini",
        messages=[{"role": "user", "content": f"'{entity_name}' 분류..."}]
    )
    return response.choices[0].message.content
```

### 4.2 시맨틱 엣지 추론

**파일**: `app/services/entity_cluster_service.py`

```python
PKM_EDGE_TYPE_MATRIX = {
    ("Goal", "Project"): ("ACHIEVED_BY", "달성 수단", "이 목표는 이 프로젝트로 달성"),
    ("Project", "Task"): ("REQUIRES", "필요 작업", "프로젝트에 필요한 태스크"),
    ("Question", "Insight"): ("ANSWERED_BY", "답변", "질문에 대한 답변 인사이트"),
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

---

## 5. 배포

### 5.1 백엔드 배포 (Railway)

```bash
cd didymos-backend

# Railway CLI
npm install -g @railway/cli
railway login

# 배포
railway up --detach

# 로그 확인
railway logs

# 재배포
railway redeploy --yes
```

### 5.2 플러그인 배포

```bash
cd didymos-obsidian

# 빌드
npm run build

# 출력 파일: main.js, manifest.json, styles.css
# GitHub Release 또는 BRAT에 업로드
```

---

## 6. 테스트 & 디버깅

### 6.1 백엔드 테스트

```bash
# Swagger UI
open http://localhost:8000/docs

# entity clusters 테스트
curl "http://localhost:8000/vault/entity-clusters?vault_id=test&user_token=xxx"

# 시맨틱 엣지 테스트
curl "http://localhost:8000/vault/entity-clusters/detail?vault_id=test&user_token=xxx"
```

### 6.2 프론트엔드 디버깅

- Obsidian 개발자 콘솔: `Cmd+Option+I` (Mac) / `Ctrl+Shift+I` (Windows)
- 콘솔 > Network 탭에서 네트워크 요청 확인

### 6.3 Neo4j 쿼리

```cypher
// 엔티티 타입 확인
MATCH (e:Entity)
RETURN e.pkm_type, count(e) as count
ORDER BY count DESC

// 시맨틱 엣지 확인
MATCH (e1:Entity)-[r:RELATES_TO]->(e2:Entity)
RETURN e1.pkm_type, e2.pkm_type, count(r) as edges
ORDER BY edges DESC

// 임베딩 확인
MATCH (e:Entity)
WHERE e.name_embedding IS NOT NULL
RETURN count(e) as entities_with_embeddings
```

---

## 7. 문제 해결

### 7.1 Railway 502 에러

- Railway 로그 확인: `railway logs`
- 흔한 원인: 환경 변수 누락
- 해결: `railway variables`로 확인

### 7.2 빈 시맨틱 엣지

- 엔티티에 `pkm_type` 라벨이 있는지 확인
- 실행: `MATCH (e:Entity) WHERE e.pkm_type IS NULL RETURN count(e)`
- 해결: 노트 재동기화로 분류 트리거

### 7.3 느린 API 응답

- 로그에서 Neo4j 쿼리 성능 확인
- 자주 쿼리되는 필드에 인덱스 추가 고려
- API 응답 캐싱 활성화 (TTL 5-12시간)

---

**질문이 있으시면 GitHub에 이슈를 생성해주세요!**
