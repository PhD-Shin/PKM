# Phase 13: SKOS 온톨로지 자동 생성 (MVP 핵심)

**완료일**: 2025-12-02
**목표**: InfraNodus 대비 핵심 차별점 완성

---

## 핵심 차별점

| 제품 | 접근 방식 | 결과 |
|------|----------|------|
| **InfraNodus** | 단어 동시출현 | 평면적 네트워크 |
| **Didymos without SKOS** | 개념 추출 | 여전히 평면적 |
| **Didymos with SKOS** | 개념 + 계층 구조 | 진정한 온톨로지 ✅ |

---

## SKOS 관계 타입

### BROADER (하위 → 상위)

하위 개념에서 상위 개념으로의 관계

```
Machine Learning -[BROADER]-> AI
Deep Learning -[BROADER]-> Machine Learning
```

### NARROWER (상위 → 하위)

상위 개념에서 하위 개념으로의 관계

```
AI -[NARROWER]-> Machine Learning
Machine Learning -[NARROWER]-> Deep Learning
```

### RELATED_TO (연관)

계층 관계가 아닌 단순 연관 관계

```
Machine Learning <-[RELATED_TO]-> Statistics
NLP <-[RELATED_TO]-> Linguistics
```

---

## 구현 상세

### LLM 프롬프트 수정

**파일**: `ontology_service.py`

```python
EXTRACTION_PROMPT = """
Extract entities and their relationships from the note.

Relationship types:
- BROADER: Concept A is more specific than B (A -[BROADER]-> B)
  Example: "Machine Learning" -[BROADER]-> "AI"

- NARROWER: Concept A is more general than B (A -[NARROWER]-> B)
  Example: "AI" -[NARROWER]-> "Machine Learning"

- RELATED_TO: Concepts are related but not hierarchically
  Example: "Machine Learning" -[RELATED_TO]-> "Statistics"

Guidelines:
1. Detect hierarchical relationships (is-a, part-of, subcategory)
2. Use BROADER for "is a type of", "is a subcategory of"
3. Use RELATED_TO only when no clear hierarchy exists
4. Avoid duplicate edges (don't create both RELATED_TO and BROADER)
"""
```

### allowed_relationships 확장

**기존**:
- MENTIONS
- RELATED_TO
- PART_OF
- ASSIGNED_TO
- HAS_TASK

**추가**:
- **BROADER** (SKOS 상위 관계)
- **NARROWER** (SKOS 하위 관계)

### SKOS 양방향성 보장

**함수**: `_ensure_skos_inverse()`

A-[BROADER]->B 생성 시 자동으로 B-[NARROWER]->A 생성

```python
def _ensure_skos_inverse(tx, source_id: str, target_id: str, rel_type: str):
    """SKOS 관계의 역방향 자동 생성"""
    if rel_type == "BROADER":
        # A -[BROADER]-> B 이면 B -[NARROWER]-> A 생성
        tx.run("""
            MATCH (a:Entity {id: $source}), (b:Entity {id: $target})
            MERGE (b)-[:NARROWER]->(a)
        """, source=source_id, target=target_id)
    elif rel_type == "NARROWER":
        # A -[NARROWER]-> B 이면 B -[BROADER]-> A 생성
        tx.run("""
            MATCH (a:Entity {id: $source}), (b:Entity {id: $target})
            MERGE (b)-[:BROADER]->(a)
        """, source=source_id, target=target_id)
```

### 맥락 중심 추출 프롬프트

**개선 사항**:
- 계층 탐지 가이드라인 추가
- 중복 엣지 방지 (RELATED_TO vs BROADER 구분)
- 노트의 핵심 개념만 추출 (고립 엔티티 필터링)

---

## 예시 결과

### 입력 노트

```markdown
# Transformer Architecture

Transformer is a deep learning model introduced in "Attention is All You Need".
It's the foundation of BERT, GPT, and other LLMs.
```

### 추출된 온톨로지

```
Transformer -[BROADER]-> Deep Learning
Transformer -[BROADER]-> Neural Network
BERT -[BROADER]-> Transformer
GPT -[BROADER]-> Transformer
Transformer -[RELATED_TO]-> Attention Mechanism
```

### 계층 구조

```
AI
└── Deep Learning
    └── Neural Network
        └── Transformer
            ├── BERT
            └── GPT
```

---

## 체크리스트

- [x] LLM 프롬프트 수정
- [x] allowed_relationships에 BROADER/NARROWER 추가
- [x] SKOS 양방향성 보장 (`_ensure_skos_inverse()`)
- [x] 맥락 중심 추출 프롬프트
- [x] 중복 엣지 방지 로직
