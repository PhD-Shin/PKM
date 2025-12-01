# 📘 Didymos - PRD (Product Requirement Document)

> AI-Powered 2nd Brain for Obsidian - 의미론적 지식 그래프 + 생산성 엔진

**최종 업데이트**: 2025-12-02
**현재 단계**: MVP 개발 (2주 Sprint)
**비즈니스 모델**: Obsidian 플러그인 구독 ($7-15/월)

---

## 🎯 Executive Summary

### 제품 비전
**"Smart Connections를 넘어선 구조화된 2nd Brain"**

Didymos는 Obsidian 사용자에게 단순한 유사도 검색을 넘어 **의미론적 계층 구조**와 **AI 인사이트**를 제공하는 지식 관리 시스템입니다.

### 핵심 차별점

| 기능 | Smart Connections | Didymos |
|------|-------------------|---------|
| **검색** | 유사 노트 찾기 | ✅ + 구조화된 맥락 |
| **구조** | 평면적 | ✅ 계층적 지식 그래프 |
| **분석** | 없음 | ✅ 의사결정 인사이트 |
| **추적** | 없음 | ✅ 지식 진화 타임라인 |
| **가격** | 무료 | $7/월 (Pro), $15/월 (Research) |

### 시장 기회

- **PKM 시장**: $500M (2020) → $3B (2025 예상)
- **Obsidian 사용자**: 1M+ (빠르게 성장)
- **타겟**: 연구자, 개발자, PKM 실천가
- **목표**: 2년차 500명 유료 사용자 ($5.7K/월 = $68K/년)

---

## 1. 비즈니스 모델

### 1.1 요금제 구조

#### 🆓 Free Tier
```
✅ 노트 싱크 (월 100회)
✅ 기본 그래프 시각화
✅ 엔티티 추출
❌ 클러스터링
❌ AI 인사이트
❌ 고급 분석
```

#### 💎 Pro - $7/월 ($70/년)
```
✅ 모든 Free 기능
✅ 스마트 클러스터링
✅ AI 요약 (월 100회)
✅ 주간 리뷰 자동화
✅ 우선 지원
✅ 무제한 노트 싱크
```

#### 🔬 Research - $15/월 ($150/년)
```
✅ 모든 Pro 기능
✅ 무제한 AI 쿼리
✅ 커스텀 분석
✅ API 접근
✅ 팀 공유 (5명)
✅ 우선 처리 큐
```

### 1.2 수익 시뮬레이션

**Year 1 (보수적)**
- 무료: 5,000명
- Pro (3%): 150명 × $7 = $1,050/월
- Research (0.5%): 25명 × $15 = $375/월
- **총**: $17K/년

**Year 2 (현실적)**
- 무료: 20,000명
- Pro (3%): 600명 × $7 = $4,200/월
- Research (0.5%): 100명 × $15 = $1,500/월
- **총**: $68K/년

**Year 3 (낙관적)**
- 무료: 50,000명
- Pro (4%): 2,000명 × $7 = $14,000/월
- Research (1%): 500명 × $15 = $7,500/월
- **총**: $258K/년

### 1.3 비용 구조

**사용자당 비용**:
- Neo4j: $0.50/월 (shared infrastructure)
- LLM API: $1.50/월 (caching + batching)
- 인프라: $0.30/월
- **총**: $2.30/월

**마진**:
- Pro: $7 - $2.30 = $4.70 (67%)
- Research: $15 - $2.30 = $12.70 (85%)

---

## 2. 제품 핵심 가치

### 2.1 문제 정의

| 문제 | 현재 솔루션 (Smart Connections) | Didymos 솔루션 |
|------|-------------------------------|---------------|
| 노트가 쌓이지만 정리 안 됨 | 유사 노트 추천만 | **자동 계층 구조 생성** |
| 큰 그림을 못 봄 | 개별 노트만 볼 수 있음 | **지식 클러스터 시각화** |
| 의사결정 지원 없음 | 검색만 가능 | **AI 인사이트 & 추천** |
| 지식 진화 추적 불가 | 정적 스냅샷 | **시간대별 변화 분석** |

### 2.2 타겟 사용자

**Primary**:
1. **연구자/대학원생** (40%)
   - 논문 작성, 문헌 관리
   - 실험 노트 구조화
   - 가격: $15/월도 OK

2. **개발자/기획자** (35%)
   - 프로젝트 관리
   - 회의록 → Task 자동화
   - 가격: $7/월 선호

3. **PKM 파워유저** (25%)
   - Zettelkasten, PARA 실천
   - 고급 기능 필요
   - 가격: $15/월 지불 의향 높음

---

## 3. MVP 기능 범위 (2주 Sprint)

### 3.1 핵심 기능 (Must Have)

#### ✅ 자동 온톨로지 구축
```python
# 노트에서 자동 추출
entities = {
    "topics": ["Machine Learning", "Neural Networks"],
    "projects": ["PhD Thesis"],
    "tasks": ["Write Chapter 3"],
    "persons": ["Prof. Smith"]
}

# Neo4j 그래프 저장
(:Note)-[:MENTIONS]->(:Topic)
(:Note)-[:PART_OF]->(:Project)
(:Note)-[:CONTAINS]->(:Task)
```

#### ✅ 의미론적 클러스터링
```
현재 상태:
- 471 notes → 보이지 않음

MVP 후:
- 471 notes → 3-10 클러스터
- 임베딩 기반 유사도
- LLM 요약 포함
```
- 알고리즘: UMAP + HDBSCAN (샘플 부족/노이즈 시 `umap_hdbscan_fallback:*`로 타입 기반 폴백)
- API: `/graph/vault/clustered?method=semantic|type_based|auto&include_llm=true&force_recompute=true` (캐시 무시 옵션 포함)
- 메타데이터: mention 기반 중요도 + 최근 7일 업데이트 보너스, 샘플 엔티티/노트, 자동 인사이트/Next Action
- 관계: 클러스터 간 공유 엔티티 기반 RELATED_TO 엣지(weight=공유 개수)
- 캐시: TTL 12h, 최신 노트 업데이트보다 오래된 캐시는 자동 무효화
- UI: Obsidian Graph View에서 Semantic/Type 전환, LLM Summary 토글, Recompute 버튼, 상태바 + 클러스터 상세 패널(요약/인사이트/샘플/최근 업데이트/액션) + 샘플 노트 열기 버튼

#### ✅ LLM 통합 (실제 구현)
```python
# cluster_service.py
def generate_llm_summaries(clusters):
    for cluster in clusters:
        prompt = f"""
        이 클러스터의 노트들을 분석해주세요:
        {cluster.notes[:5]}

        1. 공통 주제는?
        2. 최근 변화는?
        3. 다음 액션은?
        """
        cluster.summary = claude.messages.create(prompt)
        cluster.key_insights = extract_insights(cluster.summary)
```

#### ✅ Obsidian 플러그인 UI
```
Control Panel:
├── Dashboard (현재 상태 요약)
├── Graph View (클러스터 시각화)
│   ├── Vault Mode (전체 그래프)
│   └── Note Mode (현재 노트)
├── Context Panel (관련 정보)
├── Task Manager (자동 추출 Task)
└── Weekly Review
```

### 3.2 Nice to Have (Post-MVP)
- 계층적 드릴다운 (Level 1 → 2 → 3)
- 시간대별 변화 추적
- 커스텀 분석 쿼리
- 팀 공유 기능

---

## 4. 기술 아키텍처

### 4.1 시스템 구조

```
┌─────────────────────┐
│  Obsidian Plugin    │ TypeScript
│  (Frontend)         │
└──────────┬──────────┘
           │ REST API
           │ HTTPS
┌──────────▼──────────┐
│  FastAPI Server     │ Python 3.11
│  - Routes           │
│  - Services         │
│  - LLM Client       │
└──────────┬──────────┘
           │
    ┌──────┴──────┐
    │             │
┌───▼────┐   ┌───▼──────┐
│ Neo4j  │   │ Claude   │
│ AuraDB │   │ API      │
└────────┘   └──────────┘
```

### 4.2 데이터 모델 (Neo4j)

```cypher
// 노드
(:User {id, created_at})
(:Vault {id, name})
(:Note {note_id, title, path, content_hash, updated_at})
(:Topic {id, name, importance_score})
(:Project {id, name, status})
(:Task {id, title, status, priority, due_date})
(:Cluster {id, name, level, summary, key_insights[]})

// 관계
(:User)-[:OWNS]->(:Vault)
(:Vault)-[:HAS_NOTE]->(:Note)
(:Note)-[:MENTIONS]->(:Topic)
(:Note)-[:PART_OF]->(:Project)
(:Note)-[:CONTAINS]->(:Task)
(:Cluster)-[:CONTAINS]->(:Note)
(:Cluster)-[:CONTAINS]->(:Topic)
(:Cluster)-[:SUB_CLUSTER]->(:Cluster)
```

### 4.3 Neo4j 독립성 전략

**현재 (MVP)**: Neo4j Aura 사용
- 빠른 개발
- 무료 티어 활용
- 비용: 사용자당 $0.50/월

**Phase 2 (1000명 후)**: 옵션 추가
```python
# abstraction layer
class GraphBackend:
    @staticmethod
    def create(backend_type):
        if backend_type == "neo4j":
            return Neo4jEngine()
        elif backend_type == "local":
            return NetworkXEngine()  # SQLite + NetworkX
```

**Phase 3 (수익 안정 후)**: 완전 독립
- 자체 그래프 엔진
- Neo4j는 premium 옵션

---

## 5. MVP 개발 계획 (2주)

### Week 1: 기능 완성

**Day 1-2: LLM 통합** ✅
```python
# app/services/llm_client.py
class ClaudeLLMClient:
    def summarize_cluster(self, notes):
        # 실제 Claude API 호출
        # 요약 + 인사이트 생성
```

**Day 3-4: 의미론적 클러스터링** ✅
```python
# app/services/cluster_service.py
def compute_clusters_semantic(vault_id):
    # 1. 임베딩 가져오기
    # 2. UMAP 차원 축소
    # 3. HDBSCAN 클러스터링
    # 4. 실패/노이즈 시 타입 기반 클러스터링으로 폴백
```
- API: `/graph/vault/clustered?method=semantic|type_based|auto&include_llm=true&force_recompute=true`
- UI: Graph View에서 Semantic/Type 토글, LLM Summary 토글, Recompute 버튼/상태바 추가

**Day 5-7: 버그 수정 & 테스트**
- 엣지 케이스 처리
- 성능 최적화
- 사용자 경험 다듬기

### Week 2: 베타 런칭

**Day 8-9: 문서화**
- README 업데이트
- 사용 가이드 작성
- 1분 데모 영상

**Day 10-11: 배포 준비**
- Railway 설정 확인
- 모니터링 구축
- 베타 키 시스템

**Day 12-14: 커뮤니티 런칭**
- Reddit r/ObsidianMD 포스트
- Discord 공지
- 첫 10명 베타 테스터 모집

---

## 6. 성공 지표

### 6.1 MVP 검증 (2주 후)

✅ **진행 신호**:
- 5명 이상 "돈 낼게요" 코멘트
- 10명 이상 적극 사용
- 구체적 피드백 많음

⚠️ **피봇 신호**:
- 특정 기능 불만 집중
- "이것만 있으면" 코멘트
→ 해당 기능 우선 구현

❌ **중단 신호**:
- 3명 미만 관심
- 조회수 < 100
→ 다른 아이디어 찾기

### 6.2 비즈니스 지표

**3개월 후**:
- 50명 유료 사용자
- $350/월 수익
- Churn < 10%

**6개월 후**:
- 200명 유료 사용자
- $1,400/월 수익
- NPS > 40

**1년 후**:
- 500명 유료 사용자
- $3,500/월 수익
- 유료 전환율 > 3%

---

## 7. 마케팅 전략

### 7.1 런칭 계획

**Week 1-2 (베타)**:
- Reddit AMA
- Discord 공지
- Twitter 스레드

**Month 1 (Early Access)**:
- YouTube 튜토리얼
- 블로그 포스트 (SEO)
- PKM 인플루언서 협업

**Month 2-3 (Public Launch)**:
- Product Hunt 런칭
- Obsidian 포럼 핀
- 할인 프로모션

### 7.2 메시지

**헤드라인**:
> "Smart Connections를 넘어선 구조화된 2nd Brain"

**피치**:
```
Obsidian 노트가 많아질수록 정리는 어려워집니다.

Didymos는:
✅ 자동으로 지식을 구조화하고
✅ AI가 놓친 연결을 찾아주며
✅ 의사결정을 지원하는 인사이트를 제공합니다.

Smart Connections: "비슷한 노트 찾기"
Didymos: "지식의 큰 그림 보기"

첫 달 무료, 14일 환불 보장
```

---

## 8. 리스크 & 대응

| 리스크 | 확률 | 대응책 |
|--------|------|--------|
| 시장 반응 없음 | 40% | 2주 안에 검증, 빠른 피봇 |
| Neo4j 비용 증가 | 10% | NetworkX 마이그레이션 준비 |
| 경쟁자 등장 | 30% | First mover + 커뮤니티 구축 |
| LLM API 비용 폭발 | 15% | 캐싱 + 배칭 최적화 |

---

## 9. API 명세

### 9.1 핵심 엔드포인트

```
POST   /notes/sync
       노트 동기화 및 온톨로지 자동 추출

GET    /graph/vault/clustered?vault_id={id}&user_token={token}
       클러스터링된 Vault 그래프
       Response: {clusters[], edges[], summary}

POST   /graph/vault/clustered/invalidate
       클러스터 캐시 무효화

GET    /notes/context/{note_id}
       노트 컨텍스트 (관련 topics, projects, tasks)

GET    /review/weekly?vault_id={id}
       주간 리뷰 데이터
```

### 9.2 클러스터 API 응답 형식

```json
{
  "status": "success",
  "level": 1,
  "cluster_count": 8,
  "total_nodes": 471,
  "clusters": [
    {
      "id": "cluster_1",
      "name": "Research Methodology",
      "node_count": 67,
      "summary": "Mixed-methods research approaches with focus on qualitative coding...",
      "key_insights": [
        "3주간 15개 노트 추가 (활발)",
        "Qualitative coding 집중 중",
        "실제 실험 진행 0개 → 액션 필요"
      ],
      "importance_score": 8.5,
      "last_updated": "2024-12-01T10:00:00Z",
      "contains_types": {
        "topic": 12,
        "note": 55
      }
    }
  ],
  "edges": [],
  "last_computed": "2024-12-01T15:30:00Z",
  "computation_method": "semantic_embedding"
}
```

---

## 10. 프라이버시 & 보안

### 10.1 데이터 처리

```
사용자 노트 → 로컬에서 YAML 추출 → API 전송 → Neo4j 저장
           └→ LLM API (Claude) → 즉시 폐기
```

### 10.2 프라이버시 모드

| 모드 | 전송 데이터 | 정확도 |
|------|------------|--------|
| 🔵 Full | 전체 본문 | 최고 (95%) |
| 🟡 Summary | 요약만 | 중간 (80%) |
| 🔴 Metadata | 제목/태그만 | 낮음 (60%) |

### 10.3 보안

- HTTPS 강제
- JWT 인증
- Vault별 데이터 격리
- 토큰 암호화 저장
- GDPR 준수 (삭제 요청 처리)

---

## 11. 배포 전략

### 11.1 Backend (FastAPI)

**Platform**: Railway
- Docker 자동 빌드
- 환경변수: `NEO4J_URI`, `CLAUDE_API_KEY`, `STRIPE_SECRET_KEY`
- Health check: `/health`
- Auto-scaling: 2-4 instances

### 11.2 Frontend (Obsidian Plugin)

**Distribution**:
1. Community Plugins (승인 후)
2. BRAT (베타 기간)
3. GitHub Releases

**Update 전략**:
- Semantic versioning
- 자동 업데이트 체크
- 변경사항 알림

---

## 12. 다음 단계 (Post-MVP)

### Phase 2 (Month 2-3)
- 계층적 드릴다운 (조건부)
- 시간대별 분석
- 커스텀 쿼리 API

### Phase 3 (Month 4-6)
- 팀 공유 기능
- 모바일 앱
- Zapier 통합

### Phase 4 (Year 2)
- 자체 그래프 엔진
- 오픈 소스 코어
- 엔터프라이즈 플랜

---

## 부록 A: 경쟁 분석

| 제품 | 장점 | 단점 | 가격 |
|------|------|------|------|
| **Smart Connections** | 무료, 빠름 | 구조 없음 | Free |
| **Copilot** | 무료, 로컬 | 기본 기능만 | Free |
| **Mem.ai** | AI 네이티브 | 락인, 비쌈 | $15/월 |
| **Reflect** | 깔끔, 빠름 | 비쌈 | $10/월 |
| **Didymos** | 구조 + AI | 유료 | $7-15/월 |

---

## 부록 B: LLM 프롬프트 템플릿

```python
CLUSTER_SUMMARY_PROMPT = """
다음은 사용자의 지식 그래프에서 발견된 클러스터입니다.

클러스터 이름: {cluster_name}
포함 노트 수: {node_count}
노트 샘플:
{note_samples}

다음 질문에 답해주세요:
1. 이 클러스터의 공통 주제는 무엇인가?
2. 최근 3주간 어떤 변화가 있었나?
3. 사용자가 고민하는 핵심 질문은?
4. 다음에 취해야 할 구체적 액션 3가지는?

응답 형식:
SUMMARY: [2-3문장 요약]
INSIGHTS:
- [인사이트 1]
- [인사이트 2]
- [인사이트 3]
"""
```

---

**문서 버전**: 2.0
**최종 검토**: 2025-12-02
**다음 리뷰**: MVP 런칭 후 (2025-12-16)
