# 📘 Didymos - PRD (Product Requirement Document)

> 온톨로지 기반 개인 지식 그래프 + AI 생산성 엔진

---

## 1. 제품 개요

### 1.1 핵심 가치
**Didymos**는 Obsidian 노트를 기반으로 자동으로 지식 그래프를 구축하고, AI가 노트 간 연결을 발견하여 생산성을 극대화하는 시스템입니다.

### 1.2 제품 포지셔닝
> "Zettelkasten을 자동으로 해주는 두 번째 두뇌"
>
> Didymos는 Obsidian 환경에서 **Mem.ai급 지식 연결 + Notion AI급 자동화**를 제공하는 개인용 "Palantir Foundry Lite"입니다.

### 1.3 핵심 루프 (Core Loop)
Didymos의 성공은 이 루프가 원활히 작동하는지로 결정됩니다:

```
1. 사용자가 노트를 작성한다
   ↓
2. Didymos가 즉시 구조화·추천·Task 추출 등 "다음 행동"을 제안
   ↓
3. 사용자가 10초 내로 정리하거나 수락/거절
   ↓
4. Weekly Review에서 재조정
   ↓
다시 1번으로 회귀
```

**핵심 지표**: 사용자가 제안을 수락하는 비율 (Acceptance Rate)

### 1.4 기술 스택 / 배포
- **백엔드**: FastAPI + Neo4j AuraDB + OpenAI
- **프론트엔드**: Obsidian 플러그인 (TypeScript)
- **AI**: neo4j-genai + GPT-4
- **배포**: Railway (Dockerfile 자동 감지, prod 도메인: `https://didymos-backend-production.up.railway.app`)

---

## 2. 해결하려는 문제

| 문제 | Didymos의 솔루션 |
|------|----------------|
| 노트가 쌓이지만 정리는 안 됨 | 자동 온톨로지 구축 |
| 중요한 아이디어가 묻힘 | AI 기반 연관 노트 추천 |
| 노트 간 연결 수동 관리 어려움 | 자동 그래프 생성 |
| 프로젝트/Task 추적 복잡 | 자동 추출 및 추적 |

---

## 3. 타겟 사용자

1. **연구자/대학원생** - 논문, 실험 노트, 아이디어 관리
2. **개발자/기획자** - 프로젝트, 회의록, 기술 노트
3. **PKM 실천가** - Zettelkasten, PARA 사용자

---

## 3.5 UX 용어 매핑 (내부 구현 → 사용자 언어)

Didymos의 UI/문서에서는 기술 용어를 사용자 친화적 언어로 변환합니다:

| 내부 구현 | 사용자에게 보이는 언어 |
|----------|-------------------|
| Ontology | 자동 구조화된 지식 |
| Graph | 노트 간 연결 지도 |
| PageRank | 핵심 노트 / 중요한 노트 |
| Community Detection | 지식 클러스터 / 주제 그룹 |
| Orphan Detection | 고립된 노트 / 연결 없는 노트 |
| Missing Connections | 놓친 연결 / 연결 제안 |
| Weakness Analysis | 약점 분석 / 보완이 필요한 영역 |

**원칙**: 모든 사용자 대면 문구는 이 용어로 통일합니다.

---

## 3.6 Onboarding & 추천 템플릿

Didymos의 성능은 입력 구조에 영향을 받으므로, 신규 사용자에게 **추천 노트 구조**를 제공합니다.

### 추천 태그 네임스페이스
```
#project/project-name    # 프로젝트
#meeting/yyyy-mm-dd      # 회의록
#idea                    # 아이디어
#reading/book-name       # 독서 노트
#area/productivity       # 관심 영역
#person/name             # 인물
```

### 제공 템플릿

#### 1. Meeting Note Template
```markdown
---
tags: [#meeting/2024-12-01]
attendees: [[Person A]], [[Person B]]
---

# Meeting: {{title}}

## Agenda
-

## Decisions
-

## Action Items
- [ ] Task 1 (due: 2024-12-10) #high
```

#### 2. Idea Note Template
```markdown
---
tags: [#idea]
related: []
---

# 💡 {{title}}

## Core Concept


## Potential Applications


## Related Topics
- [[Topic A]]
```

#### 3. Project Note Template
```markdown
---
tags: [#project/project-name]
status: active
start_date: 2024-12-01
---

# 📁 Project: {{title}}

## Goal


## Tasks
- [ ] Task 1 #high (due: 2024-12-15)

## Resources
- [[Related Note]]
```

#### 4. Daily/Weekly Review Template
```markdown
---
tags: [#review/weekly]
date: 2024-W48
---

# 📝 Weekly Review

## Highlights


## Completed


## Next Week Focus
```

**효과**: 이 구조로 작성된 노트는 Didymos가 정확히 추출·연결할 수 있습니다.

---

## 4. 핵심 기능 (MVP)

### 4.1 자동 온톨로지 구축
- 노트에서 **Topic, Project, Task, Person** 자동 추출
- 엔티티 간 관계 자동 생성 (BROADER/NARROWER/RELATED)
- Neo4j 그래프 DB에 실시간 업데이트
- **🔄 자동 반영**: 노트 수정 시 온톨로지 자동 재추출 (realtime/hourly 모드)

### 4.2 Obsidian 플러그인
- **Control Panel**: 13개 개별 명령 → 1개 통합 패널 (UX 개선)
  - 📊 Views (Dashboard, Context, Graph, Task, Review, Decision, Insights)
  - ⚡ Actions (Export Ontology, Generate Decision Note)
  - 🔄 Sync (Sync Current Note)
  - 📝 Templates (Template Gallery, Onboarding)

- **Context Panel**: 현재 노트 관련 Topics, Projects, Tasks, 연관 노트

- **Graph Panel**: 지식 그래프 시각화 (vis-network 기반)
  - **Note 모드**: 현재 노트 중심 그래프 (1-5 hops)
  - **Vault 모드**: 전체 Vault 그래프 - **기본값** (2nd brain 철학)
  - **Auto-Hop 시스템**: 그래프 크기에 따라 자동 hop 조정 (20개 미만 → 5 hops, 200개 이상 → 1 hop)
  - **Topic 클러스터링 (1단계)**: 500개 노트 → 10-20개 클러스터로 축소
    - Topic과 연결된 노트들을 하나의 큰 원으로 묶음
    - 더블클릭으로 펼치기/접기
    - 시각적 복잡도 25-50배 감소
  - 🔄 **Sync All Notes**: Vault 전체 온톨로지 일괄 추출 (증분 동기화)
  - **향후 계획**: 2-3단계 계층 구조 (Domain → Topic → Note) - 1주일 사용 후 결정

- **Task Panel**: 자동 추출된 Task 관리
- **Weekly Review**: 잊힌 프로젝트, 새 토픽, 미완료 Task
- **💡 Insights Panel - 행동 중심 대시보드** (NEW):
  - **핵심 노트 발견**: PageRank 기반 중요 노트 자동 추천
  - **지식 클러스터 파악**: Community Detection으로 주제 그룹화
  - **고립된 노트 연결**: 연결 없는 노트 발견 → 즉시 연결 제안
  - **우선순위 Task**: 중요도 + 마감일 기반 집중 Task 추천
  - **놓친 연결 제안**: 같은 주제를 다루지만 연결 안 된 노트 쌍 제안
  - **약점 분석 & 보완 계획**: "가장 약한 링크" 발견 → 구체적 행동 제안

  **항상 "분석 → 행동"으로 이어짐**:
  - 고립 토픽 발견 → "이 3개 노트와 연결할까요?" 버튼
  - 미완료 Task 많음 → "이번 주 집중 Task로 이동" 버튼
  - 방치된 프로젝트 → "Review Note 생성" 버튼

### 4.3 AI 추천 엔진
- **벡터 유사도** 기반 연관 노트 추천
- **PageRank 알고리즘**으로 중요 노트 자동 발견
- **Community Detection**으로 지식 클러스터 파악
- **Task 우선순위** 자동 계산 (중요도 + 마감일 + 연결성)
- **놓친 연결** 제안 (같은 Topic 공유하지만 연결 안 된 노트)
- **약점 분석** 기반 보완 추천 (계획 중)

### 4.4 Automation Recipes (자동화 레시피)

**목적**: 반복적인 PKM 작업을 자동화하여 사용자가 "쓰기"에만 집중할 수 있도록 지원

#### 제공 레시피

| 레시피 | 트리거 | 자동 동작 |
|--------|--------|----------|
| **📌 Meeting → Task** | `#meeting` 태그 감지 | - Action Items 섹션에서 Task 자동 추출<br>- 참석자별로 Task 할당<br>- 프로젝트 노트에 자동 연결 |
| **💡 Idea → Project** | 아이디어 노트에 `#promote-to-project` 추가 | - Project Note 자동 생성<br>- Goal, Milestones 템플릿 삽입<br>- 관련 Reading Notes 자동 링크 |
| **📚 Reading → Concept** | 독서 노트 작성 완료 | - 핵심 개념 자동 추출<br>- 기존 Topic과 자동 병합/연결<br>- "이 개념 활용 가능 프로젝트" 제안 |
| **🗂️ Daily → Weekly** | 매주 일요일 밤 | - 이번 주 Daily Notes 요약<br>- Weekly Review Note 자동 생성<br>- 미완료 Task 목록 포함 |
| **🔗 Auto-Linking** | 새 노트 저장 시 | - 기존 노트에서 같은 키워드 감지<br>- 자동으로 `[[링크]]` 삽입 제안<br>- 사용자 승인 후 적용 |
| **🧹 Orphan Cleanup** | 매월 1일 | - 고립된 노트 목록 생성<br>- "이 노트들과 연결 제안" 레포트<br>- 1-click으로 연결 적용 |

#### 레시피 활성화 방법

```typescript
// 플러그인 설정에서 토글
settings: {
  automations: {
    meetingToTask: true,
    ideaToProject: false,  // 사용자 선택 비활성화
    autoLinking: true,
    weeklyReview: true
  }
}
```

#### 구현 우선순위 (Phase)

- **Phase 1 (MVP)**: Meeting → Task, Auto-Linking
- **Phase 2**: Idea → Project, Reading → Concept
- **Phase 3**: Daily → Weekly, Orphan Cleanup

---

## 5. 시스템 아키텍처

```
┌─────────────────┐
│ Obsidian Plugin │
└────────┬────────┘
         │ REST API
┌────────▼────────┐
│  FastAPI Server │
└────────┬────────┘
         │ Cypher
┌────────▼────────┐
│  Neo4j AuraDB   │
└─────────────────┘
         △
         │ LLM
    OpenAI GPT-4
```

---

## 5.5 Offline / Degraded Mode

**목적**: 백엔드·LLM 오류 시에도 사용자 신뢰 유지

### Fallback 전략

| 실패 케이스 | Degraded Mode 동작 |
|------------|-------------------|
| **LLM 실패** | 태그/링크 기반 추천으로 전환<br>UI 메시지: "AI 기능 일시 중단, 기본 추천 제공 중" |
| **Neo4j 연결 실패** | 로컬 Obsidian 그래프로 fallback<br>Context Panel: 로컬 백링크만 표시 |
| **백엔드 Timeout** | 로컬 캐시된 데이터 사용<br>UI 메시지: "오프라인 모드, 마지막 동기화: 2시간 전" |
| **API Rate Limit** | 요청 큐잉 + 사용자에게 우선순위 선택 제공 |

### 사용자 경험 원칙
- ❌ 기능 완전 차단 NO
- ✅ 축소된 기능이라도 계속 제공
- ✅ 명확한 상태 메시지
- ✅ 복구 시 자동 재동기화

---

## 5.6 AI Feedback Loop (학습하는 시스템)

**핵심**: 사용자 피드백을 LLM 프롬프트에 반영하여 **쓸수록 좋아지는** 개인화 엔진 구축

### Neo4j Feedback 노드 모델

```cypher
(:Feedback {
  id: "feedback_123",
  type: "accept" | "reject" | "merge",
  target_type: "Topic" | "Task" | "Link",
  target_value: "Machine Learning",
  reason: "too_generic",  // optional
  created_at: datetime(),
  user_id: "user_456"
})

// 연결 예시
(:Note)-[:HAS_FEEDBACK]->(:Feedback)
(:Topic {name: "ML"})-[:REJECTED_BY]->(:Feedback)
```

### Feedback 유형

1. **Accept**: 사용자가 AI 제안을 수락
   - Topic 병합 수락 → synonyms 목록에 추가
   - Link 제안 수락 → 강도(strength) 증가

2. **Reject**: 사용자가 AI 제안을 거부
   - Topic 추출 거부 → 해당 키워드에 penalty
   - 누적 3회 이상 거부 → LLM 프롬프트에 negative example 추가

3. **Merge**: 사용자가 중복 항목 병합
   - "Machine Learning" + "ML" → synonyms DB에 저장
   - 이후 자동으로 통합하여 추출

### 프롬프트 개선 파이프라인

```python
# 사용자 피드백 누적
rejected_topics = get_user_rejected_topics(user_id)
merged_synonyms = get_user_merged_synonyms(user_id)

# LLM 프롬프트에 반영
prompt = f"""
Extract topics from this note.

User preferences:
- Avoid these generic terms: {rejected_topics}
- Treat these as synonyms: {merged_synonyms}

Note content: ...
"""
```

### 효과
- 첫 주: 60% 정확도
- 1개월 후: 85% 정확도 (사용자별 개인화)
- 6개월 후: 95% 정확도 + 자동 제안 대부분 수락

---

## 6. 데이터 모델 (Neo4j)

### 주요 노드
- `(:User)` - 사용자
- `(:Vault)` - Obsidian vault
- `(:Note)` - 개별 노트
- `(:Topic)` - 추출된 주제/개념
- `(:Project)` - 프로젝트
- `(:Task)` - 할 일
- `(:Person)` - 인물

### 주요 관계
```cypher
(:User)-[:OWNS]->(:Vault)
(:Vault)-[:HAS_NOTE]->(:Note)
(:Note)-[:MENTIONS]->(:Topic)
(:Note)-[:RELATES_TO_PROJECT]->(:Project)
(:Note)-[:CONTAINS_TASK]->(:Task)
(:Topic)-[:BROADER|NARROWER|RELATED]->(:Topic)
```

---

## 7. API 엔드포인트

| 엔드포인트 | 메소드 | 설명 |
|-----------|--------|------|
| `/notes/sync` | POST | 노트 동기화 및 온톨로지 자동 재추출 |
| `/notes/list/{user_token}/{vault_id}` | GET | Vault의 모든 노트 목록 조회 |
| `/notes/context/{note_id}` | GET | 노트 컨텍스트 정보 조회 |
| `/notes/graph/{note_id}` | GET | 미니 그래프 데이터 조회 (vis-network 형식) |
| `/patterns/analyze/{user_token}/{vault_id}` | GET | **패턴 분석** (PageRank, Communities, Orphans) |
| `/patterns/recommendations/{user_token}/{vault_id}` | GET | **의사결정 추천** (Priority Tasks, Missing Connections) |
| `/review/weekly` | GET | 주간 리뷰 데이터 |
| `/tasks/update` | PUT | Task 상태 업데이트 |

---

## 8. LLM 파이프라인

### 입력
- 노트 본문, YAML metadata, 태그, 링크

### 출력 (JSON)
```json
{
  "topics": ["Raman scattering", "HeII line"],
  "projects": ["Symbiotic star monitoring"],
  "tasks": [
    {"title": "Analyze RR Tel spectra", "priority": "medium"}
  ],
  "persons": ["Prof. Smith"],
  "relations": [
    {"from": "Raman scattering", "to": "HeII line", "type": "related"}
  ]
}
```

---

## 9. 프라이버시 모드

| 모드 | 설명 | 정확도 |
|------|------|--------|
| 🔵 Full | 전체 본문 전송 | 최고 |
| 🟡 Summary | 요약만 전송 | 중간 |
| 🔴 Metadata | 제목/태그만 전송 | 낮음 |

---

## 10. 요금제 (Cursor 모델 참고)

### 🟢 Free
- 월 200회 온톨로지 분석
- 기본 그래프 뷰

### 🔵 Pro ($10/월)
- 월 3,000~5,000회 분석
- AI 크레딧 $3 포함
- Deep 분석 포함

### 🟣 Power ($25/월)
- AI 크레딧 $10
- 대규모 그래프 분석
- 우선 처리

---

## 11. 성능 요구사항

- **응답 속도**: Context API < 500ms, LLM 분석 < 1.2초
- **동시 사용자**: 200~500명 (1GB AuraDB 기준)
- **백엔드**: 2 vCPU / 4GB RAM (autoscaling)

---

## 12. 보안

- HTTPS 강제
- JWT 인증
- Vault별 데이터 격리
- 토큰 암호화 저장

---

## 13. MVP 로드맵 (3개월)

### 📌 Month 1
- [ ] FastAPI 백엔드 기본 구조
- [ ] Obsidian 플러그인 UI 골격
- [ ] Note Sync → DB 저장 파이프라인

### 📌 Month 2
- [ ] LLM 온톨로지 추출 파이프라인
- [ ] Neo4j 그래프 구축
- [ ] Context Panel 기능 완성
- [ ] Graph Panel 추가

### 📌 Month 3
- [ ] Task Panel
- [ ] Weekly Review
- [ ] 프라이버시 모드
- [ ] 베타 출시

---

## 14. 성공 지표 (KPI)

1. **사용자 참여도**
   - DAU (Daily Active Users)
   - 일일 노트 Sync 수

2. **AI 품질**
   - Topic 추출 정확도 > 85%
   - 추천 노트 클릭률 > 30%

3. **비즈니스**
   - Free → Pro 전환율 > 5%
   - 월 ARR 성장률

---

## 15. 배포/호스팅 전략 (MVP & 확장)

- **MVP 우선안: Render (US West)**  
  - Docker 기반 Web Service로 FastAPI 배포, `uvicorn app.main:app --host 0.0.0.0 --port $PORT`  
  - Neo4j Aura Free(Bolt+TLS) 외부 연동, 환경변수: `NEO4J_URI/USER/PASSWORD`, `OPENAI_API_KEY`, `API_ENDPOINT`, `VAULT_ID`, `USER_TOKEN`, 필요 시 `CORS_ORIGINS`  
  - 헬스체크 `/api/v1/health`, 무료 플랜 슬립 이슈는 유료로 완화

- **확장안: Fly.io (멀티 리전/프라이빗 네트워크)**  
  - WireGuard 기반 프라이빗 네트워크로 Neo4j/Aura와 저지연/보안 통신  
  - 멀티 리전 배포 및 퍼시스턴트 볼륨 지원, 초기 설정은 Render보다 다소 손이 감  
  - 리전 최적화/레이턴시 중요 시 전환 고려

---

## 16. Palantir Ontology 비교 & 개선 로드맵

### 16.1 현재 구현 vs Palantir Ontology

| 측면 | Palantir Foundry | Didymos (현재) | 개선 방향 |
|------|------------------|----------------|-----------|
| **Object Types** | 명시적 정의, 재사용 가능 | LLM 자동 추출 | → 타입 스키마 정의 추가 |
| **Properties** | 강타입, 검증 강제 | 자유 형식 JSON | → Property 타입 시스템 |
| **Links** | 양방향, 타입 명시 | 단방향, 자동 생성 | → 양방향 Link + 타입 검증 |
| **Actions** | 워크플로우, 함수 | 없음 | → 노트 액션 (merge, archive 등) |
| **Versioning** | 전체 이력 추적 | created/updated만 | → 변경 이력 추적 |
| **Permissions** | 세밀한 권한 제어 | 없음 | → Vault 레벨 권한 (미래) |
| **Hierarchy** | 3단계 계층 (Domain → Topic → Object) | **1단계 클러스터링 (Topic → Notes)** | → 2-3단계 계층 (사용자 피드백 후) |

### 16.2 Palantir 방식 도입 계획 (Phase 2)

#### Object Type 시스템
```python
# 엄격한 타입 정의
class ObjectType:
    name: str
    properties: List[PropertyDefinition]
    allowed_links: List[LinkDefinition]
    actions: List[ActionDefinition]

# 예시: Person Object Type
PersonType = ObjectType(
    name="Person",
    properties=[
        Property("name", type="string", required=True),
        Property("email", type="email", required=False),
        Property("affiliation", type="string")
    ],
    allowed_links=[
        Link("worksOn", target="Project", bidirectional=True),
        Link("collaboratesWith", target="Person", bidirectional=True)
    ],
    actions=[
        Action("sendEmail"),
        Action("addToProject")
    ]
)
```

#### Link 타입 시스템
```cypher
// 현재: 단방향, 타입 없음
(:Note)-[:MENTIONS]->(:Topic)

// 개선: 양방향, 타입 + 속성
(:Note)-[:MENTIONS {
  strength: 0.85,
  context: "introduction",
  created_at: datetime()
}]->(:Topic)
(:Topic)-[:MENTIONED_IN]->(:Note)
```

#### Action 시스템
```typescript
// 노트 액션 예시
class NoteActions {
  archiveNote(note: Note) {
    note.status = "archived";
    note.archivedAt = new Date();
    // 관련 Task들도 자동 아카이브
  }

  mergeNotes(note1: Note, note2: Note) {
    // 온톨로지 병합, 중복 제거
    // 관계 재설정
  }

  suggestLinks(note: Note): Link[] {
    // AI 기반 연결 제안
  }
}
```

### 16.3 개선 우선순위 (Post-MVP)

**현재 상태 (2025-12-01)**:
- ✅ **1단계 Topic 클러스터링 구현 완료**
  - 500개 노트 → 10-20개 클러스터로 시각적 복잡도 25-50배 감소
  - vis-network cluster API 활용
  - 더블클릭으로 expand/collapse
  - **결정 보류**: 1주일 실사용 후 2-3단계 계층 필요성 평가

1. **Phase 11 (조건부)**: 계층적 클러스터링
   - **조건**: 1주일 사용 후 현재 구조로 불편함 발견 시
   - Domain → Topic → Note 3단계 구조
   - 백엔드: hierarchy level 메타데이터 추가
   - 프론트엔드: nested clustering 구현
   - **판단 기준**: Premature optimization 회피

2. **Phase 2.1**: Object Type 시스템 도입
   - Note, Topic, Project, Task 타입 스키마 정의
   - Property 타입 검증
   - 마이그레이션 도구

3. **Phase 2.2**: Link 타입 시스템
   - 양방향 링크 자동 생성
   - Link 메타데이터 (strength, context 등)
   - Link 타입별 제약 조건

4. **Phase 2.3**: Action 시스템
   - 노트 워크플로우 (merge, archive, split)
   - 자동화 트리거 (조건 기반 액션)
   - 사용자 정의 액션

5. **Phase 2.4**: Versioning
   - 노드/관계 변경 이력 추적
   - 시간 여행 쿼리 (특정 시점 상태)
   - 변경 비교 및 롤백

---

## 17. 약점 분석 기반 추천 (계획 중)

### 17.1 "Weakest Link" 원칙
사용자의 지식 그래프에서 가장 약한 부분을 찾아 보완하도록 유도

### 17.2 약점 탐지 알고리즘
```python
def analyze_weaknesses(user_id, vault_id):
    return {
        "isolated_topics": find_isolated_topics(),      # 고립된 주제
        "stale_projects": find_stale_projects(),        # 30일+ 업데이트 없음
        "chronic_overdue": find_chronic_tasks(),        # 반복 미루기 Task
        "weak_clusters": find_sparse_areas(),           # 연결 희박한 영역
        "knowledge_gaps": detect_missing_coverage()     # 지식 공백
    }
```

### 17.3 보완 추천 예시
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
- "Weekly Review Process" (similar topic, not connected)
- "PARA Method" (related methodology)
```

---

## 부록: 프롬프트 템플릿 예시

```
You are an ontology extractor for personal knowledge management.
From the note below, extract:

1. Topics (conceptual nouns)
2. Projects (ongoing work)
3. Tasks (action items)
4. Persons (names)
5. Relations between Topics:
   - broader
   - narrower
   - related

Output JSON only.

Note content:
{{content}}
YAML:
{{yaml}}
Tags:
{{tags}}
Links:
{{links}}
```
