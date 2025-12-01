# 📊 패턴 분석 & 의사결정 추천

> Phase 9에서 구현된 고급 그래프 분석 기능

---

## 1. 개요

### 목적
사용자의 지식 그래프를 분석하여 자동으로 패턴을 발견하고, 의사결정을 지원하는 추천을 제공합니다.

### 핵심 원칙
**"The chain is only as strong as its weakest link"**
- 가장 약한 부분을 찾아 보완하도록 유도
- 고립된 지식, 방치된 프로젝트, 미루는 태스크 발견
- 놓친 연결을 찾아 지식 통합 촉진

---

## 2. 패턴 분석 알고리즘

### 2.1 PageRank (중요 노트 발견)

**알고리즘**: Google의 검색 랭킹 알고리즘을 노트에 적용

```python
def calculate_pagerank(nodes, edges, damping=0.85, iterations=20):
    """
    PageRank = (1-d)/N + d * Σ(PR(incoming) / outdegree(incoming))

    - damping: 0.85 (표준값)
    - iterations: 20회 수렴
    """
    # 초기값: 모든 노트 균등
    pagerank = {node: 1.0 / len(nodes) for node in nodes}

    # 반복 계산
    for _ in range(iterations):
        for node in nodes:
            rank = (1 - damping) / len(nodes)
            # 들어오는 링크로부터 PageRank 누적
            for incoming in get_incoming_links(node):
                rank += damping * pagerank[incoming] / outdegree[incoming]
            new_pagerank[node] = rank
```

**활용**:
- 많이 연결된 노트 = 중요한 개념
- 중요한 노트들과 연결된 노트 = 더 중요
- Top 10 노트를 자동으로 추천

**예시 결과**:
```
⭐ Most Important Notes
#1 Knowledge Management (15.43%)
#2 Second Brain (12.87%)
#3 PKM System (8.91%)
```

### 2.2 Community Detection (지식 클러스터)

**알고리즘**: DFS 기반 연결 요소(Connected Components) 탐색

```python
def detect_communities(nodes, edges):
    """
    무향 그래프에서 DFS로 연결된 노드 그룹 찾기
    """
    graph = build_undirected_graph(edges)
    visited = set()
    communities = {}

    def dfs(node, community_id):
        visited.add(node)
        communities[node] = community_id
        for neighbor in graph[node]:
            if neighbor not in visited:
                dfs(neighbor, community_id)

    community_id = 0
    for node in nodes:
        if node not in visited:
            dfs(node, community_id)
            community_id += 1
```

**활용**:
- 관련된 노트들이 자연스럽게 그룹화
- 지식 영역(Domain) 자동 발견
- Top 5 커뮤니티 표시

**예시 결과**:
```
🔗 Knowledge Clusters
Cluster 1 (35 notes)
- Daily Notes/2024-11-30
- Projects/PKM System
... and 30 more

Cluster 2 (18 notes)
- Research/Paper Review
- Topics/Machine Learning
```

### 2.3 Orphan Detection (고립된 노트)

**알고리즘**: 연결 없는 노드 탐색

```python
def find_orphan_notes(nodes, edges):
    """
    연결이 전혀 없는 노트 찾기
    """
    connected = set()
    for from_node, to_node in edges:
        connected.add(from_node)
        connected.add(to_node)

    orphans = [node for node in nodes if node not in connected]
    return orphans
```

**활용**:
- 고립된 아이디어 발견
- 연결 촉진 (제안 시스템과 연동)

**예시 결과**:
```
🏝️ Isolated Notes
23 notes have no connections. Consider linking them.
- Random Idea.md
- Meeting Notes.md
```

---

## 3. 의사결정 추천

### 3.1 Task 우선순위 계산

**알고리즘**: 다차원 스코어링

```python
def prioritize_tasks(user_id, vault_id):
    """
    Score = priority_weight + due_weight + connection_weight

    1. priority_weight: high=3, medium=2, low=1
    2. due_weight:
       - Overdue: 5.0
       - Due today: 4.0
       - Due tomorrow: 3.5
       - Due in 2-7d: 2.5
       - Due in 8-30d: 1.5
       - Due 30d+: 0.5
    3. connection_weight: min(connections * 0.1, 2.0)
    """
```

**활용**:
- 지금 집중해야 할 Task 자동 추천
- 중요도 + 긴급도 + 연결성 종합 고려
- Top 10 우선순위 Task

**예시 결과**:
```
🎯 Priority Tasks
#1 Finish PKM implementation HIGH
   Overdue (2d) in Projects/PKM System
   Score: 8.5

#2 Review weekly goals MEDIUM
   Due today in Daily Notes/2024-12-01
   Score: 7.2
```

### 3.2 놓친 연결 제안

**알고리즘**: Topic 기반 유사도

```cypher
// 같은 Topic 2개 이상 공유하지만 연결 안 된 노트 쌍
MATCH (n1:Note)-[:MENTIONS]->(topic:Topic)<-[:MENTIONS]-(n2:Note)
WHERE n1.note_id < n2.note_id
  AND NOT (n1)-[:MENTIONS|:RELATES_TO]-(n2)
WITH n1, n2, collect(DISTINCT topic.name) AS shared_topics
WHERE size(shared_topics) >= 2
RETURN n1, n2, shared_topics
ORDER BY size(shared_topics) DESC
```

**활용**:
- 관련 있지만 연결 안 된 노트 발견
- 지식 통합 촉진

**예시 결과**:
```
🔗 Suggested Connections
Knowledge Management ↔️ Second Brain
Share 3 topics: PKM, Note-taking, Learning

Daily Notes/2024-11-30 ↔️ Projects/PKM
Share 2 topics: Implementation, Development
```

---

## 4. 약점 분석 (계획 중)

### 4.1 약점 탐지 영역

```python
def analyze_weaknesses(user_id, vault_id):
    return {
        "isolated_topics": find_isolated_topics(),
        # Topic은 있지만 연결 없음

        "stale_projects": find_stale_projects(),
        # 30일 이상 업데이트 없는 프로젝트

        "chronic_overdue": find_chronic_tasks(),
        # 반복적으로 미루는 Task

        "weak_clusters": find_sparse_areas(),
        # 연결이 희박한 지식 영역

        "knowledge_gaps": detect_missing_coverage()
        # 관련 Topic은 많은데 실제 노트는 부족
    }
```

### 4.2 보완 추천 예시

```
🔍 Critical Weakness Detected

⚠️ Project Management (Weakness Score: 8.5/10)
- 3 abandoned projects (>30d no update)
- 15 overdue tasks in this area
- Only 2 connections to other knowledge areas

💡 Strengthening Plan:
1. Review "GTD System" note (45d ago)
2. Connect to "Time Management" cluster
3. Complete 3 high-priority tasks this week
4. Create "Project Review" recurring task

📚 Learning Resources:
- "Weekly Review Process" (similar, not connected)
- "PARA Method" (related methodology)
```

---

## 5. API 엔드포인트

### 5.1 패턴 분석

```http
GET /api/v1/patterns/analyze/{user_token}/{vault_id}
```

**Response**:
```json
{
  "status": "success",
  "patterns": {
    "important_notes": [
      {"note_id": "...", "score": 0.1543}
    ],
    "communities": [
      {"id": 0, "notes": [...], "size": 35}
    ],
    "orphan_notes": [...],
    "stats": {
      "total_notes": 150,
      "total_connections": 432,
      "num_communities": 8,
      "num_orphans": 23,
      "avg_connections_per_note": 2.88
    }
  }
}
```

### 5.2 의사결정 추천

```http
GET /api/v1/patterns/recommendations/{user_token}/{vault_id}
```

**Response**:
```json
{
  "status": "success",
  "recommendations": {
    "priority_tasks": [
      {
        "task_id": "...",
        "title": "Finish PKM implementation",
        "priority": "high",
        "urgency": "Overdue (2d)",
        "score": 8.5,
        "note_id": "...",
        "note_title": "Projects/PKM System"
      }
    ],
    "missing_connections": [
      {
        "note1_id": "...",
        "note1_title": "Knowledge Management",
        "note2_id": "...",
        "note2_title": "Second Brain",
        "shared_topics": ["PKM", "Note-taking", "Learning"],
        "topic_count": 3,
        "reason": "Share 3 topics: PKM, Note-taking, Learning"
      }
    ]
  }
}
```

---

## 6. 프론트엔드 UI

### 6.1 Insights View

**명령**: `Ctrl/Cmd + P` → "Open Knowledge Insights"

**화면 구성**:
```
💡 Knowledge Insights

[🔍 Analyze Patterns]  [💡 Get Recommendations]

📊 Overview
- Total Notes: 150
- Connections: 432
- Communities: 8
- Avg Connections/Note: 2.88

⭐ Most Important Notes
#1 Knowledge Management (15.43%)
#2 Second Brain (12.87%)
...

🔗 Knowledge Clusters
Cluster 1 (35 notes)
...

🏝️ Isolated Notes
23 notes have no connections...

🎯 Priority Tasks
#1 Finish PKM implementation HIGH
...

🔗 Suggested Connections
Knowledge Management ↔️ Second Brain
...
```

### 6.2 인터랙션

- **노트 클릭**: 해당 노트 열기
- **Analyze Patterns**: 패턴 분석 실행 (1-2초)
- **Get Recommendations**: 추천 생성 (1-2초)
- **진행률 표시**: 분석 중 상태 표시

---

## 7. 성능 고려사항

### 7.1 알고리즘 복잡도

- **PageRank**: O(N * iterations) = O(20N) ≈ O(N)
- **Community Detection**: O(N + E) (DFS)
- **Orphan Detection**: O(N + E)
- **Task Prioritization**: O(T) (T = task 수)
- **Missing Connections**: O(N²) (최악), 실제 O(T * N) (T = topic당 노트)

### 7.2 대규모 그래프 대응

**현재 제한**:
- Vault Graph: 최대 100개 노트
- Pattern Analysis: 제한 없음 (서버 처리)

**개선 방향**:
- 캐싱 (패턴 분석 결과 5분)
- 증분 업데이트 (전체 재계산 대신)
- 백그라운드 처리 (주기적 자동 분석)

---

## 8. 향후 개선 계획

### Phase 2.1: 약점 분석 구현
- [ ] 고립된 Topic 탐지
- [ ] 방치된 Project 발견
- [ ] 만성 미루기 Task 분석
- [ ] 지식 공백 탐지

### Phase 2.2: 고급 알고리즘
- [ ] Betweenness Centrality (중개자 노트)
- [ ] Clustering Coefficient (밀집도)
- [ ] Link Prediction (미래 연결 예측)

### Phase 2.3: AI 인사이트
- [ ] 패턴 요약을 LLM이 자연어로 설명
- [ ] 개인화된 추천 (학습 스타일 반영)
- [ ] 자동 리뷰 노트 생성

---

## 9. 참고 자료

### 알고리즘
- [PageRank - Wikipedia](https://en.wikipedia.org/wiki/PageRank)
- [Connected Components - Graph Theory](https://en.wikipedia.org/wiki/Component_(graph_theory))

### 구현
- `didymos-backend/app/services/pattern_service.py`
- `didymos-backend/app/services/recommendation_service.py`
- `didymos-backend/app/api/routes_pattern.py`
- `didymos-obsidian/src/views/insightsView.ts`
