# Phase 9: 패턴 분석 & 의사결정 추천

**예상 시간**: 6~8시간
**완료일**: 2025-12-01

---

## 목표

사용자의 지식 그래프에서 자동으로 패턴을 발견하고, 의사결정을 지원하는 추천을 제공합니다.

---

## 백엔드 알고리즘

### PageRank 구현

**파일**: `pattern_service.py::calculate_pagerank`

Google의 검색 알고리즘을 노트에 적용하여 핵심 노트를 자동 발견합니다.

```python
# 핵심 노트 Top 10 반환
# 사용자 용어: "가장 중요한 노트"
```

### Community Detection

**파일**: `pattern_service.py::detect_communities`

DFS 기반 연결 요소 찾기로 지식 클러스터를 자동 그룹화합니다.

```python
# 지식 클러스터 Top 5 반환
# 사용자 용어: "지식 클러스터"
```

### Orphan Detection

**파일**: `pattern_service.py::find_orphan_notes`

고립된 노트(연결 없는 노트)를 발견합니다.

```python
# 연결 없는 노트 목록 반환
# 사용자 용어: "고립된 노트"
```

### Task Prioritization

**파일**: `recommendation_service.py::prioritize_tasks`

우선순위 계산 공식:
```
priority_score = priority_weight + due_weight + connection_weight
```

- **Overdue**: 마감일 지남
- **Due today**: 오늘 마감
- **Due in Nd**: N일 후 마감

### Missing Connections

**파일**: `recommendation_service.py::find_missing_connections`

같은 Topic 2개 이상 공유하지만 직접 연결되지 않은 노트 쌍을 찾습니다.

```python
# "놓친 연결" 제안으로 표현
```

---

## API 엔드포인트

### 패턴 분석

```
GET /patterns/analyze/{user_token}/{vault_id}
```

**응답 예시**:
```json
{
  "overview": {
    "total_notes": 471,
    "total_connections": 1234,
    "avg_connections_per_note": 2.6
  },
  "important_notes": [...],
  "knowledge_clusters": [...],
  "isolated_notes": [...]
}
```

### 의사결정 추천

```
GET /patterns/recommendations/{user_token}/{vault_id}
```

**응답 예시**:
```json
{
  "priority_tasks": [...],
  "suggested_connections": [...]
}
```

---

## 프론트엔드 UI

### Insights View

**파일**: `insightsView.ts`

#### 버튼
- 🔍 **Analyze Patterns**: 패턴 분석 실행
- 💡 **Get Recommendations**: 의사결정 추천 실행

#### 패턴 분석 결과 섹션
- 📊 **Overview**: 통계 (노트 수, 연결 수, 평균 연결)
- ⭐ **Most Important Notes**: 핵심 노트 Top 10
- 🔗 **Knowledge Clusters**: 지식 클러스터 Top 5
- 🏝️ **Isolated Notes**: 고립된 노트

#### 의사결정 추천 섹션
- 🎯 **Priority Tasks**: 우선순위 Top 10
- 🔗 **Suggested Connections**: 놓친 연결

### 명령 등록

**파일**: `main.ts`

```typescript
this.addCommand({
  id: 'open-insights',
  name: 'Open Knowledge Insights',
  callback: () => this.activateView(VIEW_TYPE_INSIGHTS)
});
```

---

## 성과

- 자동 패턴 발견으로 사용자 인사이트 제공
- 과학적 알고리즘 (PageRank, Community Detection) 기반
- 의사결정 지원 (중요도 + 긴급도 + 연결성 고려)
- **UX 용어 매핑 적용**: 기술 용어 → 사용자 친화적 언어

---

## 체크리스트

- [x] PageRank 구현
- [x] Community Detection
- [x] Orphan Detection
- [x] Task Prioritization
- [x] Missing Connections
- [x] API 엔드포인트
- [x] Insights View UI
- [x] 명령 등록
