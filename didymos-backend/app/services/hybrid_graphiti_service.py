"""
Hybrid Graphiti + PKM Ontology Service

Graphiti의 EntityNode에 PKM 온톨로지 레이블(Topic, Project, Task, Person)을
추가하여 두 시스템의 장점을 결합:

- Graphiti: Temporal KG, 자동 엔티티 요약, 하이브리드 검색
- PKM Ontology: 우리 cluster_service와 호환되는 레이블

Flow:
1. Graphiti가 노트를 처리 → EntityNode 생성
2. 후처리로 EntityNode에 PKM 레이블 추가 (LLM 분류)
3. Note → EntityNode MENTIONS 관계 생성
4. cluster_service가 PKM 레이블로 클러스터링
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio

from app.db.neo4j import get_neo4j_client
from app.config import settings

logger = logging.getLogger(__name__)

# PKM 온톨로지 타입
PKM_TYPES = ["Topic", "Project", "Task", "Person"]

# 엔티티 이름 기반 분류 규칙 (LLM 호출 없이 빠른 분류)
# 더 정교한 분류가 필요하면 LLM 사용
CLASSIFICATION_RULES = {
    "Person": [
        # 사람 이름 패턴
        lambda name: any(suffix in name for suffix in ["님", "씨", "교수", "박사", "선생"]),
        lambda name: name.endswith(("수", "호", "민", "준", "진", "현", "석", "영", "훈")),  # 한국 이름 끝글자
    ],
    "Project": [
        lambda name: any(kw in name.lower() for kw in ["프로젝트", "project", "개발", "구현", "시스템"]),
        lambda name: name.startswith(("PKM", "Didymos", "AI")),
    ],
    "Task": [
        lambda name: any(kw in name.lower() for kw in ["todo", "task", "작업", "할일", "수정", "추가", "구현해야"]),
    ],
    # Topic은 기본값 (다른 타입에 해당하지 않으면 Topic)
}


def classify_entity_to_pkm_type(entity_name: str, entity_summary: str = None) -> str:
    """
    엔티티 이름/요약을 기반으로 PKM 타입 분류

    Args:
        entity_name: 엔티티 이름
        entity_summary: Graphiti가 생성한 엔티티 요약

    Returns:
        PKM 타입 (Topic, Project, Task, Person)
    """
    name_lower = entity_name.lower()

    # 규칙 기반 분류
    for pkm_type, rules in CLASSIFICATION_RULES.items():
        for rule in rules:
            try:
                if rule(entity_name):
                    return pkm_type
            except Exception:
                continue

    # 요약에서 힌트 찾기
    if entity_summary:
        summary_lower = entity_summary.lower()
        if any(kw in summary_lower for kw in ["사람", "person", "연구원", "학생", "팀원"]):
            return "Person"
        if any(kw in summary_lower for kw in ["프로젝트", "project", "개발 중", "구현"]):
            return "Project"
        if any(kw in summary_lower for kw in ["해야 할", "완료해야", "task", "todo"]):
            return "Task"

    # 기본값: Topic
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
        # Step 1: PKM 레이블이 없는 EntityNode 조회
        cypher_find = """
        MATCH (e:EntityNode)
        WHERE NOT e:Topic AND NOT e:Project AND NOT e:Task AND NOT e:Person
        RETURN e.uuid as uuid, e.name as name, e.summary as summary
        LIMIT $batch_size
        """

        entities = client.query(cypher_find, {"batch_size": batch_size})

        if not entities:
            logger.info("No EntityNode without PKM labels found")
            return {
                "status": "completed",
                "processed": 0,
                "message": "All EntityNodes already have PKM labels"
            }

        logger.info(f"Found {len(entities)} EntityNodes to classify")

        # Step 2: 각 엔티티 분류 및 레이블 추가
        stats = {"Topic": 0, "Project": 0, "Task": 0, "Person": 0, "errors": 0}

        for entity in entities:
            try:
                uuid = entity["uuid"]
                name = entity["name"] or uuid
                summary = entity.get("summary", "")

                # PKM 타입 분류
                pkm_type = classify_entity_to_pkm_type(name, summary)

                # 레이블 추가
                cypher_add_label = f"""
                MATCH (e:EntityNode {{uuid: $uuid}})
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

        total_processed = sum(stats[t] for t in PKM_TYPES)
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
    """PKM 레이블이 없는 EntityNode 수 조회"""
    try:
        result = client.query("""
            MATCH (e:EntityNode)
            WHERE NOT e:Topic AND NOT e:Project AND NOT e:Task AND NOT e:Person
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
    Graphiti Episode-Entity 관계를 Note-Entity MENTIONS 관계로 변환

    Graphiti는 Episode → EntityNode 관계를 사용
    cluster_service는 Note → Entity MENTIONS 관계를 기대

    이 함수는 Episode의 source_description에서 note_id를 추출하여
    Note → EntityNode MENTIONS 관계를 생성

    Args:
        vault_id: 특정 vault만 처리
        batch_size: 한 번에 처리할 관계 수

    Returns:
        처리 결과 통계
    """
    client = get_neo4j_client()

    try:
        # Step 1: Episode-Entity 관계에서 Note-Entity MENTIONS가 없는 것 찾기
        # Graphiti의 Episode에는 source_description에 "Obsidian note: {path}" 형태로 저장됨
        cypher_find = """
        MATCH (ep:EpisodicNode)-[:MENTIONS]->(e:EntityNode)
        WHERE ep.source_description STARTS WITH 'Obsidian note:'
        WITH ep, e,
             replace(ep.source_description, 'Obsidian note: ', '') as note_path
        MATCH (n:Note {note_id: note_path})
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
                "message": "All Episode-Entity relations already have MENTIONS"
            }

        logger.info(f"Found {len(relations)} MENTIONS relationships to create")

        # Step 2: MENTIONS 관계 생성
        created = 0
        errors = 0

        for rel in relations:
            try:
                cypher_create = """
                MATCH (n:Note {note_id: $note_id})
                MATCH (e:EntityNode {uuid: $entity_uuid})
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
            for pkm_type in PKM_TYPES:
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

        # Step 2: 추출된 EntityNode에 PKM 레이블 추가
        client = get_neo4j_client()

        # 이 노트와 연결된 EntityNode 찾기
        cypher_find_entities = """
        MATCH (ep:EpisodicNode)-[:MENTIONS]->(e:EntityNode)
        WHERE ep.name = $episode_name
          AND NOT e:Topic AND NOT e:Project AND NOT e:Task AND NOT e:Person
        RETURN e.uuid as uuid, e.name as name, e.summary as summary
        """

        episode_name = f"note_{note_id}"
        entities = client.query(cypher_find_entities, {"episode_name": episode_name})

        labeled_count = 0
        for entity in (entities or []):
            pkm_type = classify_entity_to_pkm_type(
                entity["name"] or entity["uuid"],
                entity.get("summary", "")
            )

            cypher_add_label = f"""
            MATCH (e:EntityNode {{uuid: $uuid}})
            SET e:{pkm_type}
            SET e.pkm_type = $pkm_type
            SET e.pkm_classified_at = datetime()
            """

            client.query(cypher_add_label, {"uuid": entity["uuid"], "pkm_type": pkm_type})
            labeled_count += 1

        # Step 3: Note → EntityNode MENTIONS 관계 생성
        cypher_create_mentions = """
        MATCH (n:Note {note_id: $note_id})
        MATCH (ep:EpisodicNode {name: $episode_name})-[:MENTIONS]->(e:EntityNode)
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
