"""
Hybrid Graphiti + PKM Ontology Service

Graphiti의 Entity에 PKM 온톨로지 레이블(Topic, Project, Task, Person)을
추가하여 두 시스템의 장점을 결합:

- Graphiti: Temporal KG, 자동 엔티티 요약, 하이브리드 검색
- PKM Ontology: 우리 cluster_service와 호환되는 레이블

Flow:
1. Graphiti가 노트를 처리 → Entity 생성 (Episodic -> Entity MENTIONS)
2. 후처리로 Entity에 PKM 레이블 추가 (LLM 분류)
3. Note → Entity MENTIONS 관계 생성 (Episodic의 name에서 note_id 추출)
4. cluster_service가 PKM 레이블로 클러스터링

Note: Graphiti uses 'Entity' and 'Episodic' labels (NOT 'EntityNode' or 'EpisodicNode')
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio

from app.db.neo4j import get_neo4j_client
from app.config import settings

logger = logging.getLogger(__name__)

# PKM Core Ontology v2 타입 (8개)
# - Goal: 최상위 목표 (OKR의 O)
# - Project: Goal을 달성하기 위한 중간 단위
# - Task: 실행 가능한 최소 단위
# - Topic: 주제/개념 카테고리
# - Concept: 구체적 개념/용어 (Topic의 하위)
# - Question: 연구 질문 또는 미해결 의문
# - Insight: 발견/통찰/결론
# - Resource: 외부 자료 참조 (논문, 책, URL)
PKM_TYPES = ["Goal", "Project", "Task", "Topic", "Concept", "Question", "Insight", "Resource"]

# 하위 호환성을 위해 Person도 지원 (기존 데이터)
PKM_TYPES_LEGACY = ["Person"]

# 엔티티 이름 최소 길이 (너무 짧은 이름 제외)
MIN_ENTITY_NAME_LENGTH = 2
MAX_ENTITY_NAME_LENGTH = 100


def is_valid_entity(name: str) -> bool:
    """
    엔티티 이름의 기본 유효성 검사 (최소한의 필터링만)

    블랙리스트는 사용하지 않음 - 모든 명사가 문맥에 따라 유용할 수 있음
    대신 min_connections 필터로 시각화 단계에서 필터링

    Returns:
        True if entity name is valid
    """
    if not name:
        return False

    name_stripped = name.strip()

    # 길이 체크
    if len(name_stripped) < MIN_ENTITY_NAME_LENGTH:
        return False
    if len(name_stripped) > MAX_ENTITY_NAME_LENGTH:
        return False

    # 숫자만으로 이루어진 경우 제외 (예: "123", "2024")
    if name_stripped.isdigit():
        return False

    # 특수문자만으로 이루어진 경우 제외
    if not any(c.isalnum() for c in name_stripped):
        return False

    return True


# 엔티티 이름 기반 분류 규칙 (LLM 호출 없이 빠른 분류)
# PKM Core Ontology v2 - 8개 타입 분류
CLASSIFICATION_RULES = {
    "Goal": [
        # 최상위 목표 (OKR의 O)
        lambda name: any(kw in name.lower() for kw in ["목표", "goal", "objective", "vision", "미션", "mission"]),
        lambda name: any(kw in name for kw in ["완성", "달성", "성취"]),
    ],
    "Project": [
        # Goal을 달성하기 위한 중간 단위
        lambda name: any(kw in name.lower() for kw in ["프로젝트", "project", "개발", "구현", "시스템", "chapter", "phase"]),
        lambda name: name.startswith(("PKM", "Didymos", "MVP")),
    ],
    "Task": [
        # 실행 가능한 최소 단위
        lambda name: any(kw in name.lower() for kw in ["todo", "task", "작업", "할일", "수정", "추가", "구현해야", "작성", "검토"]),
        lambda name: name.startswith(("[ ]", "[x]", "TODO", "FIXME")),
    ],
    "Question": [
        # 연구 질문 또는 미해결 의문
        lambda name: name.endswith("?"),
        lambda name: any(kw in name.lower() for kw in ["질문", "question", "의문", "궁금", "어떻게", "왜", "무엇"]),
        lambda name: name.startswith(("RQ", "Q:", "Q.")),
    ],
    "Insight": [
        # 발견/통찰/결론
        lambda name: any(kw in name.lower() for kw in ["인사이트", "insight", "발견", "결론", "conclusion", "finding", "배움", "깨달음"]),
        lambda name: name.startswith(("💡", "✨", "Insight:", "Finding:")),
    ],
    "Resource": [
        # 외부 자료 참조 (논문, 책, URL)
        lambda name: any(kw in name.lower() for kw in ["논문", "paper", "책", "book", "article", "url", "링크", "참고", "reference"]),
        lambda name: name.startswith(("http", "www.", "📚", "📄")),
        lambda name: any(ext in name.lower() for ext in [".pdf", ".epub", "arxiv", "doi:"]),
    ],
    "Concept": [
        # 구체적 개념/용어 (Topic의 하위)
        # 특정 기술 용어, 방법론, 알고리즘 등
        lambda name: any(kw in name.lower() for kw in [
            "algorithm", "알고리즘", "method", "방법", "technique", "기법",
            "architecture", "아키텍처", "pattern", "패턴", "model", "모델",
            "framework", "프레임워크", "protocol", "프로토콜"
        ]),
        # 대문자로 시작하는 기술 용어 (예: Transformer, BERT, GPT)
        lambda name: len(name) > 2 and name[0].isupper() and any(c.isupper() for c in name[1:]),
    ],
    # Topic은 기본값 (다른 타입에 해당하지 않으면 Topic)
    # 기존 Person 지원 (하위 호환성)
    "Person": [
        lambda name: any(suffix in name for suffix in ["님", "씨", "교수", "박사", "선생"]),
        lambda name: name.endswith(("수", "호", "민", "준", "진", "현", "석", "영", "훈")),
    ],
}


def classify_entity_to_pkm_type(entity_name: str, entity_summary: str = None) -> str:
    """
    엔티티 이름/요약을 기반으로 PKM 타입 분류 (Core Ontology v2)

    분류 전략:
    1. 이름 기반 규칙 (가장 확실한 경우)
    2. 요약 기반 의미 분석 (Graphiti가 생성한 요약 활용)
    3. 이름 패턴 분석 (대문자, 특수 형식 등)
    4. 기본값: Topic

    Args:
        entity_name: 엔티티 이름
        entity_summary: Graphiti가 생성한 엔티티 요약

    Returns:
        PKM 타입 (Goal, Project, Task, Topic, Concept, Question, Insight, Resource)
    """
    name_lower = entity_name.lower()

    # Step 1: 이름 기반 규칙 (우선순위 순서대로 체크)
    # 순서: Goal > Question > Insight > Resource > Task > Project > Concept > Person > Topic
    priority_order = ["Goal", "Question", "Insight", "Resource", "Task", "Project", "Concept", "Person"]

    for pkm_type in priority_order:
        if pkm_type in CLASSIFICATION_RULES:
            for rule in CLASSIFICATION_RULES[pkm_type]:
                try:
                    if rule(entity_name):
                        return pkm_type
                except Exception:
                    continue

    # Step 2: 요약 기반 의미 분석 (확장된 키워드)
    if entity_summary:
        summary_lower = entity_summary.lower()

        # Goal 패턴 - 장기 목표, 비전, 방향
        goal_keywords = [
            "목표", "goal", "objective", "vision", "장기 계획", "미션", "mission",
            "달성하고자", "이루고자", "위해", "지향", "추구", "지향점", "방향성",
            "궁극적", "최종", "비전", "전략적 목표", "okr"
        ]
        if any(kw in summary_lower for kw in goal_keywords):
            return "Goal"

        # Question 패턴 - 질문, 의문, 탐구할 것
        question_keywords = [
            "질문", "question", "의문", "연구 문제", "탐구", "알아보",
            "궁금", "조사", "research question", "rq", "어떻게", "왜",
            "무엇인지", "확인 필요", "검토 필요", "파악 필요", "알아야"
        ]
        if any(kw in summary_lower for kw in question_keywords):
            return "Question"

        # Insight 패턴 - 발견, 깨달음, 결론
        insight_keywords = [
            "발견", "insight", "결론", "깨달음", "배움", "통찰", "이해",
            "알게 됨", "파악됨", "확인됨", "깨닫", "인사이트", "교훈",
            "핵심", "중요한 점", "시사점", "함의", "의미하는", "learned"
        ]
        if any(kw in summary_lower for kw in insight_keywords):
            return "Insight"

        # Resource 패턴 - 외부 자료, 참고 문헌
        resource_keywords = [
            "논문", "paper", "책", "book", "참고 자료", "출처", "링크",
            "article", "reference", "문헌", "자료", "source", "문서",
            "저널", "journal", "arxiv", "doi", "isbn", "url", "웹사이트",
            "블로그", "강의", "lecture", "course", "tutorial", "가이드"
        ]
        if any(kw in summary_lower for kw in resource_keywords):
            return "Resource"

        # Task 패턴 - 실행 가능한 할일
        task_keywords = [
            "해야 할", "완료해야", "task", "todo", "작업", "실행",
            "처리", "수행", "진행해야", "체크", "확인해야", "작성해야",
            "구현해야", "수정해야", "추가해야", "삭제해야", "변경해야",
            "action item", "next step", "할 일"
        ]
        if any(kw in summary_lower for kw in task_keywords):
            return "Task"

        # Project 패턴 - 중간 단위 프로젝트
        project_keywords = [
            "프로젝트", "project", "개발 중", "구현", "진행 중", "계획",
            "시스템", "플랫폼", "서비스", "앱", "애플리케이션", "모듈",
            "컴포넌트", "feature", "기능 개발", "스프린트", "마일스톤",
            "phase", "단계", "initiative", "워크스트림"
        ]
        if any(kw in summary_lower for kw in project_keywords):
            return "Project"

        # Concept 패턴 - 기술 개념, 방법론, 알고리즘
        concept_keywords = [
            "개념", "concept", "방법", "method", "기법", "알고리즘",
            "기술", "아키텍처", "architecture", "패턴", "pattern",
            "프레임워크", "framework", "프로토콜", "protocol", "모델",
            "이론", "theory", "원리", "principle", "법칙", "정의",
            "용어", "terminology", "접근법", "approach", "전략",
            "테크닉", "technique", "메서드", "스키마", "구조"
        ]
        if any(kw in summary_lower for kw in concept_keywords):
            return "Concept"

        # Person 패턴 (하위 호환성)
        person_keywords = [
            "사람", "person", "연구원", "학생", "팀원", "저자",
            "동료", "교수", "박사", "researcher", "author", "colleague",
            "개발자", "developer", "엔지니어", "engineer", "디자이너"
        ]
        if any(kw in summary_lower for kw in person_keywords):
            return "Person"

    # Step 3: 이름 패턴 분석 (규칙에서 못 잡은 케이스)

    # 대문자 약어는 Concept 가능성 높음 (API, SDK, LLM, GPT 등)
    if entity_name.isupper() and len(entity_name) <= 6:
        return "Concept"

    # CamelCase 기술 용어는 Concept (GraphQL, TypeScript 등)
    if len(entity_name) > 3 and entity_name[0].isupper() and any(c.isupper() for c in entity_name[1:]) and not entity_name.isupper():
        return "Concept"

    # "-ing" 또는 "-tion" 으로 끝나는 영어 단어는 Concept 가능성
    if entity_name.endswith(("ing", "tion", "ment", "ness", "ity")):
        return "Concept"

    # 기본값: Topic (주제 카테고리)
    return "Topic"


async def add_pkm_labels_to_graphiti_entities(
    vault_id: str = None,
    batch_size: int = 100
) -> Dict[str, Any]:
    """
    기존 Graphiti EntityNode에 PKM 레이블 추가

    이미 레이블이 있는 엔티티는 스킵

    Args:
        vault_id: 특정 vault만 처리 (None이면 전체)
        batch_size: 한 번에 처리할 엔티티 수

    Returns:
        처리 결과 통계
    """
    client = get_neo4j_client()

    try:
        # Step 1: PKM 레이블이 없는 Entity 조회 (Core Ontology v2 - 8개 타입)
        cypher_find = """
        MATCH (e:Entity)
        WHERE NOT e:Goal AND NOT e:Project AND NOT e:Task AND NOT e:Topic
          AND NOT e:Concept AND NOT e:Question AND NOT e:Insight AND NOT e:Resource
          AND NOT e:Person
        RETURN e.uuid as uuid, e.name as name, e.summary as summary
        LIMIT $batch_size
        """

        entities = client.query(cypher_find, {"batch_size": batch_size})

        if not entities:
            logger.info("No Entity without PKM labels found")
            return {
                "status": "completed",
                "processed": 0,
                "message": "All Entities already have PKM labels"
            }

        logger.info(f"Found {len(entities)} Entities to classify")

        # Step 2: 각 엔티티 분류 및 레이블 추가 (Core Ontology v2 - 8개 타입 + Person)
        stats = {
            "Goal": 0, "Project": 0, "Task": 0, "Topic": 0,
            "Concept": 0, "Question": 0, "Insight": 0, "Resource": 0,
            "Person": 0, "errors": 0
        }

        for entity in entities:
            try:
                uuid = entity["uuid"]
                name = entity["name"] or uuid
                summary = entity.get("summary", "")

                # PKM 타입 분류
                pkm_type = classify_entity_to_pkm_type(name, summary)

                # 레이블 추가
                cypher_add_label = f"""
                MATCH (e:Entity {{uuid: $uuid}})
                SET e:{pkm_type}
                SET e.pkm_type = $pkm_type
                SET e.pkm_classified_at = datetime()
                RETURN e.name as name
                """

                result = client.query(cypher_add_label, {"uuid": uuid, "pkm_type": pkm_type})

                if result:
                    stats[pkm_type] += 1
                    logger.debug(f"Added {pkm_type} label to: {name}")

            except Exception as e:
                logger.error(f"Error adding label to {entity.get('name')}: {e}")
                stats["errors"] += 1

        # Core Ontology v2 - 8개 타입 + Person
        all_types = PKM_TYPES + PKM_TYPES_LEGACY
        total_processed = sum(stats.get(t, 0) for t in all_types)
        logger.info(f"✅ PKM labels added: {stats}")

        return {
            "status": "success",
            "processed": total_processed,
            "stats": stats,
            "remaining": await _count_unlabeled_entities(client)
        }

    except Exception as e:
        logger.error(f"Error in add_pkm_labels_to_graphiti_entities: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


async def _count_unlabeled_entities(client) -> int:
    """PKM 레이블이 없는 Entity 수 조회 (Core Ontology v2 - 8개 타입)"""
    try:
        result = client.query("""
            MATCH (e:Entity)
            WHERE NOT e:Goal AND NOT e:Project AND NOT e:Task AND NOT e:Topic
              AND NOT e:Concept AND NOT e:Question AND NOT e:Insight AND NOT e:Resource
              AND NOT e:Person
            RETURN count(e) as count
        """, {})
        return result[0]["count"] if result else 0
    except Exception:
        return -1


async def create_mentions_from_episodes(
    vault_id: str = None,
    batch_size: int = 100
) -> Dict[str, Any]:
    """
    Graphiti Episodic-Entity 관계를 Note-Entity MENTIONS 관계로 변환

    Graphiti는 Episodic → Entity MENTIONS 관계를 사용
    cluster_service는 Note → Entity MENTIONS 관계를 기대

    이 함수는 Episodic의 name에서 note_id를 추출하여 (name = 'note_{note_id}')
    Note → Entity MENTIONS 관계를 생성

    Args:
        vault_id: 특정 vault만 처리
        batch_size: 한 번에 처리할 관계 수

    Returns:
        처리 결과 통계
    """
    client = get_neo4j_client()

    try:
        # Step 1: Episodic-Entity 관계에서 Note-Entity MENTIONS가 없는 것 찾기
        # Graphiti의 Episodic.name = 'note_{note_id}' 형태
        # Note.note_id = '{path}' 형태
        cypher_find = """
        MATCH (ep:Episodic)-[:MENTIONS]->(e:Entity)
        WHERE ep.name STARTS WITH 'note_'
        WITH ep, e,
             replace(ep.name, 'note_', '') as note_id
        MATCH (n:Note {note_id: note_id})
        WHERE NOT (n)-[:MENTIONS]->(e)
        RETURN n.note_id as note_id, e.uuid as entity_uuid, e.name as entity_name
        LIMIT $batch_size
        """

        relations = client.query(cypher_find, {"batch_size": batch_size})

        if not relations:
            logger.info("No new MENTIONS relationships to create")
            return {
                "status": "completed",
                "created": 0,
                "message": "All Episodic-Entity relations already have Note MENTIONS"
            }

        logger.info(f"Found {len(relations)} MENTIONS relationships to create")

        # Step 2: MENTIONS 관계 생성
        created = 0
        errors = 0

        for rel in relations:
            try:
                cypher_create = """
                MATCH (n:Note {note_id: $note_id})
                MATCH (e:Entity {uuid: $entity_uuid})
                MERGE (n)-[m:MENTIONS]->(e)
                SET m.created_at = datetime()
                SET m.source = 'graphiti_migration'
                RETURN count(m) as count
                """

                result = client.query(cypher_create, {
                    "note_id": rel["note_id"],
                    "entity_uuid": rel["entity_uuid"]
                })

                if result and result[0]["count"] > 0:
                    created += 1

            except Exception as e:
                logger.error(f"Error creating MENTIONS: {e}")
                errors += 1

        logger.info(f"✅ Created {created} MENTIONS relationships")

        return {
            "status": "success",
            "created": created,
            "errors": errors
        }

    except Exception as e:
        logger.error(f"Error in create_mentions_from_episodes: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


async def migrate_graphiti_to_hybrid(
    vault_id: str = None,
    max_iterations: int = 10
) -> Dict[str, Any]:
    """
    전체 마이그레이션: Graphiti 스키마 → 하이브리드 스키마

    1. EntityNode에 PKM 레이블 추가
    2. Episode-Entity → Note-Entity MENTIONS 관계 생성

    Args:
        vault_id: 특정 vault만 처리
        max_iterations: 최대 반복 횟수 (배치 처리)

    Returns:
        전체 마이그레이션 결과
    """
    logger.info(f"🚀 Starting Graphiti → Hybrid migration (vault: {vault_id or 'all'})")

    results = {
        "pkm_labels": {"total_processed": 0, "stats": {}},
        "mentions": {"total_created": 0},
        "iterations": 0
    }

    for i in range(max_iterations):
        results["iterations"] = i + 1

        # Step 1: PKM 레이블 추가
        label_result = await add_pkm_labels_to_graphiti_entities(vault_id)

        if label_result.get("processed", 0) > 0:
            results["pkm_labels"]["total_processed"] += label_result["processed"]
            # Core Ontology v2 - 8개 타입 + Person
            all_types = PKM_TYPES + PKM_TYPES_LEGACY
            for pkm_type in all_types:
                prev = results["pkm_labels"]["stats"].get(pkm_type, 0)
                results["pkm_labels"]["stats"][pkm_type] = prev + label_result.get("stats", {}).get(pkm_type, 0)

        # Step 2: MENTIONS 관계 생성
        mentions_result = await create_mentions_from_episodes(vault_id)

        if mentions_result.get("created", 0) > 0:
            results["mentions"]["total_created"] += mentions_result["created"]

        # 더 이상 처리할 것이 없으면 종료
        if label_result.get("processed", 0) == 0 and mentions_result.get("created", 0) == 0:
            logger.info(f"Migration completed after {i + 1} iterations")
            break

        # Rate limiting
        await asyncio.sleep(0.5)

    logger.info(f"✅ Migration complete: {results}")
    return results


async def process_note_hybrid(
    note_id: str,
    content: str,
    updated_at: datetime = None,
    metadata: dict = None
) -> Dict[str, Any]:
    """
    하이브리드 방식으로 노트 처리

    1. Graphiti로 엔티티 추출 (temporal, 자동 요약)
    2. 추출된 EntityNode에 PKM 레이블 추가
    3. Note → EntityNode MENTIONS 관계 생성

    Args:
        note_id: 노트 ID
        content: 노트 내용
        updated_at: 수정 시간
        metadata: 추가 메타데이터

    Returns:
        처리 결과
    """
    from app.services.graphiti_service import async_process_note

    try:
        # Step 1: Graphiti로 처리
        graphiti_result = await async_process_note(
            note_id=note_id,
            content=content,
            updated_at=updated_at,
            metadata=metadata
        )

        if graphiti_result.get("status") != "success":
            return graphiti_result

        nodes_extracted = graphiti_result.get("nodes_extracted", 0)

        if nodes_extracted == 0:
            return graphiti_result

        # Step 2: 추출된 Entity에 PKM 레이블 추가
        client = get_neo4j_client()

        # 이 노트와 연결된 Entity 찾기 (Graphiti uses 'Episodic' and 'Entity' labels)
        cypher_find_entities = """
        MATCH (ep:Episodic)-[:MENTIONS]->(e:Entity)
        WHERE ep.name = $episode_name
          AND NOT e:Topic AND NOT e:Project AND NOT e:Task AND NOT e:Person
        RETURN e.uuid as uuid, e.name as name, e.summary as summary
        """

        episode_name = f"note_{note_id}"
        entities = client.query(cypher_find_entities, {"episode_name": episode_name})

        labeled_count = 0

        for entity in (entities or []):
            entity_name = entity["name"] or entity["uuid"]

            # 기본 유효성 검사만 수행 (너무 짧거나 숫자만인 경우만 제외)
            # 블랙리스트는 사용하지 않음 - min_connections 필터로 시각화 단계에서 처리
            if not is_valid_entity(entity_name):
                logger.debug(f"⏩ Skipping invalid entity: {entity_name}")
                continue

            pkm_type = classify_entity_to_pkm_type(
                entity_name,
                entity.get("summary", "")
            )

            cypher_add_label = f"""
            MATCH (e:Entity {{uuid: $uuid}})
            SET e:{pkm_type}
            SET e.pkm_type = $pkm_type
            SET e.pkm_classified_at = datetime()
            """

            client.query(cypher_add_label, {"uuid": entity["uuid"], "pkm_type": pkm_type})
            labeled_count += 1

        # Step 3: Note → Entity MENTIONS 관계 생성 (유효한 엔티티만)
        cypher_create_mentions = """
        MATCH (n:Note {note_id: $note_id})
        MATCH (ep:Episodic {name: $episode_name})-[:MENTIONS]->(e:Entity)
        WHERE NOT (n)-[:MENTIONS]->(e)
        MERGE (n)-[m:MENTIONS]->(e)
        SET m.created_at = datetime()
        SET m.source = 'graphiti_hybrid'
        RETURN count(m) as count
        """

        mentions_result = client.query(cypher_create_mentions, {
            "note_id": note_id,
            "episode_name": episode_name
        })

        mentions_created = mentions_result[0]["count"] if mentions_result else 0

        return {
            **graphiti_result,
            "pkm_labels_added": labeled_count,
            "mentions_created": mentions_created,
            "hybrid_mode": True
        }

    except Exception as e:
        logger.error(f"Error in hybrid processing for {note_id}: {e}")
        return {
            "status": "error",
            "note_id": note_id,
            "error": str(e)
        }


# Sync wrapper for compatibility
def process_note_to_graph_hybrid(note_id: str, content: str, metadata: dict = None) -> int:
    """
    동기 래퍼: 기존 ontology_service와 호환
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    process_note_hybrid(note_id, content, metadata=metadata)
                )
                result = future.result()
        else:
            result = loop.run_until_complete(
                process_note_hybrid(note_id, content, metadata=metadata)
            )

        return result.get("nodes_extracted", 0)

    except RuntimeError:
        result = asyncio.run(process_note_hybrid(note_id, content, metadata=metadata))
        return result.get("nodes_extracted", 0)
