"""
LangChain 기반 Text2Graph 서비스 (HTTP API 버전)
"""
import re
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from app.db.neo4j import get_neo4j_client
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# 동의어 매핑 (정규화용)
ENTITY_SYNONYMS = {
    # 대학교
    "서울대": "서울대학교",
    "snu": "서울대학교",
    "seoul national university": "서울대학교",
    "서울 대학교": "서울대학교",
    # 추가 동의어는 여기에...
}


def normalize_entity_id(entity_id: str) -> str:
    """
    엔티티 ID 정규화
    - 소문자 변환
    - 공백 정리
    - 동의어 병합
    """
    if not entity_id:
        return entity_id

    # 1. 기본 정규화: 앞뒤 공백 제거, 연속 공백 단일화
    normalized = re.sub(r'\s+', ' ', entity_id.strip())

    # 2. 동의어 확인 (소문자로 비교)
    lower_id = normalized.lower()
    if lower_id in ENTITY_SYNONYMS:
        normalized = ENTITY_SYNONYMS[lower_id]

    # 3. 부분 매칭으로 동의어 적용 (예: "서울대 박사" → skip)
    # 단, 정확히 일치하는 경우만 치환

    return normalized

# LLM 초기화
llm = ChatOpenAI(
    model="gpt-5-mini",  # GPT-5 Mini
    temperature=0,        # 추출은 결정적이어야 함
    api_key=settings.openai_api_key
)

# 커스텀 프롬프트 템플릿 - 맥락 중심 엔티티 추출
from langchain_core.prompts import ChatPromptTemplate

CUSTOM_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a semantic analyst for a personal knowledge management system. Your task is to deeply understand the CONTEXT and PURPOSE of each note, then extract only the concepts that represent what this note is truly about.

## Your Analysis Process:
1. **Read the entire note carefully** - understand the author's intent
2. **Identify the central theme** - what question is being answered? what problem is being solved?
3. **Find conceptual anchors** - ideas that would connect this note to other related notes
4. **Ignore surface-level keywords** - names, places, dates that appear but aren't central

## Entity Types (Extract ONLY if central to the note's purpose):

**Topic** - The intellectual concept or domain this note explores
- Good: "Attention Mechanism", "Knowledge Graph Design", "Spaced Repetition Learning"
- Bad: "Python" (just a tool), "2024" (just a date), "서울대학교" (just a location)
- Ask: "Is this note TEACHING or EXPLORING this concept?"

**Project** - A defined initiative with goals that this note documents
- Good: "Didymos PKM System", "Thesis Chapter 3"
- Bad: "research" (too vague), "meeting" (just an event)
- Ask: "Does this note advance or plan this specific project?"

**Person** - Someone whose ideas, work, or collaboration is discussed in depth
- Good: "Vaswani" (if discussing their transformer paper in depth)
- Bad: "Professor Kim" (if just mentioned in passing or as affiliation)
- Ask: "Are this person's contributions central to understanding this note?"

**Task** - A concrete action item with clear deliverable
- Good: "Implement embedding pipeline", "Review literature on RAG"
- Bad: "think about it", "follow up" (too vague)
- Ask: "Is this a specific, actionable commitment?"

## Critical Rules:
1. **Context over Keywords**: "서울대학교에서 Transformer 연구" → Extract "Transformer" (the topic), NOT "서울대학교" (just context)
2. **Depth over Breadth**: Extract 1-3 truly central concepts, not 10 loosely related terms
3. **Searchability Test**: "If I search for this entity, would I want to find THIS note?" If no, don't extract.
4. **No Generic Terms**: Never extract: 연구, 논문, 프로젝트, 회의, 미팅, 정리, 메모, 노트

## Relationships:
- RELATED_TO: Conceptual connection between extracted entities
- PART_OF: Hierarchical relationship (subtopic of larger topic)

Think step by step about what this note is REALLY about before extracting."""),
    ("human", "{input}")
])

# 그래프 변환기 설정
llm_transformer = LLMGraphTransformer(
    llm=llm,
    allowed_nodes=["Topic", "Project", "Task", "Person"],
    allowed_relationships=["MENTIONS", "RELATED_TO", "PART_OF", "ASSIGNED_TO", "HAS_TASK"],
    strict_mode=False,
    node_properties=["name", "description"],
    prompt=CUSTOM_EXTRACTION_PROMPT
)


def filter_entities_by_relations(graph_doc) -> tuple:
    """
    Graph-based Entity Resolution: 관계가 있는 엔티티만 필터링

    LLM이 추출한 엔티티 중에서 다른 엔티티와 관계(RELATED_TO, PART_OF 등)가
    있는 엔티티만 유지합니다. 관계가 없는 고립 엔티티는 단순 언급으로 간주하여 제외.

    Args:
        graph_doc: LLM이 추출한 GraphDocument

    Returns:
        (filtered_nodes, filtered_relationships): 필터링된 노드와 관계
    """
    if not graph_doc.nodes:
        return [], []

    # 관계에 참여하는 엔티티 ID 수집
    connected_entity_ids = set()
    for rel in graph_doc.relationships:
        # Note-Entity 관계는 제외하고, Entity-Entity 관계만 고려
        # MENTIONS는 Note→Entity 관계이므로 제외
        if rel.type not in ["MENTIONS"]:
            source_id = normalize_entity_id(rel.source.id)
            target_id = normalize_entity_id(rel.target.id)
            connected_entity_ids.add(source_id)
            connected_entity_ids.add(target_id)

    # 연결된 엔티티만 필터링
    filtered_nodes = []
    filtered_node_ids = set()

    for node in graph_doc.nodes:
        normalized_id = normalize_entity_id(node.id)
        if normalized_id in connected_entity_ids:
            filtered_nodes.append(node)
            filtered_node_ids.add(normalized_id)

    # 필터링된 노드에 해당하는 관계만 유지
    filtered_relationships = []
    for rel in graph_doc.relationships:
        source_id = normalize_entity_id(rel.source.id)
        target_id = normalize_entity_id(rel.target.id)
        # 양쪽 노드가 모두 필터링된 노드에 있는 경우만 유지
        if source_id in filtered_node_ids and target_id in filtered_node_ids:
            filtered_relationships.append(rel)

    return filtered_nodes, filtered_relationships


def process_note_to_graph(note_id: str, content: str, metadata: dict = None):
    """
    노트 텍스트를 그래프로 변환하여 Neo4j에 저장

    Graph-based Entity Resolution (2단계 추출):
    - Stage 1: LLM이 엔티티 후보 + 관계 동시 추출
    - Stage 2: 관계(RELATED_TO, PART_OF)가 있는 엔티티만 저장
    - 고립 엔티티(관계 없음)는 단순 언급으로 간주하여 제외

    Args:
        note_id: 노트 ID
        content: 노트 내용
        metadata: 메타데이터 (tags 등)

    Returns:
        추출된 노드 개수 (필터링 후)
    """
    if not content or len(content.strip()) < 10:
        logger.info(f"Content too short for {note_id}, skipping extraction")
        return 0

    try:
        client = get_neo4j_client()
        metadata = metadata or {}

        # 1. Document 객체 생성
        doc = Document(
            page_content=content,
            metadata={
                "id": note_id,
                **metadata
            }
        )

        # 2. Stage 1: Text -> GraphDocument 변환 (LLM 호출)
        # LLM이 엔티티 후보와 관계를 동시에 추출
        logger.info(f"[Stage 1] Extracting entity candidates from note: {note_id}")
        graph_documents = llm_transformer.convert_to_graph_documents([doc])

        if not graph_documents or not graph_documents[0].nodes:
            logger.info(f"No entities extracted from {note_id}")
            return 0

        graph_doc = graph_documents[0]
        original_count = len(graph_doc.nodes)
        original_rel_count = len(graph_doc.relationships)

        # 3. Stage 2: Graph-based Entity Resolution
        # 관계가 있는 엔티티만 필터링 (고립 엔티티 제외)
        logger.info(f"[Stage 2] Filtering entities by relations...")
        filtered_nodes, filtered_relationships = filter_entities_by_relations(graph_doc)

        filtered_count = len(filtered_nodes)
        excluded_count = original_count - filtered_count

        if excluded_count > 0:
            # 제외된 엔티티 로깅 (디버깅용)
            excluded_ids = set(normalize_entity_id(n.id) for n in graph_doc.nodes) - \
                          set(normalize_entity_id(n.id) for n in filtered_nodes)
            logger.info(f"[Stage 2] Excluded {excluded_count} isolated entities: {list(excluded_ids)[:5]}...")

        if not filtered_nodes:
            logger.info(f"No connected entities found in {note_id} (all {original_count} were isolated)")
            return 0

        # 4. 필터링된 노드만 저장
        for node in filtered_nodes:
            save_node_via_http(client, node)

        # 5. 필터링된 관계만 저장
        for rel in filtered_relationships:
            save_relationship_via_http(client, rel)

        # 6. Note와 필터링된 엔티티 연결
        # graph_doc 대신 filtered_nodes를 사용하여 연결
        link_filtered_entities_to_note(client, note_id, filtered_nodes)

        logger.info(f"✅ Successfully extracted {filtered_count}/{original_count} entities from {note_id} "
                   f"(excluded {excluded_count} isolated entities)")
        return filtered_count

    except Exception as e:
        logger.error(f"Error converting note to graph: {e}")
        raise e


def link_filtered_entities_to_note(client, note_id: str, filtered_nodes: list):
    """
    필터링된 엔티티들을 Note 노드와 MENTIONS 관계로 연결
    """
    try:
        for node in filtered_nodes:
            # 정규화된 ID 사용
            entity_id = normalize_entity_id(node.id)

            cypher = f"""
            MATCH (note:Note {{note_id: $note_id}})
            MATCH (entity:{node.type} {{id: $entity_id}})
            MERGE (note)-[m:MENTIONS]->(entity)
            ON CREATE SET m.created_at = datetime(), m.last_seen = datetime()
            ON MATCH SET m.last_seen = datetime()
            """

            params = {
                "note_id": note_id,
                "entity_id": entity_id
            }

            client.query(cypher, params)

        logger.info(f"Linked {len(filtered_nodes)} filtered entities to note {note_id}")

    except Exception as e:
        logger.error(f"Error linking entities to note: {e}")


def save_node_via_http(client, node):
    """HTTP API를 통해 노드 저장"""
    try:
        # node.type: "Topic", "Project", etc.
        # node.id: 엔티티 ID (LLM이 생성)
        # node.properties: 추가 속성

        # 정규화된 ID 생성 (소문자, 공백 제거)
        normalized_id = normalize_entity_id(node.id)

        # properties에서 name 추출 (없으면 원본 id 사용)
        properties = node.properties.copy() if node.properties else {}
        if "name" not in properties or not properties.get("name"):
            properties["name"] = node.id  # 원본 이름 보존

        cypher = f"""
        MERGE (n:{node.type} {{id: $id}})
        ON CREATE SET
            n += $properties,
            n.created_at = datetime(),
            n.first_seen = datetime(),
            n.last_seen = datetime()
        ON MATCH SET
            n += $properties,
            n.updated_at = datetime(),
            n.last_seen = datetime()
        RETURN n.id AS id
        """

        params = {
            "id": normalized_id,
            "properties": properties
        }

        client.query(cypher, params)
        logger.debug(f"Saved node: {node.type}({normalized_id}) [name: {properties.get('name')}]")

    except Exception as e:
        logger.error(f"Error saving node {node.type}({node.id}): {e}")


def save_relationship_via_http(client, rel):
    """HTTP API를 통해 관계 저장"""
    try:
        # rel.source: Node
        # rel.target: Node
        # rel.type: "MENTIONS", "RELATED_TO", etc.

        # 정규화된 ID 사용
        source_id = normalize_entity_id(rel.source.id)
        target_id = normalize_entity_id(rel.target.id)

        cypher = f"""
        MATCH (source:{rel.source.type} {{id: $source_id}})
        MATCH (target:{rel.target.type} {{id: $target_id}})
        MERGE (source)-[r:{rel.type}]->(target)
        ON CREATE SET
            r.created_at = datetime(),
            r.last_seen = datetime()
        ON MATCH SET
            r.last_seen = datetime()
        RETURN type(r) AS rel_type
        """

        params = {
            "source_id": source_id,
            "target_id": target_id
        }

        client.query(cypher, params)
        logger.debug(f"Saved relationship: {rel.source.id}-[{rel.type}]->{rel.target.id}")

    except Exception as e:
        logger.error(f"Error saving relationship: {e}")


def link_extracted_entities_to_note(client, note_id, graph_doc):
    """
    추출된 엔티티들을 Note 노드와 MENTIONS 관계로 연결
    """
    try:
        for node in graph_doc.nodes:
            # 정규화된 ID 사용
            entity_id = normalize_entity_id(node.id)

            cypher = f"""
            MATCH (note:Note {{note_id: $note_id}})
            MATCH (entity:{node.type} {{id: $entity_id}})
            MERGE (note)-[m:MENTIONS]->(entity)
            ON CREATE SET m.created_at = datetime(), m.last_seen = datetime()
            ON MATCH SET m.last_seen = datetime()
            """

            params = {
                "note_id": note_id,
                "entity_id": entity_id
            }

            client.query(cypher, params)

        logger.info(f"Linked {len(graph_doc.nodes)} entities to note {note_id}")

    except Exception as e:
        logger.error(f"Error linking entities to note: {e}")


def deduplicate_entities(client, dry_run: bool = True) -> dict:
    """
    중복 엔티티를 병합하는 유틸리티 함수

    동의어 매핑을 기반으로 중복 엔티티를 찾아서 병합합니다.
    - 관계를 canonical 엔티티로 이전
    - 중복 엔티티 삭제

    Args:
        client: Neo4j 클라이언트
        dry_run: True면 실제 삭제하지 않고 결과만 반환

    Returns:
        병합 결과 통계
    """
    stats = {
        "duplicates_found": 0,
        "relations_migrated": 0,
        "entities_deleted": 0,
        "details": []
    }

    try:
        # 1. 동의어 기반 중복 찾기
        for synonym, canonical in ENTITY_SYNONYMS.items():
            if synonym == canonical.lower():
                continue  # 자기 자신은 스킵

            # 중복 엔티티 찾기
            cypher_find = """
            MATCH (dup)
            WHERE (dup:Topic OR dup:Project OR dup:Task OR dup:Person)
              AND toLower(dup.id) = $synonym
            RETURN dup.id as dup_id, labels(dup)[0] as dup_type
            """
            dups = client.query(cypher_find, {"synonym": synonym})

            if not dups:
                continue

            for dup in dups:
                dup_id = dup["dup_id"]
                dup_type = dup["dup_type"]
                stats["duplicates_found"] += 1
                stats["details"].append({
                    "duplicate": dup_id,
                    "canonical": canonical,
                    "type": dup_type
                })

                if dry_run:
                    continue

                # 2. 관계 이전: duplicate → canonical
                # MENTIONS 관계 이전
                cypher_migrate_mentions = f"""
                MATCH (note:Note)-[old:MENTIONS]->(dup:{dup_type} {{id: $dup_id}})
                MATCH (canon:{dup_type} {{id: $canonical}})
                MERGE (note)-[new:MENTIONS]->(canon)
                ON CREATE SET new.created_at = old.created_at, new.last_seen = datetime()
                ON MATCH SET new.last_seen = datetime()
                DELETE old
                RETURN count(*) as migrated
                """
                result = client.query(cypher_migrate_mentions, {
                    "dup_id": dup_id,
                    "canonical": canonical
                })
                if result:
                    stats["relations_migrated"] += result[0].get("migrated", 0)

                # 다른 관계들도 이전 (RELATED_TO 등)
                cypher_migrate_outgoing = f"""
                MATCH (dup:{dup_type} {{id: $dup_id}})-[old]->(target)
                WHERE type(old) <> 'MENTIONS'
                MATCH (canon:{dup_type} {{id: $canonical}})
                WITH dup, old, target, canon, type(old) as rel_type
                CALL apoc.merge.relationship(canon, rel_type, {{}}, {{}}, target, {{}}) YIELD rel
                DELETE old
                RETURN count(*) as migrated
                """
                # Note: APOC이 없으면 이 부분은 수동으로 처리해야 함

                # 3. 중복 엔티티 삭제
                cypher_delete = f"""
                MATCH (dup:{dup_type} {{id: $dup_id}})
                WHERE NOT (dup)--()  // 관계가 없는 경우만 삭제
                DELETE dup
                RETURN count(*) as deleted
                """
                result = client.query(cypher_delete, {"dup_id": dup_id})
                if result:
                    stats["entities_deleted"] += result[0].get("deleted", 0)

        logger.info(f"Deduplication {'dry run' if dry_run else 'completed'}: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Error during deduplication: {e}")
        stats["error"] = str(e)
        return stats


def merge_duplicate_entities(client, source_id: str, target_id: str, entity_type: str) -> bool:
    """
    특정 중복 엔티티를 수동으로 병합

    Args:
        client: Neo4j 클라이언트
        source_id: 병합할 엔티티 ID (삭제될 엔티티)
        target_id: 대상 엔티티 ID (유지될 엔티티)
        entity_type: 엔티티 타입 (Topic, Project, Task, Person)

    Returns:
        성공 여부
    """
    try:
        # 1. MENTIONS 관계 이전
        cypher_migrate = f"""
        MATCH (note:Note)-[old:MENTIONS]->(source:{entity_type} {{id: $source_id}})
        MATCH (target:{entity_type} {{id: $target_id}})
        MERGE (note)-[new:MENTIONS]->(target)
        ON CREATE SET new.created_at = old.created_at, new.last_seen = datetime()
        ON MATCH SET new.last_seen = datetime()
        DELETE old
        RETURN count(*) as migrated
        """
        client.query(cypher_migrate, {"source_id": source_id, "target_id": target_id})

        # 2. 엔티티 간 관계 이전 (RELATED_TO 등)
        cypher_migrate_rels = f"""
        MATCH (source:{entity_type} {{id: $source_id}})-[old:RELATED_TO]->(other)
        MATCH (target:{entity_type} {{id: $target_id}})
        MERGE (target)-[:RELATED_TO]->(other)
        DELETE old
        """
        client.query(cypher_migrate_rels, {"source_id": source_id, "target_id": target_id})

        # 3. 소스 엔티티 삭제
        cypher_delete = f"""
        MATCH (source:{entity_type} {{id: $source_id}})
        DETACH DELETE source
        """
        client.query(cypher_delete, {"source_id": source_id})

        logger.info(f"Merged entity: {source_id} → {target_id}")
        return True

    except Exception as e:
        logger.error(f"Error merging entities: {e}")
        return False
