# Phase 11: 의미론적 계층 클러스터링 MVP

**예상 시간**: 2주 (Day 1-14)
**목표**: 구독 가치 입증
**상태**: Week 1-2 완료, Day 12-13 테스트 진행 중

---

## 핵심 차별점

| 기능 | Smart Connections | Didymos |
|------|-------------------|---------|
| 검색 | 유사 노트 찾기 (평면적) | 의미론적 계층 그래프 |
| 분석 | 단순 임베딩 매칭 | LLM 기반 클러스터 요약 |
| 인사이트 | 없음 | 의사결정 인사이트 |
| 구조 | 평면적 | 구조화된 2nd Brain |

---

## Week 1: LLM 통합 & 의미론적 클러스터링 (Day 1-7)

### Day 1-2: GPT-5 Mini API 통합 ✅ 2025-12-02 완료

**파일**: `app/services/llm_client.py`

- LLM 클라이언트 설정
- 클러스터 요약 프롬프트 작성
- `generate_llm_summaries()` 실제 구현
- 모든 gpt-4o-mini → gpt-5-mini 마이그레이션
- API 버그 수정 및 백엔드 테스트 완료

### Day 3-4: 의미론적 클러스터링 알고리즘 ✅ 2025-12-02 완료

**알고리즘**: UMAP + HDBSCAN

```python
# 1. 노트 임베딩 로드
embeddings = get_note_embeddings(vault_id)

# 2. UMAP 차원 축소 (고차원 → 2D/3D)
reduced = umap.UMAP(n_components=2).fit_transform(embeddings)

# 3. HDBSCAN 클러스터링
clusters = hdbscan.HDBSCAN(min_cluster_size=5).fit_predict(reduced)
```

**폴백 전략**:
- 노이즈/샘플 부족 시 자동 폴백 (`umap_hdbscan_fallback:*`)
- `compute_clusters_semantic()` 개선: 최소 샘플 가드
- 클러스터 미생성 시 타입 기반 폴백

**API 파라미터**:
- `method`: `semantic`, `type_based`, `auto`
- `no_cache`: 캐시 무시 옵션

**Obsidian Graph View**:
- 클러스터링 방식/LLM 요약 토글
- Recompute 버튼 추가
- 상태 표시바로 피드백 제공

### Day 5-6: 클러스터 메타데이터 강화 ✅ 2025-12-02 완료

**중요도 계산**:
```python
importance = mention_count + recency_bonus
# recency_bonus: 최근 7일 업데이트 수
```

**메타데이터**:
- 샘플 엔티티/노트 (최대 5개)
- 자동 인사이트/Next Action 추가
- 클러스터 간 공유 엔티티 기반 엣지 생성 (RELATED_TO, weight=공유 개수)

**캐싱**:
- 캐시 TTL 12시간
- 최신 노트 업데이트보다 오래된 캐시는 자동 무효화

**Obsidian Graph View**:
- 클러스터 상세 패널 (요약/인사이트/샘플/최근 업데이트/액션)
- 샘플 노트 바로 열기 버튼 제공

### Day 7: 캐싱 & 성능 최적화 ✅ 2025-12-02 완료

- 클러스터 캐시 TTL 12시간으로 최적화
- 증분 업데이트 로직 (노트 변경 시 캐시 무효화)
- LLM 병렬 처리 (ThreadPoolExecutor, 최대 3개 동시)
- 백그라운드 캐시 워밍업 기능 추가 (warmup 파라미터)

---

## Week 2: UI 개선 & 사용자 테스트 (Day 8-14)

### Day 8-9: 계층적 탐색 UI ✅ 2025-12-02 완료

**애니메이션**:
- 클러스터 상세 패널 슬라이드 애니메이션 (slideInRight)
- 인사이트/액션 hover 애니메이션 (translateX)
- 샘플 노트 버튼 hover 효과 추가
- 상태 바 hover 효과로 사용자 피드백 개선

### Day 10-11: 의사결정 인사이트 강화 ✅ 2025-12-02 완료

- LLM 기반 "다음 행동 제안" (next_actions) 생성
- 최근 7일간 업데이트 수 통계 표시
- 클러스터별 샘플 노트 제공 (최대 5개)
- 실행 가능한 인사이트 생성 프롬프트 개선

### Day 12-13: 내부 테스트 (진행 중)

- [ ] 본인 Vault (471개 노트)로 실전 테스트
- [ ] 클러스터 품질 평가 (의미 있는 그룹화?)
- [ ] UX 버그 수정
- [ ] API 응답 시간 측정

### Day 14: 베타 준비

- [ ] 데모 비디오 녹화 (1분)
- [ ] README 업데이트 (스크린샷 포함)
- [ ] Beta 키 시스템 설정

---

## 성공 지표 (2주 후 평가)

### 기술적 성공

| 지표 | 목표 |
|------|------|
| 클러스터 축소 | 471개 노트 → 8-12개 클러스터 |
| 요약 생성 성공률 | > 95% |
| API 응답 시간 | < 2초 |

### 사용자 가치

| 지표 | 목표 |
|------|------|
| "의미 있는 그룹화" 자가 평가 | ≥ 8/10 |
| LLM 인사이트 유용성 | 실제로 유용함 |
| Smart Connections 대비 | 우월성 체감 |

### 비즈니스 준비

- 데모 가능한 상태
- 구독 가치 명확히 설명 가능
- 베타 런칭 준비 완료

---

## 체크리스트

### Week 1
- [x] Day 1-2: GPT-5 Mini API 통합
- [x] Day 3-4: 의미론적 클러스터링 알고리즘
- [x] Day 5-6: 클러스터 메타데이터 강화
- [x] Day 7: 캐싱 & 성능 최적화

### Week 2
- [x] Day 8-9: 계층적 탐색 UI
- [x] Day 10-11: 의사결정 인사이트 강화
- [ ] Day 12-13: 내부 테스트
- [ ] Day 14: 베타 준비
