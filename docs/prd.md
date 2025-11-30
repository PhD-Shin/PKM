# 📘 Didymos - PRD (Product Requirement Document)

> 온톨로지 기반 개인 지식 그래프 + AI 생산성 엔진

---

## 1. 제품 개요

### 1.1 핵심 가치
**Didymos**는 Obsidian 노트를 기반으로 자동으로 지식 그래프를 구축하고, AI가 노트 간 연결을 발견하여 생산성을 극대화하는 시스템입니다.

### 1.2 기술 스택
- **백엔드**: FastAPI + Neo4j AuraDB + OpenAI
- **프론트엔드**: Obsidian 플러그인 (TypeScript)
- **AI**: neo4j-genai + GPT-4

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

## 4. 핵심 기능 (MVP)

### 4.1 자동 온톨로지 구축
- 노트에서 **Topic, Project, Task, Person** 자동 추출
- 엔티티 간 관계 자동 생성 (BROADER/NARROWER/RELATED)
- Neo4j 그래프 DB에 실시간 업데이트

### 4.2 Obsidian 플러그인
- **Context Panel**: 현재 노트 관련 Topics, Projects, Tasks, 연관 노트
- **Graph Panel**: 1-2 hop 미니 그래프 시각화
- **Task Panel**: 자동 추출된 Task 관리
- **Weekly Review**: 잊힌 프로젝트, 새 토픽, 미완료 Task

### 4.3 AI 추천 엔진
- 토픽 유사도 기반 연관 노트 추천
- 잊힌 프로젝트 리마인드
- Task 우선순위 자동 분석

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
| `/notes/sync` | POST | 노트 동기화 및 온톨로지 업데이트 |
| `/notes/context/{note_id}` | GET | 노트 컨텍스트 정보 조회 |
| `/notes/graph/{note_id}` | GET | 미니 그래프 데이터 조회 |
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
