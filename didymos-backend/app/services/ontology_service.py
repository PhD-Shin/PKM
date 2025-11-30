"""
LangChain 기반 Text2Graph 서비스 (HTTP API 버전)
"""
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from app.db.neo4j import get_neo4j_client
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# LLM 초기화
llm = ChatOpenAI(
    model="gpt-4o-mini",  # 비용 효율적
    temperature=0,        # 추출은 결정적이어야 함
    api_key=settings.openai_api_key
)

# 그래프 변환기 설정
llm_transformer = LLMGraphTransformer(
    llm=llm,
    allowed_nodes=["Topic", "Project", "Task", "Person"],
    allowed_relationships=["MENTIONS", "RELATED_TO", "PART_OF", "ASSIGNED_TO", "HAS_TASK"],
    strict_mode=False
)


def process_note_to_graph(note_id: str, content: str, metadata: dict = None):
    """
    노트 텍스트를 그래프로 변환하여 Neo4j에 저장

    Args:
        note_id: 노트 ID
        content: 노트 내용
        metadata: 메타데이터 (tags 등)

    Returns:
        추출된 노드 개수
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

        # 2. Text -> GraphDocument 변환 (LLM 호출)
        logger.info(f"Extracting graph from note: {note_id}")
        graph_documents = llm_transformer.convert_to_graph_documents([doc])

        if not graph_documents or not graph_documents[0].nodes:
            logger.info(f"No entities extracted from {note_id}")
            return 0

        graph_doc = graph_documents[0]

        # 3. 노드 저장
        for node in graph_doc.nodes:
            save_node_via_http(client, node)

        # 4. 관계 저장
        for rel in graph_doc.relationships:
            save_relationship_via_http(client, rel)

        # 5. Note와 추출된 엔티티 연결
        link_extracted_entities_to_note(client, note_id, graph_doc)

        logger.info(f"✅ Successfully extracted {len(graph_doc.nodes)} nodes from {note_id}")
        return len(graph_doc.nodes)

    except Exception as e:
        logger.error(f"Error converting note to graph: {e}")
        raise e


def save_node_via_http(client, node):
    """HTTP API를 통해 노드 저장"""
    try:
        # node.type: "Topic", "Project", etc.
        # node.id: 엔티티 ID (LLM이 생성)
        # node.properties: 추가 속성

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
            "id": node.id,
            "properties": node.properties or {}
        }

        client.query(cypher, params)
        logger.debug(f"Saved node: {node.type}({node.id})")

    except Exception as e:
        logger.error(f"Error saving node {node.type}({node.id}): {e}")


def save_relationship_via_http(client, rel):
    """HTTP API를 통해 관계 저장"""
    try:
        # rel.source: Node
        # rel.target: Node
        # rel.type: "MENTIONS", "RELATED_TO", etc.

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
            "source_id": rel.source.id,
            "target_id": rel.target.id
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
            cypher = f"""
            MATCH (note:Note {{note_id: $note_id}})
            MATCH (entity:{node.type} {{id: $entity_id}})
            MERGE (note)-[m:MENTIONS]->(entity)
            ON CREATE SET m.created_at = datetime(), m.last_seen = datetime()
            ON MATCH SET m.last_seen = datetime()
            """

            params = {
                "note_id": note_id,
                "entity_id": node.id
            }

            client.query(cypher, params)

        logger.info(f"Linked {len(graph_doc.nodes)} entities to note {note_id}")

    except Exception as e:
        logger.error(f"Error linking entities to note: {e}")
