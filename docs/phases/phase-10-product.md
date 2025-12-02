# Phase 10: 제품 개선 & 사용자 경험 강화

**예상 시간**: 8~10시간
**시작일**: 2025-12-01
**상태**: 문서화 완료, 기능 구현은 Phase 11 이후 예정

---

## 목표

PRD/UseCase 문서 업데이트 및 향후 사용자 경험 개선 계획 수립

---

## 문서화 개선 (완료)

### PRD 업데이트

- [x] 제품 포지셔닝 추가 ("Zettelkasten을 자동으로 해주는 두 번째 두뇌")
- [x] Core Loop 정의 (쓰기 → 제안 → 수락/거절 → 리뷰)
- [x] UX 용어 매핑 (Ontology → 자동 구조화된 지식)
- [x] Onboarding & 템플릿 섹션 추가
- [x] Insights Panel 행동 중심으로 강화
- [x] Offline/Degraded Mode 전략 추가
- [x] AI Feedback Loop 설계 추가
- [x] Automation Recipes 기능 명세 추가

### UseCase 업데이트

- [x] 신규 사용자 온보딩 시나리오 추가 (템플릿 기반)
- [x] UX 용어 매핑 반영 (기술 용어 → 사용자 언어)
- [x] Automation Recipes 사용 사례 추가
- [x] Offline/Degraded Mode 사용 사례 추가

### Process 업데이트

- [x] Phase 5 Graph Panel 기능 업데이트 (클러스터링, Control Panel)
- [x] Phase 10 추가 (현재 진행 중)
- [x] Phase 11 계층적 클러스터링 로드맵 추가

---

## 향후 구현 계획

### 프론트엔드 개선

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

### 백엔드 개선

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

### 핵심 지표

- [ ] **Acceptance Rate 추적**
  - 사용자별 수락률 측정
  - 개선 추이 대시보드
  - 목표: 60% → 85% (1개월) → 95% (6개월)

---

## 체크리스트

- [x] PRD 업데이트
- [x] UseCase 업데이트
- [x] Process 업데이트
- [ ] 온보딩 경험 구현
- [ ] Automation Recipes MVP
- [ ] Feedback Loop UI
- [ ] Feedback 노드 모델
- [ ] Automation Service
- [ ] Offline Mode 지원
- [ ] Acceptance Rate 추적
