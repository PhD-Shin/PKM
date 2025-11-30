"""
벡터 검색 및 임베딩 서비스
"""
from langchain_openai import OpenAIEmbeddings
from app.config import settings
from app.db.neo4j import get_neo4j_client
import logging
from typing import List

logger = logging.getLogger(__name__)

# OpenAI Embeddings 초기화
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",  # 비용 효율적
    api_key=settings.openai_api_key
)


def initialize_vector_index():
    """
    Neo4j 벡터 인덱스 초기화

    Note 노드에 대한 벡터 인덱스를 생성합니다.
    이미 존재하는 경우 무시됩니다.
    """
    client = get_neo4j_client()

    try:
        # 벡터 인덱스 생성 쿼리
        # Neo4j 5.x에서는 벡터 인덱스를 수동으로 생성해야 합니다
        cypher = """
        CREATE VECTOR INDEX note_embeddings IF NOT EXISTS
        FOR (n:Note)
        ON n.embedding
        OPTIONS {indexConfig: {
            `vector.dimensions`: 1536,
            `vector.similarity_function`: 'cosine'
        }}
        """

        client.query(cypher, {})
        logger.info("✅ Vector index 'note_embeddings' created or already exists")
        return True

    except Exception as e:
        logger.error(f"Error creating vector index: {e}")
        # 인덱스가 이미 존재하는 경우 등은 무시
        if "already exists" in str(e).lower() or "equivalent" in str(e).lower():
            logger.info("Vector index already exists")
            return True
        return False


def store_note_embedding(note_id: str, content: str, metadata: dict = None):
    """
    노트 임베딩을 생성하고 Neo4j에 저장

    Args:
        note_id: 노트 ID
        content: 노트 내용
        metadata: 메타데이터

    Returns:
        성공 여부
    """
    if not content or len(content.strip()) < 10:
        logger.info(f"Content too short for embedding: {note_id}")
        return False

    try:
        client = get_neo4j_client()

        # 1. 임베딩 생성
        embedding_vector = embeddings.embed_query(content)

        # 2. Neo4j에 저장
        cypher = """
        MATCH (n:Note {note_id: $note_id})
        SET n.embedding = $embedding
        SET n.embedding_updated_at = datetime()
        RETURN n.note_id AS note_id
        """

        params = {
            "note_id": note_id,
            "embedding": embedding_vector
        }

        result = client.query(cypher, params)

        if result:
            logger.info(f"✅ Embedding stored for note: {note_id}")
            return True
        else:
            logger.warning(f"Note not found for embedding: {note_id}")
            return False

    except Exception as e:
        logger.error(f"Error storing embedding for {note_id}: {e}")
        return False


def vector_search(query: str, k: int = 5, filter_dict: dict = None):
    """
    벡터 유사도 검색

    Args:
        query: 검색 쿼리
        k: 반환할 결과 개수
        filter_dict: 필터 조건 (예: {"user_id": "user123"})

    Returns:
        유사한 노트 목록
    """
    try:
        client = get_neo4j_client()

        # 1. 쿼리 임베딩 생성
        query_embedding = embeddings.embed_query(query)

        # 2. 벡터 검색 (코사인 유사도)
        cypher = """
        CALL db.index.vector.queryNodes('note_embeddings', $k, $query_embedding)
        YIELD node AS n, score
        RETURN
            n.note_id AS note_id,
            n.title AS title,
            n.path AS path,
            n.content AS content,
            n.tags AS tags,
            score
        ORDER BY score DESC
        LIMIT $k
        """

        params = {
            "query_embedding": query_embedding,
            "k": k
        }

        results = client.query(cypher, params)

        if not results:
            logger.warning("Vector search returned no results")
            return []

        return [{
            "note_id": r.get("note_id", ""),
            "title": r.get("title", ""),
            "path": r.get("path", ""),
            "content": r.get("content", "")[:200],  # 처음 200자만
            "tags": r.get("tags", []),
            "score": r.get("score", 0.0),
            "source": "vector"
        } for r in results if r.get("note_id")]

    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        logger.warning("Falling back to empty results")
        return []


def graph_search(note_id: str, max_depth: int = 2, limit: int = 5):
    """
    그래프 기반 연결된 노트 검색

    Args:
        note_id: 기준 노트 ID
        max_depth: 탐색 깊이
        limit: 반환할 결과 개수

    Returns:
        연결된 노트 목록
    """
    try:
        client = get_neo4j_client()

        # 그래프 탐색: 현재 노트와 연결된 엔티티를 통해 다른 노트 찾기
        cypher = f"""
        MATCH (n:Note {{note_id: $note_id}})-[:MENTIONS]->(entity)
        MATCH (entity)<-[:MENTIONS]-(related:Note)
        WHERE related.note_id <> $note_id
        WITH related, COUNT(DISTINCT entity) AS shared_entities
        ORDER BY shared_entities DESC
        LIMIT $limit
        RETURN
            related.note_id AS note_id,
            related.title AS title,
            related.path AS path,
            related.content AS content,
            related.tags AS tags,
            shared_entities AS score
        """

        params = {
            "note_id": note_id,
            "limit": limit
        }

        results = client.query(cypher, params)

        if not results:
            logger.warning("Graph search returned no results")
            return []

        return [{
            "note_id": r.get("note_id", ""),
            "title": r.get("title", ""),
            "path": r.get("path", ""),
            "content": r.get("content", "")[:200],
            "tags": r.get("tags", []),
            "score": r.get("score", 0),
            "source": "graph",
            "shared_entities": r.get("score", 0)
        } for r in results if r.get("note_id")]

    except Exception as e:
        logger.error(f"Graph search failed: {e}")
        logger.warning("Falling back to empty results")
        return []


def hybrid_search(query: str = None, note_id: str = None, k: int = 10):
    """
    하이브리드 검색: 벡터 + 그래프 결합

    Args:
        query: 텍스트 쿼리 (벡터 검색용)
        note_id: 기준 노트 ID (그래프 검색용)
        k: 총 반환할 결과 개수

    Returns:
        추천 노트 목록 (중복 제거 및 점수 기반 정렬)
    """
    results = []

    # 1. 벡터 검색
    if query:
        vector_results = vector_search(query, k=k)
        results.extend(vector_results)

    # 2. 그래프 검색
    if note_id:
        graph_results = graph_search(note_id, limit=k)
        results.extend(graph_results)

    # 3. 중복 제거 및 점수 정규화
    seen = {}
    for item in results:
        note_id_key = item["note_id"]
        if note_id_key not in seen:
            seen[note_id_key] = item
        else:
            # 같은 노트가 여러 소스에서 나온 경우 점수 합산
            seen[note_id_key]["score"] = seen[note_id_key]["score"] + item["score"] * 0.5
            seen[note_id_key]["source"] = "hybrid"

    # 4. 점수 기반 정렬
    final_results = sorted(seen.values(), key=lambda x: x["score"], reverse=True)

    return final_results[:k]


def find_semantically_similar_notes(query: str, limit: int = 5) -> List[dict]:
    """
    벡터 유사도 기반 관련 노트 추천
    """
    try:
        results = vector_search(query=query, k=limit)
        similar = []
        for item in results:
            similarity = _normalize_similarity(item.get("score", 0.0))
            similar.append(
                {
                    "note_id": item.get("note_id", ""),
                    "title": item.get("title", ""),
                    "path": item.get("path", ""),
                    "similarity": similarity,
                    "reason": "semantic",
                }
            )
        return similar
    except Exception as e:
        logger.error(f"Vector similarity search failed: {e}")
        return []


def _normalize_similarity(score: float) -> float:
    """
    Neo4j 벡터 점수를 0~1 범위로 정규화
    """
    try:
        normalized = (float(score) + 1.0) / 2.0
        return max(0.0, min(normalized, 1.0))
    except Exception:
        return 0.0
