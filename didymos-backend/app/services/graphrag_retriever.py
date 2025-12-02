"""
neo4j-graphrag 기반 Hybrid Retriever 서비스

Phase 12: VectorRetriever + Text2CypherRetriever 통합
Phase 14: ToolsRetriever 통합 (Agentic RAG)

기능:
- 시맨틱 벡터 검색 (Note 임베딩)
- 자연어 → Cypher 변환 검색
- VectorCypherRetriever (하이브리드)
- ToolsRetriever (LLM이 자동으로 최적 retriever 선택)

참고: https://neo4j.com/docs/neo4j-graphrag-python/current/
"""
import logging
from typing import Optional, List, Dict, Any
from neo4j import GraphDatabase
from app.config import settings

logger = logging.getLogger(__name__)

# neo4j-graphrag는 선택적 의존성
try:
    from neo4j_graphrag.retrievers import (
        VectorRetriever,
        VectorCypherRetriever,
        Text2CypherRetriever,
    )
    from neo4j_graphrag.embeddings import OpenAIEmbeddings
    from neo4j_graphrag.llm import OpenAILLM
    GRAPHRAG_AVAILABLE = True

    # ToolsRetriever는 별도 import (없을 수 있음)
    try:
        from neo4j_graphrag.retrievers import ToolsRetriever
        TOOLS_RETRIEVER_AVAILABLE = True
    except ImportError:
        TOOLS_RETRIEVER_AVAILABLE = False
        logger.info("ToolsRetriever not available in this neo4j-graphrag version")
except ImportError:
    GRAPHRAG_AVAILABLE = False
    TOOLS_RETRIEVER_AVAILABLE = False
    logger.warning("neo4j-graphrag not installed. GraphRAG features disabled.")


# 노트 검색을 위한 Cypher 템플릿
NOTE_RETRIEVAL_QUERY = """
// Vector search로 찾은 노트에서 시작
MATCH (node:Note)
WHERE node.note_id IN $node_ids

// 노트가 언급하는 엔티티들 (1-hop)
OPTIONAL MATCH (node)-[:MENTIONS]->(entity)
WHERE entity:Topic OR entity:Project OR entity:Task OR entity:Person

// SKOS 계층 관계 탐색 (1-hop 상위/하위)
OPTIONAL MATCH (entity)-[:BROADER]->(broader)
OPTIONAL MATCH (entity)-[:NARROWER]->(narrower)

// 관련 엔티티 (1-hop)
OPTIONAL MATCH (entity)-[:RELATED_TO]-(related)

RETURN
    node.note_id AS note_id,
    node.title AS title,
    node.path AS path,
    node.content AS content,
    node.updated_at AS updated_at,
    collect(DISTINCT {
        id: entity.id,
        name: entity.name,
        type: labels(entity)[0]
    }) AS mentioned_entities,
    collect(DISTINCT {
        id: broader.id,
        name: broader.name,
        relation: 'BROADER'
    }) AS hierarchy_broader,
    collect(DISTINCT {
        id: narrower.id,
        name: narrower.name,
        relation: 'NARROWER'
    }) AS hierarchy_narrower,
    collect(DISTINCT {
        id: related.id,
        name: related.name
    }) AS related_entities
ORDER BY node.updated_at DESC
"""

# Text2Cypher용 스키마 설명
GRAPH_SCHEMA_DESCRIPTION = """
## 노드 타입
- Note: 사용자의 Obsidian 노트 (note_id, title, path, content, tags, created_at, updated_at)
- Topic: 지식 주제/개념 (id, name, description)
- Project: 프로젝트 (id, name, status, description)
- Task: 할일 (id, title, status, priority, due_date)
- Person: 사람 (id, name, role)
- Vault: 사용자의 Obsidian Vault (id)
- User: 사용자 (id, token)

## 관계 타입
- (User)-[:OWNS]->(Vault): 사용자가 Vault 소유
- (Vault)-[:CONTAINS]->(Note): Vault에 노트 포함
- (Note)-[:MENTIONS]->(Topic|Project|Task|Person): 노트가 엔티티 언급
- (Topic)-[:BROADER]->(Topic): SKOS 계층 (하위→상위)
- (Topic)-[:NARROWER]->(Topic): SKOS 계층 (상위→하위)
- (Topic)-[:RELATED_TO]-(Topic): 연관 관계
- (Project)-[:HAS_TASK]->(Task): 프로젝트에 태스크 포함
- (Task)-[:ASSIGNED_TO]->(Person): 태스크 담당자

## 일반적인 쿼리 패턴
1. 특정 주제 관련 노트 찾기:
   MATCH (n:Note)-[:MENTIONS]->(t:Topic {name: "주제명"}) RETURN n

2. 주제의 상위 계층 탐색:
   MATCH path = (t:Topic {name: "Machine Learning"})-[:BROADER*1..3]->(parent:Topic)
   RETURN path

3. 프로젝트의 할일 목록:
   MATCH (p:Project {name: "프로젝트명"})-[:HAS_TASK]->(t:Task)
   RETURN t

4. 최근 수정된 노트:
   MATCH (n:Note) RETURN n ORDER BY n.updated_at DESC LIMIT 10
"""


class GraphRAGRetrieverService:
    """
    neo4j-graphrag 기반 하이브리드 검색 서비스

    지원 검색 모드:
    1. vector: 순수 벡터 유사도 검색 (VectorRetriever)
    2. text2cypher: 자연어 → Cypher 변환 검색 (Text2CypherRetriever)
    3. hybrid: 벡터 검색 + 그래프 컨텍스트 확장 (VectorCypherRetriever)
    """

    _instance = None

    def __init__(self):
        if not GRAPHRAG_AVAILABLE:
            raise RuntimeError("neo4j-graphrag is not installed")

        # Neo4j 드라이버 생성
        self.driver = GraphDatabase.driver(
            self._normalize_uri(settings.neo4j_uri),
            auth=(settings.neo4j_username, settings.neo4j_password)
        )

        # OpenAI 임베딩 & LLM 초기화
        self.embedder = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.openai_api_key
        )

        self.llm = OpenAILLM(
            model_name="gpt-4o-mini",
            api_key=settings.openai_api_key
        )

        # Retrievers 초기화 (lazy)
        self._vector_retriever = None
        self._vector_cypher_retriever = None
        self._text2cypher_retriever = None
        self._tools_retriever = None

        logger.info("GraphRAGRetrieverService initialized")

    @classmethod
    async def get_instance(cls) -> "GraphRAGRetrieverService":
        """싱글톤 인스턴스 반환"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @staticmethod
    def _normalize_uri(uri: str) -> str:
        """AuraDB 호환 URI 변환"""
        if uri.startswith("neo4j+s://"):
            return uri.replace("neo4j+s://", "neo4j+ssc://")
        return uri

    @property
    def vector_retriever(self) -> VectorRetriever:
        """VectorRetriever (lazy initialization)"""
        if self._vector_retriever is None:
            self._vector_retriever = VectorRetriever(
                driver=self.driver,
                index_name="note_embeddings",  # vector_service.py에서 생성하는 인덱스
                embedder=self.embedder,
                return_properties=["note_id", "title", "path", "content", "updated_at"]
            )
        return self._vector_retriever

    @property
    def vector_cypher_retriever(self) -> VectorCypherRetriever:
        """VectorCypherRetriever (lazy initialization)"""
        if self._vector_cypher_retriever is None:
            self._vector_cypher_retriever = VectorCypherRetriever(
                driver=self.driver,
                index_name="note_embeddings",
                embedder=self.embedder,
                retrieval_query=NOTE_RETRIEVAL_QUERY
            )
        return self._vector_cypher_retriever

    @property
    def text2cypher_retriever(self) -> Text2CypherRetriever:
        """Text2CypherRetriever (lazy initialization)"""
        if self._text2cypher_retriever is None:
            self._text2cypher_retriever = Text2CypherRetriever(
                driver=self.driver,
                llm=self.llm,
                neo4j_schema=GRAPH_SCHEMA_DESCRIPTION
            )
        return self._text2cypher_retriever

    @property
    def tools_retriever(self):
        """
        ToolsRetriever (lazy initialization)

        LLM이 질문을 분석하고 최적의 retriever를 자동 선택:
        - 시맨틱 유사도 → VectorRetriever
        - 구조화된 질문 → Text2CypherRetriever
        - 복합 질문 → 여러 retriever 조합

        Phase 14: Agentic RAG 패턴
        """
        if not TOOLS_RETRIEVER_AVAILABLE:
            return None

        if self._tools_retriever is None:
            # 각 retriever에 설명 추가
            retrievers = [
                {
                    "retriever": self.vector_retriever,
                    "name": "semantic_search",
                    "description": "Use for conceptual or semantic similarity queries. "
                                   "Best for finding notes about a topic, concept, or idea. "
                                   "Example: 'notes about machine learning', 'content related to transformers'"
                },
                {
                    "retriever": self.text2cypher_retriever,
                    "name": "structured_query",
                    "description": "Use for structured queries about specific entities, relationships, or filters. "
                                   "Best for finding specific items, counting, filtering by properties. "
                                   "Example: 'list all tasks with high priority', 'projects started in 2024', "
                                   "'topics broader than Machine Learning'"
                },
                {
                    "retriever": self.vector_cypher_retriever,
                    "name": "hybrid_search",
                    "description": "Use for queries that need both semantic matching AND graph context. "
                                   "Best for understanding context around matched notes. "
                                   "Example: 'what topics are related to my notes on LLMs'"
                }
            ]

            self._tools_retriever = ToolsRetriever(
                retrievers=retrievers,
                llm=self.llm
            )
        return self._tools_retriever

    async def search_vector(
        self,
        query: str,
        top_k: int = 10,
        vault_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        순수 벡터 검색 (VectorRetriever)

        노트 임베딩을 기반으로 시맨틱 유사도 검색

        Args:
            query: 검색 쿼리
            top_k: 반환할 결과 수
            vault_id: 특정 Vault로 필터링 (optional)

        Returns:
            검색된 노트 목록 (score 포함)
        """
        try:
            # 검색 실행
            results = self.vector_retriever.search(
                query_text=query,
                top_k=top_k
            )

            # 결과 변환
            notes = []
            for item in results.items:
                note = {
                    "note_id": item.content.get("note_id"),
                    "title": item.content.get("title"),
                    "path": item.content.get("path"),
                    "content": item.content.get("content", "")[:500],  # 미리보기
                    "updated_at": item.content.get("updated_at"),
                    "score": item.score
                }

                # vault_id 필터링 (필요한 경우)
                if vault_id:
                    # path에서 vault 확인 또는 추가 쿼리
                    pass  # 현재는 전체 검색

                notes.append(note)

            logger.info(f"Vector search returned {len(notes)} results for: {query[:50]}...")
            return notes

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            raise

    async def search_hybrid(
        self,
        query: str,
        top_k: int = 10,
        vault_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        하이브리드 검색 (VectorCypherRetriever)

        벡터 검색 + 그래프 컨텍스트 확장:
        1. 벡터 검색으로 관련 노트 찾기
        2. 노트가 언급하는 엔티티 탐색
        3. SKOS 계층 관계 확장
        4. 관련 엔티티 포함

        Args:
            query: 검색 쿼리
            top_k: 반환할 결과 수
            vault_id: 특정 Vault로 필터링 (optional)

        Returns:
            검색된 노트 + 그래프 컨텍스트
        """
        try:
            results = self.vector_cypher_retriever.search(
                query_text=query,
                top_k=top_k
            )

            notes = []
            for item in results.items:
                content = item.content
                note = {
                    "note_id": content.get("note_id"),
                    "title": content.get("title"),
                    "path": content.get("path"),
                    "content": content.get("content", "")[:500],
                    "updated_at": content.get("updated_at"),
                    "score": item.score,
                    # 그래프 컨텍스트
                    "mentioned_entities": content.get("mentioned_entities", []),
                    "hierarchy": {
                        "broader": content.get("hierarchy_broader", []),
                        "narrower": content.get("hierarchy_narrower", [])
                    },
                    "related_entities": content.get("related_entities", [])
                }
                notes.append(note)

            logger.info(f"Hybrid search returned {len(notes)} results for: {query[:50]}...")
            return notes

        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            raise

    async def search_text2cypher(
        self,
        query: str,
        vault_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        자연어 → Cypher 변환 검색 (Text2CypherRetriever)

        자연어 질문을 Cypher 쿼리로 변환하여 그래프 검색

        예시 질문:
        - "Machine Learning 관련 노트 보여줘"
        - "프로젝트 Didymos의 할일 목록"
        - "최근 일주일간 수정된 노트"

        Args:
            query: 자연어 질문
            vault_id: 특정 Vault로 필터링 (optional)

        Returns:
            생성된 Cypher 쿼리 + 검색 결과
        """
        try:
            results = self.text2cypher_retriever.search(query_text=query)

            # 결과 구조화
            response = {
                "query": query,
                "generated_cypher": results.metadata.get("cypher") if results.metadata else None,
                "results": []
            }

            for item in results.items:
                response["results"].append(item.content)

            logger.info(f"Text2Cypher search executed for: {query[:50]}...")
            return response

        except Exception as e:
            logger.error(f"Text2Cypher search failed: {e}")
            raise

    async def search_agentic(
        self,
        query: str,
        vault_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Agentic RAG 검색 (ToolsRetriever)

        LLM이 질문을 분석하고 최적의 retriever를 자동 선택합니다.

        예시:
        - "Machine Learning 관련 노트" → VectorRetriever (시맨틱)
        - "우선순위 높은 태스크 목록" → Text2CypherRetriever (구조화)
        - "Transformer 관련 노트와 그 주제들" → VectorCypherRetriever (하이브리드)

        Args:
            query: 자연어 질문
            vault_id: Vault 필터 (optional)

        Returns:
            선택된 retriever 정보 + 검색 결과
        """
        if not TOOLS_RETRIEVER_AVAILABLE or self.tools_retriever is None:
            # fallback to hybrid search
            logger.info("ToolsRetriever not available, falling back to hybrid search")
            results = await self.search_hybrid(query, vault_id=vault_id)
            return {
                "mode": "hybrid",
                "fallback": True,
                "message": "ToolsRetriever not available, used hybrid search",
                "results": results
            }

        try:
            # ToolsRetriever가 자동으로 최적 retriever 선택
            results = self.tools_retriever.search(query_text=query)

            # 결과 구조화
            response = {
                "mode": "agentic",
                "query": query,
                "selected_retriever": results.metadata.get("retriever_name") if results.metadata else None,
                "reasoning": results.metadata.get("reasoning") if results.metadata else None,
                "results": []
            }

            for item in results.items:
                response["results"].append(item.content)

            logger.info(f"Agentic search used {response['selected_retriever']} for: {query[:50]}...")
            return response

        except Exception as e:
            logger.error(f"Agentic search failed: {e}")
            # fallback
            results = await self.search_hybrid(query, vault_id=vault_id)
            return {
                "mode": "hybrid",
                "fallback": True,
                "error": str(e),
                "results": results
            }

    async def search(
        self,
        query: str,
        mode: str = "hybrid",
        top_k: int = 10,
        vault_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        통합 검색 인터페이스

        Args:
            query: 검색 쿼리
            mode: 검색 모드 (vector, hybrid, text2cypher, agentic)
            top_k: 반환할 결과 수
            vault_id: 특정 Vault로 필터링

        Returns:
            검색 결과
        """
        if mode == "vector":
            results = await self.search_vector(query, top_k, vault_id)
            return {"mode": mode, "results": results}

        elif mode == "hybrid":
            results = await self.search_hybrid(query, top_k, vault_id)
            return {"mode": mode, "results": results}

        elif mode == "text2cypher":
            return await self.search_text2cypher(query, vault_id)

        elif mode == "agentic":
            return await self.search_agentic(query, vault_id)

        else:
            raise ValueError(f"Unknown search mode: {mode}")

    def close(self):
        """드라이버 종료"""
        if self.driver:
            self.driver.close()


# 편의 함수
async def get_graphrag_service() -> Optional[GraphRAGRetrieverService]:
    """GraphRAG 서비스 인스턴스 반환 (없으면 None)"""
    if not GRAPHRAG_AVAILABLE:
        return None
    try:
        return await GraphRAGRetrieverService.get_instance()
    except Exception as e:
        logger.error(f"Failed to get GraphRAG service: {e}")
        return None
