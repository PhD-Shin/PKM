"""
Graph Visualization API 라우터
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.services.graph_visualization_service import (
    get_note_graph,
    get_note_graph_vis,
    get_user_graph,
    get_entity_graph
)
from app.services.cluster_service import (
    compute_clusters_louvain,
    compute_clusters_semantic,
    get_cached_clusters,
    save_cluster_cache,
    invalidate_cluster_cache,
    generate_llm_summaries,
    is_cluster_cache_stale
)
from app.services.entity_cluster_service import (
    compute_entity_clusters_hybrid,
    get_cluster_detail
)
from app.schemas.cluster import (
    ClusteredGraphResponse,
    ClusterComputeRequest,
    ClusterUpdateRequest
)
from app.db.neo4j_bolt import Neo4jBoltClient
import logging

logger = logging.getLogger(__name__)


def get_neo4j_client():
    """Neo4j 클라이언트 의존성"""
    from app.config import settings
    return Neo4jBoltClient(
        uri=settings.neo4j_uri,
        username=settings.neo4j_username,
        password=settings.neo4j_password
    )

router = APIRouter(prefix="/graph", tags=["graph"])


class GraphNode(BaseModel):
    """그래프 노드"""
    id: str
    label: str
    type: str
    properties: Dict[str, Any]


class GraphEdge(BaseModel):
    """그래프 엣지"""
    from_: str = None  # Use alias to avoid 'from' keyword
    to: str
    type: str
    label: str

    class Config:
        fields = {'from_': 'from'}


class GraphResponse(BaseModel):
    """그래프 응답"""
    status: str
    count_nodes: int
    count_edges: int
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]


@router.get("/note/{note_id}", response_model=GraphResponse)
async def get_note_graph_view(
    note_id: str,
    depth: int = Query(1, description="탐색 깊이", ge=1, le=3)
):
    """
    특정 노트 중심의 그래프 시각화 데이터

    - note_id: 중심 노트 ID
    - depth: 탐색 깊이 (1~3)
    """
    try:
        graph_data = get_note_graph_vis(note_id=note_id, hops=depth)

        return GraphResponse(
            status="success",
            count_nodes=len(graph_data["nodes"]),
            count_edges=len(graph_data["edges"]),
            nodes=graph_data["nodes"],
            edges=graph_data["edges"]
        )

    except Exception as e:
        logger.error(f"Failed to get note graph: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve graph: {str(e)}"
        )


@router.get("/user/{user_id}", response_model=GraphResponse)
async def get_user_graph_view(
    user_id: str,
    vault_id: Optional[str] = Query(None, description="Vault ID (optional)"),
    limit: int = Query(100, description="최대 노드 개수", ge=10, le=500)
):
    """
    사용자의 전체 지식 그래프

    - user_id: 사용자 ID
    - vault_id: Vault ID (optional)
    - limit: 최대 노드 개수 (기본 100, 최대 5000)
    """
    try:
        graph_data = get_user_graph(
            user_id=user_id,
            vault_id=vault_id,
            limit=limit
        )

        return GraphResponse(
            status="success",
            count_nodes=len(graph_data["nodes"]),
            count_edges=len(graph_data["edges"]),
            nodes=graph_data["nodes"],
            edges=graph_data["edges"]
        )

    except Exception as e:
        logger.error(f"Failed to get user graph: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve graph: {str(e)}"
        )


@router.get("/entities", response_model=GraphResponse)
async def get_entities_graph_view(
    entity_type: Optional[str] = Query(None, description="엔티티 타입 (Topic, Project, Task, Person)"),
    limit: int = Query(50, description="최대 엔티티 개수", ge=10, le=200)
):
    """
    엔티티 중심 그래프

    - entity_type: 필터링할 엔티티 타입 (optional)
    - limit: 최대 엔티티 개수
    """
    try:
        graph_data = get_entity_graph(
            entity_type=entity_type,
            limit=limit
        )

        return GraphResponse(
            status="success",
            count_nodes=len(graph_data["nodes"]),
            count_edges=len(graph_data["edges"]),
            nodes=graph_data["nodes"],
            edges=graph_data["edges"]
        )

    except Exception as e:
        logger.error(f"Failed to get entity graph: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve graph: {str(e)}"
        )


@router.get("/vault/clustered", response_model=ClusteredGraphResponse)
async def get_clustered_vault_graph(
    vault_id: str = Query(..., description="Vault ID"),
    user_token: str = Query(..., description="User token"),
    folder_prefix: str = Query(None, description="폴더 경로 필터 (예: '1_프로젝트/', '2_연구/')"),
    force_recompute: bool = Query(False, description="캐시 무시하고 재계산"),
    target_clusters: int = Query(10, ge=3, le=50, description="목표 클러스터 개수"),
    include_llm: bool = Query(False, description="LLM 요약 포함 (느림)"),
    method: str = Query("semantic", description="클러스터링 방법: 'semantic' (UMAP+HDBSCAN) 또는 'type_based'"),
    warmup: bool = Query(False, description="백그라운드 캐시 워밍업 (응답 즉시 반환)"),
    client: Neo4jBoltClient = Depends(get_neo4j_client)
):
    """
    클러스터링된 Vault 그래프

    - vault_id: Vault ID
    - force_recompute: 캐시 무시하고 재계산
    - target_clusters: 목표 클러스터 개수
    - include_llm: LLM 요약 포함 여부
    - warmup: 백그라운드 캐시 워밍업 (응답 즉시 반환)

    **응답 예시:**
    ```json
    {
      "status": "success",
      "level": 1,
      "cluster_count": 3,
      "total_nodes": 2543,
      "clusters": [
        {
          "id": "cluster_1",
          "name": "Topic Cluster",
          "level": 1,
          "node_count": 45,
          "summary": "Research topics related to...",
          "key_insights": ["Insight 1", "Insight 2"],
          "importance_score": 8.5
        }
      ],
      "edges": [],
      "last_computed": "2024-12-01T10:00:00"
    }
    ```
    """
    try:
        # Warmup 모드: 백그라운드에서 캐시 생성, 즉시 응답 반환
        if warmup:
            import asyncio
            from concurrent.futures import ThreadPoolExecutor

            def background_warmup():
                try:
                    logger.info(f"🔥 Background warmup started for vault {vault_id}")
                    result = compute_clusters_semantic(
                        client=client,
                        vault_id=vault_id,
                        target_clusters=target_clusters
                    )
                    if result.get("clusters"):
                        save_cluster_cache(client, vault_id, result["clusters"], result["method"], edges=result.get("edges", []))
                        logger.info(f"✅ Background warmup completed for vault {vault_id}")
                except Exception as e:
                    logger.error(f"Background warmup failed: {e}")

            executor = ThreadPoolExecutor(max_workers=1)
            executor.submit(background_warmup)

            return ClusteredGraphResponse(
                status="warming_up",
                level=1,
                cluster_count=0,
                total_nodes=0,
                clusters=[],
                edges=[],
                last_computed="warmup_in_progress",
                computation_method="background_warmup"
            )

        # 캐시 키에 folder_prefix 포함
        cache_key = f"{vault_id}:{folder_prefix or 'all'}"

        # 캐시 확인 (folder_prefix가 있으면 캐시 스킵 - 폴더별 캐시는 별도 구현 필요)
        if not force_recompute and not folder_prefix:
            cached = get_cached_clusters(client, vault_id)
            if cached and not is_cluster_cache_stale(client, vault_id, cached.get("computed_at")):
                logger.info(f"✅ Returning cached clusters for vault {vault_id}")
                return ClusteredGraphResponse(
                    status="success",
                    level=1,
                    cluster_count=len(cached["clusters"]),
                    total_nodes=sum(c.get("node_count", 0) for c in cached["clusters"]),
                    clusters=cached["clusters"],
                    edges=cached.get("edges", []),
                    last_computed=cached["computed_at"],
                    computation_method=cached["method"]
                )
            elif cached:
                logger.info(f"♻️ Cache stale for vault {vault_id}, recomputing...")

        # 클러스터 계산 (방법 선택)
        folder_info = f" in folder '{folder_prefix}'" if folder_prefix else ""
        logger.info(f"🔄 Computing clusters for vault {vault_id}{folder_info} using method={method}")
        method_normalized = method.lower()

        if method_normalized in ["semantic", "auto"]:
            result = compute_clusters_semantic(
                client=client,
                vault_id=vault_id,
                target_clusters=target_clusters,
                folder_prefix=folder_prefix
            )
        elif method_normalized in ["type_based", "type"]:
            result = compute_clusters_louvain(
                client=client,
                vault_id=vault_id,
                target_clusters=target_clusters,
                folder_prefix=folder_prefix
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid clustering method")

        # 의미론적 클러스터링이 실패했거나 결과가 없으면 폴백
        if method_normalized in ["semantic", "auto"] and (not result.get("clusters")):
            logger.info("Semantic clustering returned no clusters. Falling back to type-based.")
            result = compute_clusters_louvain(
                client=client,
                vault_id=vault_id,
                target_clusters=target_clusters,
                folder_prefix=folder_prefix
            )
            result["method"] = "semantic_fallback"

        clusters = result["clusters"]
        edges = result.get("edges", [])

        # LLM 요약 생성 (옵션)
        if include_llm and len(clusters) > 0:
            logger.info("🤖 Generating LLM summaries with GPT-5 Mini...")
            clusters = generate_llm_summaries(client, vault_id, clusters)

        # 캐시 저장 (folder_prefix 없을 때만)
        if not folder_prefix:
            save_cluster_cache(client, vault_id, clusters, result["method"], edges=edges)

        return ClusteredGraphResponse(
            status="success",
            level=1,
            cluster_count=len(clusters),
            total_nodes=result["total_nodes"],
            clusters=clusters,
            edges=edges,
            last_computed=result["computed_at"],
            computation_method=result["method"]
        )

    except Exception as e:
        logger.error(f"Failed to get clustered graph: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compute clusters: {str(e)}"
        )


@router.post("/vault/clustered/invalidate")
async def invalidate_clusters(
    vault_id: str = Query(..., description="Vault ID"),
    user_token: str = Query(..., description="User token"),
    client: Neo4jBoltClient = Depends(get_neo4j_client)
):
    """
    클러스터 캐시 무효화 (노트 업데이트 후 호출)

    - vault_id: Vault ID
    """
    try:
        success = invalidate_cluster_cache(client, vault_id)

        if success:
            return {"status": "success", "message": "Cluster cache invalidated"}
        else:
            raise HTTPException(status_code=500, detail="Failed to invalidate cache")

    except Exception as e:
        logger.error(f"Failed to invalidate cluster cache: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to invalidate cache: {str(e)}"
        )


@router.post("/vault/reset-entities")
async def reset_vault_entities(
    vault_id: str = Query(..., description="Vault ID"),
    user_token: str = Query(..., description="User token"),
    client: Neo4jBoltClient = Depends(get_neo4j_client)
):
    """
    🔴 Vault 엔티티 완전 초기화 (MVP 개발용)

    - 모든 Topic, Project, Task, Person 엔티티 삭제
    - MENTIONS 관계 삭제
    - 클러스터 캐시 무효화
    - Note 노드는 유지

    ⚠️ 이 작업은 되돌릴 수 없습니다!
    """
    try:
        # 1. Vault에 연결된 엔티티와 관계 삭제
        cypher_delete_entities = """
        MATCH (v:Vault {id: $vault_id})-[:HAS_NOTE]->(n:Note)-[m:MENTIONS]->(e)
        WHERE e:Topic OR e:Project OR e:Task OR e:Person
        DELETE m
        WITH DISTINCT e
        WHERE NOT (e)--()
        DELETE e
        RETURN count(e) as deleted_entities
        """

        result1 = client.query(cypher_delete_entities, {"vault_id": vault_id})
        deleted_entities = result1[0]["deleted_entities"] if result1 else 0

        # 2. 고아 엔티티 정리 (다른 vault에서도 사용되지 않는 경우)
        cypher_cleanup_orphans = """
        MATCH (e)
        WHERE (e:Topic OR e:Project OR e:Task OR e:Person)
          AND NOT (e)--()
        DELETE e
        RETURN count(e) as orphans_deleted
        """

        result2 = client.query(cypher_cleanup_orphans, {})
        orphans_deleted = result2[0]["orphans_deleted"] if result2 else 0

        # 3. 엔티티 간 관계도 정리
        cypher_delete_entity_relations = """
        MATCH (v:Vault {id: $vault_id})-[:HAS_NOTE]->(n:Note)
        WITH COLLECT(n.note_id) as note_ids
        MATCH (e1)-[r:RELATED_TO|PART_OF]->(e2)
        WHERE (e1:Topic OR e1:Project OR e1:Task OR e1:Person)
          AND (e2:Topic OR e2:Project OR e2:Task OR e2:Person)
        DELETE r
        RETURN count(r) as relations_deleted
        """

        result3 = client.query(cypher_delete_entity_relations, {"vault_id": vault_id})
        relations_deleted = result3[0]["relations_deleted"] if result3 else 0

        # 4. 클러스터 캐시 무효화
        invalidate_cluster_cache(client, vault_id)

        logger.info(f"🔴 Reset entities for vault {vault_id}: {deleted_entities} entities, {orphans_deleted} orphans, {relations_deleted} relations")

        return {
            "status": "success",
            "message": "Vault entities reset complete",
            "deleted_entities": deleted_entities,
            "orphans_deleted": orphans_deleted,
            "relations_deleted": relations_deleted
        }

    except Exception as e:
        logger.error(f"Failed to reset vault entities: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset entities: {str(e)}"
        )


@router.get("/vault/folders")
async def get_vault_folders(
    vault_id: str = Query(..., description="Vault ID"),
    user_token: str = Query(..., description="User token"),
    client: Neo4jBoltClient = Depends(get_neo4j_client)
):
    """
    Vault 내 폴더 목록 조회 (PARA 노트 기법 지원)

    폴더별 노트 개수와 함께 반환합니다.
    """
    try:
        # 노트 경로에서 폴더 추출
        cypher = """
        MATCH (v:Vault {id: $vault_id})-[:HAS_NOTE]->(n:Note)
        WITH n.note_id AS note_id
        WITH split(note_id, '/')[0] AS folder
        WHERE folder IS NOT NULL AND folder <> ''
        RETURN folder, count(*) AS note_count
        ORDER BY note_count DESC
        """

        result = client.query(cypher, {"vault_id": vault_id})

        folders = [
            {"folder": r["folder"], "note_count": r["note_count"]}
            for r in (result or [])
        ]

        return {
            "status": "success",
            "vault_id": vault_id,
            "total_folders": len(folders),
            "folders": folders
        }

    except Exception as e:
        logger.error(f"Failed to get vault folders: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get folders: {str(e)}"
        )


@router.get("/debug/stats")
async def get_debug_stats(
    vault_id: str = Query(..., description="Vault ID"),
    client: Neo4jBoltClient = Depends(get_neo4j_client)
):
    """
    디버그용: Neo4j 데이터 통계 확인
    """
    try:
        # 1. Vault 존재 확인
        vault_check = client.query(
            "MATCH (v:Vault {id: $vault_id}) RETURN v.id AS id",
            {"vault_id": vault_id}
        )

        # 2. 전체 Note 수
        total_notes = client.query(
            "MATCH (n:Note) RETURN count(n) AS count",
            {}
        )

        # 3. Vault에 연결된 Note 수
        vault_notes = client.query(
            "MATCH (v:Vault {id: $vault_id})-[:HAS_NOTE]->(n:Note) RETURN count(n) AS count",
            {"vault_id": vault_id}
        )

        # 4. 임베딩이 있는 Note 수
        notes_with_embedding = client.query(
            "MATCH (v:Vault {id: $vault_id})-[:HAS_NOTE]->(n:Note) WHERE n.embedding IS NOT NULL RETURN count(n) AS count",
            {"vault_id": vault_id}
        )

        # 5. 전체 Vault 목록
        all_vaults = client.query(
            "MATCH (v:Vault) RETURN v.id AS id LIMIT 10",
            {}
        )

        # 6. 엔티티 수 (Topic, Project, Task, Person)
        entity_counts = client.query(
            """
            MATCH (v:Vault {id: $vault_id})-[:HAS_NOTE]->(n:Note)-[:MENTIONS]->(e)
            WHERE e:Topic OR e:Project OR e:Task OR e:Person
            WITH labels(e)[0] AS entity_type, count(DISTINCT e) AS cnt
            RETURN entity_type, cnt
            """,
            {"vault_id": vault_id}
        )

        # 7. Note-Entity MENTIONS 관계 수
        mentions_count = client.query(
            """
            MATCH (v:Vault {id: $vault_id})-[:HAS_NOTE]->(n:Note)-[m:MENTIONS]->(e)
            RETURN count(m) AS count
            """,
            {"vault_id": vault_id}
        )

        entity_stats = {r["entity_type"]: r["cnt"] for r in (entity_counts or [])}

        return {
            "vault_id_queried": vault_id,
            "vault_exists": len(vault_check or []) > 0,
            "all_vaults": [v["id"] for v in (all_vaults or [])],
            "total_notes_in_db": (total_notes[0]["count"] if total_notes else 0),
            "notes_in_vault": (vault_notes[0]["count"] if vault_notes else 0),
            "notes_with_embedding": (notes_with_embedding[0]["count"] if notes_with_embedding else 0),
            "entity_counts": entity_stats,
            "total_mentions": (mentions_count[0]["count"] if mentions_count else 0),
        }

    except Exception as e:
        logger.error(f"Debug stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/migrate/graphiti-to-hybrid")
async def migrate_graphiti_to_hybrid(
    vault_id: str = Query(None, description="Vault ID (optional, all if not specified)"),
    max_iterations: int = Query(10, description="Maximum migration iterations")
) -> Dict[str, Any]:
    """
    Graphiti Entity에 PKM 레이블 추가 마이그레이션

    Graphiti가 생성한 Entity에 Topic/Project/Task/Person 레이블을 추가하여
    cluster_service와 호환되도록 합니다.

    Note: Graphiti uses 'Entity' and 'Episodic' labels (NOT 'EntityNode' or 'EpisodicNode')

    이 작업은 다음을 수행합니다:
    1. Entity에 PKM 타입 레이블 추가 (Topic, Project, Task, Person)
    2. Episodic-Entity MENTIONS 관계를 Note-Entity MENTIONS로 변환
    """
    try:
        from app.services.hybrid_graphiti_service import migrate_graphiti_to_hybrid

        logger.info(f"Starting Graphiti → Hybrid migration (vault: {vault_id or 'all'})")

        result = await migrate_graphiti_to_hybrid(
            vault_id=vault_id,
            max_iterations=max_iterations
        )

        return {
            "status": "success",
            "migration_result": result
        }

    except Exception as e:
        logger.error(f"Migration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/debug/entity-nodes")
async def get_entity_node_stats() -> Dict[str, Any]:
    """
    Graphiti Entity 통계 조회

    Entity (Graphiti) 중 PKM 레이블이 있는 것과 없는 것의 수를 확인합니다.
    Note: Graphiti uses 'Entity' label (NOT 'EntityNode')
    """
    try:
        client = get_neo4j_client()

        # 모든 노드 레이블 조회
        all_labels = client.query("CALL db.labels() YIELD label RETURN label ORDER BY label", {})

        # Entity 전체 수 (Graphiti uses 'Entity' label)
        total = client.query("MATCH (e:Entity) RETURN count(e) as count", {})

        # Episodic 노드 수 (Graphiti episodes)
        episodic_count = client.query("MATCH (e:Episodic) RETURN count(e) as count", {})

        # PKM 레이블이 있는 Entity
        with_pkm = client.query("""
            MATCH (e:Entity)
            WHERE e:Topic OR e:Project OR e:Task OR e:Person
            RETURN count(e) as count
        """, {})

        # PKM 레이블이 없는 Entity
        without_pkm = client.query("""
            MATCH (e:Entity)
            WHERE NOT e:Topic AND NOT e:Project AND NOT e:Task AND NOT e:Person
            RETURN count(e) as count
        """, {})

        # PKM 타입별 통계
        by_type = client.query("""
            MATCH (e:Entity)
            WHERE e:Topic OR e:Project OR e:Task OR e:Person
            WITH CASE
                WHEN e:Topic THEN 'Topic'
                WHEN e:Project THEN 'Project'
                WHEN e:Task THEN 'Task'
                WHEN e:Person THEN 'Person'
            END as pkm_type
            RETURN pkm_type, count(*) as count
        """, {})

        # Note -> Entity MENTIONS 관계 수
        note_entity_mentions = client.query("""
            MATCH (n:Note)-[m:MENTIONS]->(e:Entity)
            RETURN count(m) as count
        """, {})

        # Episodic -> Entity MENTIONS 관계 수 (Graphiti)
        episodic_entity_mentions = client.query("""
            MATCH (ep:Episodic)-[m:MENTIONS]->(e:Entity)
            RETURN count(m) as count
        """, {})

        return {
            "all_labels": [r["label"] for r in (all_labels or [])],
            "total_entities": total[0]["count"] if total else 0,
            "total_episodic": episodic_count[0]["count"] if episodic_count else 0,
            "with_pkm_labels": with_pkm[0]["count"] if with_pkm else 0,
            "without_pkm_labels": without_pkm[0]["count"] if without_pkm else 0,
            "by_pkm_type": {r["pkm_type"]: r["count"] for r in (by_type or [])},
            "note_entity_mentions": note_entity_mentions[0]["count"] if note_entity_mentions else 0,
            "episodic_entity_mentions": episodic_entity_mentions[0]["count"] if episodic_entity_mentions else 0
        }

    except Exception as e:
        logger.error(f"Entity stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vault/entities")
async def get_vault_entity_graph(
    vault_id: str = Query(..., description="Vault ID"),
    user_token: str = Query(..., description="User token"),
    limit: int = Query(200, description="Maximum entities to return", ge=10, le=1000),
    min_connections: int = Query(1, description="Minimum RELATES_TO connections", ge=0),
    include_notes: bool = Query(False, description="Include connected notes")
) -> Dict[str, Any]:
    """
    Entity Graph 시각화를 위한 데이터 반환

    클러스터 대신 Entity 노드와 RELATES_TO 관계를 직접 반환하여
    진정한 Knowledge Graph 시각화를 지원합니다.

    - Entity = 노드 (타입별 색상: Topic=파랑, Project=초록, Person=주황, Task=빨강)
    - RELATES_TO = 엣지 (의미론적 연결)
    """
    try:
        client = get_neo4j_client()

        # Step 1: Entity들 조회 (RELATES_TO 관계가 있는 것)
        # Graphiti는 Episodic-[:MENTIONS]->Entity 구조를 사용하므로
        # Entity를 직접 조회하고 RELATES_TO 관계로 필터링
        cypher_entities = """
        MATCH (e:Entity)
        OPTIONAL MATCH (e)-[r:RELATES_TO]-(other:Entity)
        WITH e, count(r) as connection_count
        WHERE connection_count >= $min_connections
        RETURN
            e.uuid as id,
            e.name as name,
            e.summary as summary,
            CASE
                WHEN e:Person THEN 'Person'
                WHEN e:Project THEN 'Project'
                WHEN e:Task THEN 'Task'
                ELSE 'Topic'
            END as type,
            connection_count
        ORDER BY connection_count DESC
        LIMIT $limit
        """

        entities = client.query(cypher_entities, {
            "vault_id": vault_id,
            "min_connections": min_connections,
            "limit": limit
        })

        if not entities:
            return {
                "status": "success",
                "node_count": 0,
                "edge_count": 0,
                "nodes": [],
                "edges": [],
                "stats": {"by_type": {}}
            }

        entity_ids = [e["id"] for e in entities]

        # Step 2: Entity 간 RELATES_TO 관계 조회
        cypher_relations = """
        MATCH (e1:Entity)-[r:RELATES_TO]->(e2:Entity)
        WHERE e1.uuid IN $entity_ids AND e2.uuid IN $entity_ids
        RETURN DISTINCT
            e1.uuid as source,
            e2.uuid as target,
            type(r) as rel_type,
            r.fact as fact
        """

        relations = client.query(cypher_relations, {"entity_ids": entity_ids})

        # Step 3: 노드 데이터 구성
        nodes = []
        type_colors = {
            "Topic": "#3498db",    # 파랑
            "Project": "#2ecc71",  # 초록
            "Person": "#e67e22",   # 주황
            "Task": "#e74c3c"      # 빨강
        }

        for e in entities:
            node = {
                "id": e["id"],
                "label": e["name"] or e["id"][:20],
                "type": e["type"],
                "color": type_colors.get(e["type"], "#95a5a6"),
                "size": min(30, 10 + e["connection_count"] * 2),  # 연결 수에 따라 크기
                "summary": e.get("summary", ""),
                "connections": e["connection_count"]
            }
            nodes.append(node)

        # Step 4: 엣지 데이터 구성
        edges = []
        for r in (relations or []):
            edge = {
                "source": r["source"],
                "target": r["target"],
                "type": r["rel_type"],
                "label": r.get("fact", "")[:50] if r.get("fact") else ""
            }
            edges.append(edge)

        # Step 5: 연결된 노트 정보 (선택적)
        note_connections = {}
        if include_notes:
            cypher_notes = """
            MATCH (n:Note)-[:MENTIONS]->(e:Entity)
            WHERE e.uuid IN $entity_ids
            RETURN e.uuid as entity_id, collect(DISTINCT n.note_id)[..5] as note_ids
            """
            note_results = client.query(cypher_notes, {"entity_ids": entity_ids})
            for nr in (note_results or []):
                note_connections[nr["entity_id"]] = nr["note_ids"]

            # 노드에 note 정보 추가
            for node in nodes:
                node["connected_notes"] = note_connections.get(node["id"], [])

        # 타입별 통계
        stats = {"by_type": {}}
        for e in entities:
            t = e["type"]
            stats["by_type"][t] = stats["by_type"].get(t, 0) + 1

        return {
            "status": "success",
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes,
            "edges": edges,
            "stats": stats
        }

    except Exception as e:
        logger.error(f"Entity graph error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vault/entity-clusters")
async def get_entity_clusters(
    vault_id: str = Query(..., description="Vault ID"),
    user_token: str = Query(..., description="User token"),
    folder_prefix: str = Query(None, description="폴더 경로 필터 (예: '1_프로젝트/'). 해당 폴더 노트의 엔티티만 클러스터링"),
    min_cluster_size: int = Query(3, description="Minimum entities per cluster", ge=2, le=20),
    resolution: float = Query(1.0, description="Louvain resolution (higher = more clusters)", ge=0.5, le=3.0),
    min_connections: int = Query(1, description="최소 연결 노트 수 (기본 1 = 모든 엔티티 포함, 2 = 2개 이상 노트에서 언급된 엔티티만)", ge=1, le=10),
    client: Neo4jBoltClient = Depends(get_neo4j_client)
) -> Dict[str, Any]:
    """
    하이브리드 Entity 클러스터링

    RELATES_TO 그래프 구조 + name_embedding 벡터 유사도를 결합하여
    Entity들을 의미론적 클러스터로 그룹핑합니다.

    2nd Brain 시각화를 위한 클러스터 뷰:
    - 각 클러스터는 시멘틱하게 유사한 개념들의 그룹
    - 클러스터 간 연결은 RELATES_TO 관계에 기반
    - 클러스터 내 엔티티들은 펼쳐서 볼 수 있음

    **알고리즘:**
    1. RELATES_TO 그래프에서 Louvain 커뮤니티 탐지
    2. name_embedding으로 HDBSCAN 클러스터링
    3. 두 결과를 병합하여 최종 클러스터 결정

    **응답 예시:**
    ```json
    {
      "status": "success",
      "cluster_count": 15,
      "total_entities": 635,
      "clusters": [
        {
          "id": "cluster_0",
          "name": "Knowledge Graph",
          "entity_count": 42,
          "sample_entities": ["PKM", "Obsidian", "Neo4j", ...],
          "type_distribution": {"Topic": 35, "Project": 7},
          "cohesion_score": 0.85
        }
      ],
      "edges": [
        {"from": "cluster_0", "to": "cluster_1", "weight": 5}
      ]
    }
    ```
    """
    try:
        folder_info = f" for folder '{folder_prefix}'" if folder_prefix else ""
        logger.info(f"Computing entity clusters for vault {vault_id}{folder_info} (min_connections={min_connections})")

        result = compute_entity_clusters_hybrid(
            client=client,
            min_cluster_size=min_cluster_size,
            resolution=resolution,
            folder_prefix=folder_prefix,
            min_connections=min_connections
        )

        return {
            "status": "success",
            "cluster_count": len(result["clusters"]),
            "total_entities": result["total_entities"],
            "clustered_entities": result.get("clustered_entities", 0),
            "clusters": result["clusters"],
            "edges": result["edges"],
            "method": result["method"],
            "computed_at": result["computed_at"]
        }

    except Exception as e:
        logger.error(f"Entity clustering error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vault/cleanup-orphan-entities")
async def cleanup_orphan_entities(
    vault_id: str = Query(..., description="Vault ID"),
    user_token: str = Query(..., description="User token"),
    dry_run: bool = Query(True, description="미리보기 모드 (실제 삭제 안함)"),
    client: Neo4jBoltClient = Depends(get_neo4j_client)
) -> Dict[str, Any]:
    """
    고아 엔티티 정리

    어떤 Note에도 연결되지 않은 (MENTIONS 관계가 없는) 엔티티를 정리합니다.
    dry_run=True (기본값)면 삭제할 엔티티 목록만 반환합니다.
    dry_run=False면 실제로 삭제합니다.

    참고: 단일 노트 연결 엔티티는 삭제하지 않음 (나중에 커질 수 있음)
    """
    try:
        # 고아 Entity 조회 (MENTIONS 관계가 전혀 없는)
        cypher_orphan_entities = """
        MATCH (e:Entity)
        WHERE NOT (e)<-[:MENTIONS]-(:Note)
          AND NOT (e)<-[:MENTIONS]-(:Episodic)
        RETURN e.uuid as uuid, e.name as name
        """
        orphan_entities = client.query(cypher_orphan_entities, {})

        if dry_run:
            return {
                "status": "preview",
                "message": f"Found {len(orphan_entities or [])} orphan entities. Set dry_run=false to delete.",
                "orphan_count": len(orphan_entities or []),
                "sample_entities": [{"uuid": e["uuid"], "name": e["name"]} for e in (orphan_entities or [])[:50]]
            }

        # 실제 삭제 실행
        cypher_cleanup_orphans = """
        MATCH (e:Entity)
        WHERE NOT (e)<-[:MENTIONS]-(:Note)
          AND NOT (e)<-[:MENTIONS]-(:Episodic)
        WITH e
        OPTIONAL MATCH (e)-[r]-()
        DELETE r, e
        RETURN count(e) as count
        """
        cleanup_result = client.query(cypher_cleanup_orphans, {})
        deleted_entities = cleanup_result[0]["count"] if cleanup_result else 0

        logger.info(f"🧹 Cleaned up {deleted_entities} orphan entities")

        return {
            "status": "success",
            "message": f"Cleaned up {deleted_entities} orphan entities",
            "deleted_entities": deleted_entities
        }

    except Exception as e:
        logger.error(f"Cleanup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/debug/entity-relations")
async def debug_entity_relations(
    client: Neo4jBoltClient = Depends(get_neo4j_client)
) -> Dict[str, Any]:
    """
    디버그용: Entity 간 관계 타입 확인
    """
    try:
        # 모든 Entity 간 관계 타입 조회
        cypher = """
        MATCH (e1:Entity)-[r]->(e2:Entity)
        RETURN type(r) as rel_type, count(*) as count
        ORDER BY count DESC
        LIMIT 20
        """
        results = client.query(cypher, {})

        # 샘플 관계 조회
        cypher_sample = """
        MATCH (e1:Entity)-[r]->(e2:Entity)
        RETURN e1.name as from_name, type(r) as rel_type, e2.name as to_name,
               r.fact as fact
        LIMIT 10
        """
        samples = client.query(cypher_sample, {})

        return {
            "status": "success",
            "relation_types": [{"type": r["rel_type"], "count": r["count"]} for r in results or []],
            "samples": [
                {
                    "from": r["from_name"],
                    "type": r["rel_type"],
                    "to": r["to_name"],
                    "fact": r.get("fact", "")
                }
                for r in samples or []
            ]
        }
    except Exception as e:
        logger.error(f"Debug error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class EntityClusterDetailRequest(BaseModel):
    """클러스터 상세 조회 요청"""
    cluster_name: str
    entity_uuids: List[str]


@router.post("/vault/entity-clusters/detail")
async def get_entity_cluster_detail_by_uuids(
    request: EntityClusterDetailRequest,
    vault_id: str = Query(..., description="Vault ID"),
    user_token: str = Query(..., description="User token"),
    client: Neo4jBoltClient = Depends(get_neo4j_client)
) -> Dict[str, Any]:
    """
    클러스터 엔티티 목록으로 상세 정보 조회

    프론트엔드에서 저장한 entity_uuids를 직접 전달받아 상세 정보를 반환합니다.
    클러스터링 결과의 일관성을 보장합니다.
    """
    try:
        uuids = request.entity_uuids
        cluster_name = request.cluster_name

        if not uuids:
            raise HTTPException(status_code=400, detail="entity_uuids is required")

        # 엔티티 상세 정보 조회
        cypher = """
        MATCH (e:Entity)
        WHERE e.uuid IN $uuids
        OPTIONAL MATCH (e)-[r:RELATES_TO]-(other:Entity)
        WHERE other.uuid IN $uuids
        RETURN e.uuid as uuid,
               e.name as name,
               e.summary as summary,
               e.pkm_type as pkm_type,
               count(r) as internal_connections
        ORDER BY internal_connections DESC
        """

        results = client.query(cypher, {"uuids": uuids})

        entities = []
        type_distribution = {}
        for row in results or []:
            pkm_type = row.get("pkm_type", "Topic")
            entities.append({
                "uuid": row["uuid"],
                "name": row["name"],
                "summary": row.get("summary", ""),
                "pkm_type": pkm_type,
                "connections": row.get("internal_connections", 0)
            })
            type_distribution[pkm_type] = type_distribution.get(pkm_type, 0) + 1

        # 내부 관계들 (모든 Entity 간 관계)
        # Graphiti는 다양한 관계 타입을 생성할 수 있음 (RELATES_TO, BROADER, NARROWER 등)
        cypher_edges = """
        MATCH (e1:Entity)-[r]->(e2:Entity)
        WHERE e1.uuid IN $uuids AND e2.uuid IN $uuids
        RETURN e1.uuid as from_uuid, e2.uuid as to_uuid,
               type(r) as rel_type,
               r.fact as fact,
               COALESCE(r.weight, 1.0) as weight
        """

        edge_results = client.query(cypher_edges, {"uuids": uuids})

        edges = []
        for row in edge_results or []:
            edges.append({
                "from": row["from_uuid"],
                "to": row["to_uuid"],
                "type": row.get("rel_type", "RELATES_TO"),
                "fact": row.get("fact", ""),
                "weight": row.get("weight", 1.0)
            })

        # 관련 노트 조회 (엔티티들이 MENTIONS된 노트들)
        cypher_notes = """
        MATCH (n:Note)-[:MENTIONS]->(e:Entity)
        WHERE e.uuid IN $uuids
        RETURN n.note_id as note_id,
               n.title as title,
               n.path as path,
               collect(DISTINCT e.uuid) as entity_uuids,
               collect(DISTINCT e.name) as entity_names
        ORDER BY size(entity_uuids) DESC
        LIMIT 50
        """

        note_results = client.query(cypher_notes, {"uuids": uuids})

        related_notes = []
        for row in note_results or []:
            related_notes.append({
                "note_id": row["note_id"],
                "title": row.get("title", row["note_id"]),
                "path": row.get("path", ""),
                "entity_uuids": row.get("entity_uuids", []),
                "entity_names": row.get("entity_names", []),
                "entity_count": len(row.get("entity_uuids", []))
            })

        return {
            "status": "success",
            "cluster": {
                "name": cluster_name,
                "entity_count": len(entities),
                "entity_uuids": uuids,
                "type_distribution": type_distribution,
                "entities": entities,
                "internal_edges": edges,
                "related_notes": related_notes
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cluster detail error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vault/entity-note-graph")
async def get_entity_note_graph(
    vault_id: str = Query(..., description="Vault ID"),
    user_token: str = Query(..., description="User token"),
    folder_prefix: str = Query(None, description="폴더 경로 필터"),
    limit: int = Query(100, description="최대 엔티티 수", ge=10, le=500),
    min_note_connections: int = Query(2, description="최소 노트 연결 수 (2 = 2개 이상 노트에서 언급된 엔티티만)", ge=1),
    client: Neo4jBoltClient = Depends(get_neo4j_client)
) -> Dict[str, Any]:
    """
    Entity-Note 연결 그래프 (2nd Brain 시각화용)

    Entity를 통해 Note 간 연결을 보여줍니다:
    - Entity가 2개 이상의 Note에서 MENTIONS되면, 그 Note들은 "연결된" 것
    - Entity 노드 + Note 노드를 함께 시각화
    - Note 간 실제 연결성 파악 가능

    **응답 예시:**
    ```json
    {
      "entities": [
        {"id": "uuid", "name": "PKM", "type": "Topic", "connected_notes": ["note1.md", "note2.md"]}
      ],
      "notes": [
        {"id": "note1.md", "title": "Note 1", "connected_entities": ["uuid1", "uuid2"]}
      ],
      "entity_note_edges": [
        {"entity_id": "uuid", "note_id": "note1.md"}
      ],
      "note_note_edges": [
        {"from": "note1.md", "to": "note2.md", "shared_entities": ["uuid1"], "strength": 3}
      ]
    }
    ```
    """
    try:
        # 폴더 필터 조건
        folder_condition = "n.note_id STARTS WITH $folder_prefix AND" if folder_prefix else ""
        folder_condition2 = "n2.note_id STARTS WITH $folder_prefix AND" if folder_prefix else ""

        # Step 1: 여러 노트에서 언급된 엔티티들 조회
        # 두 가지 경로 지원:
        # 1. Note -[:MENTIONS]-> Entity (hybrid_graphiti_service가 생성한 직접 관계)
        # 2. Episodic -[:MENTIONS]-> Entity (Graphiti가 생성한 관계, Note.note_id = Episodic.name)
        cypher_entities = f"""
        // 방법1: 직접 MENTIONS 관계
        MATCH (n:Note)-[:MENTIONS]->(e:Entity)
        WHERE {folder_condition} e.name IS NOT NULL
        WITH e, collect(DISTINCT n.note_id) as direct_notes

        // 방법2: Episodic 통한 연결 (UNION)
        RETURN e.uuid as uuid, e.name as name, e.summary as summary,
               CASE
                   WHEN e:Goal THEN 'Goal'
                   WHEN e:Project THEN 'Project'
                   WHEN e:Task THEN 'Task'
                   WHEN e:Concept THEN 'Concept'
                   WHEN e:Question THEN 'Question'
                   WHEN e:Insight THEN 'Insight'
                   WHEN e:Resource THEN 'Resource'
                   WHEN e:Person THEN 'Person'
                   ELSE 'Topic'
               END as type,
               direct_notes as note_ids,
               size(direct_notes) as note_count

        UNION

        // Episodic 기반 연결 (Episodic.name = 'note_' + Note.note_id)
        MATCH (ep:Episodic)-[:MENTIONS]->(e:Entity)
        WHERE e.name IS NOT NULL AND ep.name IS NOT NULL AND ep.name STARTS WITH 'note_'
        WITH e, ep, replace(ep.name, 'note_', '') as derived_note_id
        MATCH (n2:Note)
        WHERE {folder_condition2} n2.note_id = derived_note_id
        WITH e, collect(DISTINCT n2.note_id) as episodic_notes
        WHERE size(episodic_notes) > 0
        RETURN e.uuid as uuid, e.name as name, e.summary as summary,
               CASE
                   WHEN e:Goal THEN 'Goal'
                   WHEN e:Project THEN 'Project'
                   WHEN e:Task THEN 'Task'
                   WHEN e:Concept THEN 'Concept'
                   WHEN e:Question THEN 'Question'
                   WHEN e:Insight THEN 'Insight'
                   WHEN e:Resource THEN 'Resource'
                   WHEN e:Person THEN 'Person'
                   ELSE 'Topic'
               END as type,
               episodic_notes as note_ids,
               size(episodic_notes) as note_count
        """

        params = {
            "folder_prefix": folder_prefix or "",
            "min_note_connections": min_note_connections,
            "limit": limit
        }

        entities_result = client.query(cypher_entities, params)

        if not entities_result:
            return {
                "status": "success",
                "entity_count": 0,
                "note_count": 0,
                "entities": [],
                "notes": [],
                "entity_note_edges": [],
                "note_note_edges": [],
                "insights": {}
            }

        # UNION 결과에서 같은 엔티티의 note_ids를 합쳐야 함
        entity_map = {}  # uuid -> {name, summary, type, note_ids}
        for row in entities_result:
            uuid = row["uuid"]
            if uuid not in entity_map:
                entity_map[uuid] = {
                    "name": row["name"],
                    "summary": row.get("summary", ""),
                    "type": row["type"],
                    "note_ids": set(row["note_ids"] or [])
                }
            else:
                # 기존 엔티티에 note_ids 추가
                entity_map[uuid]["note_ids"].update(row["note_ids"] or [])

        # min_note_connections 필터 적용 및 정렬
        filtered_entities = [
            (uuid, data) for uuid, data in entity_map.items()
            if len(data["note_ids"]) >= min_note_connections
        ]
        # note_count 내림차순 정렬 후 limit 적용
        filtered_entities.sort(key=lambda x: len(x[1]["note_ids"]), reverse=True)
        filtered_entities = filtered_entities[:limit]

        # Entity 데이터 구성
        entities = []
        all_note_ids = set()
        entity_note_edges = []

        # PKM Core Ontology v2 - 8개 타입 + Person 색상
        type_colors = {
            "Goal": "#9b59b6",      # 보라색 - 최상위 목표
            "Project": "#2ecc71",   # 초록색 - 프로젝트
            "Task": "#e74c3c",      # 빨간색 - 태스크
            "Topic": "#3498db",     # 파란색 - 주제
            "Concept": "#1abc9c",   # 청록색 - 개념
            "Question": "#f39c12",  # 주황색 - 질문
            "Insight": "#e91e63",   # 분홍색 - 인사이트
            "Resource": "#607d8b",  # 회색 - 자료
            "Person": "#e67e22",    # 오렌지색 - 인물 (하위호환)
        }

        for uuid, data in filtered_entities:
            note_ids_list = list(data["note_ids"])
            entity = {
                "id": uuid,
                "name": data["name"] or "Unknown",
                "summary": data["summary"],
                "type": data["type"],
                "color": type_colors.get(data["type"], "#95a5a6"),
                "connected_notes": note_ids_list,
                "note_count": len(note_ids_list)
            }
            entities.append(entity)

            # Entity-Note 엣지 추가
            for note_id in note_ids_list:
                all_note_ids.add(note_id)
                entity_note_edges.append({
                    "entity_id": uuid,
                    "note_id": note_id
                })

        # Step 2: Note 데이터 조회
        notes = []
        if all_note_ids:
            cypher_notes = """
            MATCH (n:Note)
            WHERE n.note_id IN $note_ids
            RETURN n.note_id as note_id,
                   n.title as title,
                   n.path as path
            """
            notes_result = client.query(cypher_notes, {"note_ids": list(all_note_ids)})

            for row in notes_result or []:
                notes.append({
                    "id": row["note_id"],
                    "title": row.get("title") or row["note_id"].split("/")[-1].replace(".md", ""),
                    "path": row.get("path", row["note_id"])
                })

        # Step 3: Note-Note 연결 계산 (공유 Entity 기반)
        note_note_edges = []
        note_shared_entities = {}  # {(note1, note2): [entity_ids]}

        for entity in entities:
            note_list = entity["connected_notes"]
            if len(note_list) >= 2:
                # 모든 노트 쌍에 대해 공유 Entity 기록
                for i in range(len(note_list)):
                    for j in range(i + 1, len(note_list)):
                        pair = tuple(sorted([note_list[i], note_list[j]]))
                        if pair not in note_shared_entities:
                            note_shared_entities[pair] = []
                        note_shared_entities[pair].append(entity["id"])

        for (note1, note2), shared_entities in note_shared_entities.items():
            note_note_edges.append({
                "from": note1,
                "to": note2,
                "shared_entities": shared_entities,
                "strength": len(shared_entities)
            })

        # 연결 강도순 정렬
        note_note_edges.sort(key=lambda x: x["strength"], reverse=True)

        return {
            "status": "success",
            "entity_count": len(entities),
            "note_count": len(notes),
            "edge_count": len(note_note_edges),
            "entities": entities,
            "notes": notes,
            "entity_note_edges": entity_note_edges,
            "note_note_edges": note_note_edges[:200]  # 상위 200개 연결만
        }

    except Exception as e:
        logger.error(f"Entity-Note graph error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vault/thinking-insights")
async def get_thinking_insights(
    vault_id: str = Query(..., description="Vault ID"),
    user_token: str = Query(..., description="User token"),
    folder_prefix: str = Query(None, description="폴더 경로 필터"),
    client: Neo4jBoltClient = Depends(get_neo4j_client)
) -> Dict[str, Any]:
    """
    사고 패턴 인사이트 (Palantir Foundry 스타일)

    노트와 엔티티 분석을 통해:
    1. **집중 영역**: 가장 많이 언급되는 주제들
    2. **브릿지 개념**: 여러 영역을 연결하는 핵심 엔티티
    3. **고립된 영역**: 다른 것과 연결이 적은 주제들
    4. **성장 영역**: 최근 활발하게 확장되는 주제들
    5. **탐구 제안**: 연결을 강화할 수 있는 영역

    **응답 예시:**
    ```json
    {
      "focus_areas": [
        {"name": "Knowledge Graph", "strength": 15, "trend": "growing"}
      ],
      "bridge_concepts": [
        {"name": "PKM", "connects": ["Research", "Development", "Writing"], "importance": 0.9}
      ],
      "isolated_areas": [
        {"name": "Old Project", "connection_count": 1, "suggestion": "연결할 주제 검토"}
      ],
      "growth_areas": [
        {"name": "AI", "recent_notes": 5, "growth_rate": 2.5}
      ],
      "exploration_suggestions": [
        {"area1": "PKM", "area2": "AI", "potential": "높음", "reason": "공통 관심사 발견"}
      ]
    }
    ```
    """
    try:
        folder_condition = "n.note_id STARTS WITH $folder_prefix AND" if folder_prefix else ""
        params = {"folder_prefix": folder_prefix or ""}

        # 1. 집중 영역 (Focus Areas): 가장 많이 언급되는 엔티티
        cypher_focus = f"""
        MATCH (n:Note)-[:MENTIONS]->(e:Entity)
        WHERE {folder_condition} e.name IS NOT NULL
        WITH e, count(DISTINCT n) as mention_count, collect(DISTINCT n.note_id) as notes
        WHERE mention_count >= 2
        RETURN e.uuid as uuid,
               e.name as name,
               CASE WHEN e:Goal THEN 'Goal'
                    WHEN e:Project THEN 'Project'
                    WHEN e:Task THEN 'Task'
                    WHEN e:Concept THEN 'Concept'
                    WHEN e:Question THEN 'Question'
                    WHEN e:Insight THEN 'Insight'
                    WHEN e:Resource THEN 'Resource'
                    WHEN e:Person THEN 'Person'
                    ELSE 'Topic' END as type,
               mention_count,
               notes
        ORDER BY mention_count DESC
        LIMIT 15
        """

        focus_result = client.query(cypher_focus, params)
        focus_areas = []
        for row in focus_result or []:
            focus_areas.append({
                "uuid": row["uuid"],
                "name": row["name"],
                "type": row["type"],
                "strength": row["mention_count"],
                "notes": row["notes"][:5]  # 상위 5개 노트
            })

        # 2. 브릿지 개념 (Bridge Concepts): 여러 다른 엔티티들을 연결하는 허브
        cypher_bridge = f"""
        MATCH (n:Note)-[:MENTIONS]->(e1:Entity)
        WHERE {folder_condition} e1.name IS NOT NULL
        WITH n, e1
        MATCH (n)-[:MENTIONS]->(e2:Entity)
        WHERE e2.uuid <> e1.uuid AND e2.name IS NOT NULL
        WITH e1, count(DISTINCT e2) as connected_entities, collect(DISTINCT e2.name)[..5] as connections
        WHERE connected_entities >= 3
        RETURN e1.uuid as uuid,
               e1.name as name,
               connected_entities,
               connections
        ORDER BY connected_entities DESC
        LIMIT 10
        """

        bridge_result = client.query(cypher_bridge, params)
        bridge_concepts = []
        for row in bridge_result or []:
            bridge_concepts.append({
                "uuid": row["uuid"],
                "name": row["name"],
                "connected_count": row["connected_entities"],
                "connects": row["connections"],
                "importance": min(1.0, row["connected_entities"] / 10)
            })

        # 3. 고립된 영역 (Isolated Areas): 연결이 적은 엔티티
        cypher_isolated = f"""
        MATCH (n:Note)-[:MENTIONS]->(e:Entity)
        WHERE {folder_condition} e.name IS NOT NULL
        WITH e, count(DISTINCT n) as note_count
        WHERE note_count = 1
        OPTIONAL MATCH (e)-[r:RELATES_TO]-()
        WITH e, note_count, count(r) as relation_count
        WHERE relation_count <= 1
        RETURN e.uuid as uuid,
               e.name as name,
               note_count,
               relation_count
        LIMIT 15
        """

        isolated_result = client.query(cypher_isolated, params)
        isolated_areas = []
        for row in isolated_result or []:
            isolated_areas.append({
                "uuid": row["uuid"],
                "name": row["name"],
                "note_count": row["note_count"],
                "relation_count": row["relation_count"],
                "suggestion": "다른 주제와 연결 검토"
            })

        # 4. 타입별 분포 (PKM Core Ontology v2 - 8개 타입 + Person)
        cypher_distribution = f"""
        MATCH (n:Note)-[:MENTIONS]->(e:Entity)
        WHERE {folder_condition} e.name IS NOT NULL
        WITH CASE WHEN e:Goal THEN 'Goal'
                  WHEN e:Project THEN 'Project'
                  WHEN e:Task THEN 'Task'
                  WHEN e:Concept THEN 'Concept'
                  WHEN e:Question THEN 'Question'
                  WHEN e:Insight THEN 'Insight'
                  WHEN e:Resource THEN 'Resource'
                  WHEN e:Person THEN 'Person'
                  ELSE 'Topic' END as type,
             count(DISTINCT e) as entity_count,
             count(DISTINCT n) as note_count
        RETURN type, entity_count, note_count
        ORDER BY entity_count DESC
        """

        dist_result = client.query(cypher_distribution, params)
        type_distribution = {}
        for row in dist_result or []:
            type_distribution[row["type"]] = {
                "entity_count": row["entity_count"],
                "note_count": row["note_count"]
            }

        # 5. 탐구 제안: 연결이 약하지만 잠재적 연결 가능성이 있는 영역
        exploration_suggestions = []
        if len(focus_areas) >= 2:
            # 상위 집중 영역 중 직접 연결이 없는 쌍 찾기
            top_entities = [f["uuid"] for f in focus_areas[:8]]

            cypher_unconnected = """
            MATCH (e1:Entity), (e2:Entity)
            WHERE e1.uuid IN $uuids AND e2.uuid IN $uuids
              AND e1.uuid < e2.uuid
              AND NOT (e1)-[:RELATES_TO]-(e2)
            RETURN e1.name as name1, e2.name as name2
            LIMIT 5
            """

            unconnected = client.query(cypher_unconnected, {"uuids": top_entities})
            for row in unconnected or []:
                exploration_suggestions.append({
                    "area1": row["name1"],
                    "area2": row["name2"],
                    "potential": "높음",
                    "reason": "둘 다 집중 영역이지만 직접 연결 없음"
                })

        # 6. 시간 기반 트렌드 (Time-based Trends)
        # 최근 7일 vs 30일 토픽 비교
        cypher_time_trends = f"""
        MATCH (n:Note)-[:MENTIONS]->(e:Entity)
        WHERE {folder_condition} e.name IS NOT NULL AND n.updated_at IS NOT NULL
        WITH e,
             sum(CASE WHEN n.updated_at >= datetime() - duration('P7D') THEN 1 ELSE 0 END) as recent_7d,
             sum(CASE WHEN n.updated_at >= datetime() - duration('P30D') AND n.updated_at < datetime() - duration('P7D') THEN 1 ELSE 0 END) as older_30d,
             count(DISTINCT n) as total_mentions
        WHERE total_mentions >= 2
        RETURN e.name as name,
               e.uuid as uuid,
               recent_7d,
               older_30d,
               total_mentions,
               CASE
                   WHEN recent_7d > 0 AND older_30d = 0 THEN 'emerging'
                   WHEN recent_7d > older_30d THEN 'growing'
                   WHEN recent_7d < older_30d THEN 'declining'
                   ELSE 'stable'
               END as trend
        ORDER BY recent_7d DESC
        LIMIT 20
        """

        trends_result = client.query(cypher_time_trends, params)

        time_trends = {
            "recent_topics": [],      # 최근 7일 활발
            "emerging_topics": [],    # 새로 등장 (7일 내 신규)
            "declining_topics": [],   # 감소 추세
            "stable_topics": [],      # 안정적
            "trend_period": "7d vs 30d"
        }

        for row in trends_result or []:
            topic_info = {
                "name": row["name"],
                "uuid": row["uuid"],
                "recent_count": row["recent_7d"],
                "older_count": row["older_30d"],
                "total": row["total_mentions"]
            }

            if row["trend"] == "emerging":
                time_trends["emerging_topics"].append(topic_info)
            elif row["trend"] == "growing":
                time_trends["recent_topics"].append(topic_info)
            elif row["trend"] == "declining":
                time_trends["declining_topics"].append(topic_info)
            else:
                time_trends["stable_topics"].append(topic_info)

        # 상위 5개씩만 유지
        time_trends["recent_topics"] = time_trends["recent_topics"][:5]
        time_trends["emerging_topics"] = time_trends["emerging_topics"][:5]
        time_trends["declining_topics"] = time_trends["declining_topics"][:5]
        time_trends["stable_topics"] = time_trends["stable_topics"][:5]

        # 7. Knowledge Health Score (지식 건강도)
        # 연결 밀도, 고립 비율, 완성도 계산

        # 7-1. 전체 노트 수와 연결된 노트 수
        cypher_health_notes = f"""
        MATCH (n:Note)
        WHERE {folder_condition.replace('AND', '') if folder_condition else '1=1'}
        WITH count(n) as total_notes
        OPTIONAL MATCH (n2:Note)-[:MENTIONS]->(:Entity)
        WHERE {folder_condition.replace('AND', '') if folder_condition else '1=1'}
        WITH total_notes, count(DISTINCT n2) as connected_notes
        RETURN total_notes, connected_notes
        """
        # Simplified query for health metrics
        cypher_health_simple = f"""
        MATCH (n:Note)
        {"WHERE " + folder_condition.replace('AND', '').strip() if folder_condition else ""}
        WITH count(n) as total_notes
        MATCH (n2:Note)-[:MENTIONS]->(:Entity)
        {"WHERE " + folder_condition.replace('AND', '').strip() if folder_condition else ""}
        WITH total_notes, count(DISTINCT n2) as connected_notes
        RETURN total_notes, connected_notes
        """

        health_result = client.query(cypher_health_simple, params)
        total_notes_count = 0
        connected_notes_count = 0

        if health_result and len(health_result) > 0:
            total_notes_count = health_result[0].get("total_notes", 0) or 0
            connected_notes_count = health_result[0].get("connected_notes", 0) or 0

        # 7-2. 고립 노트 수 (엔티티 연결 없음)
        isolation_ratio = 0.0
        if total_notes_count > 0:
            isolation_ratio = 1 - (connected_notes_count / total_notes_count)

        # 7-3. 연결 밀도 (평균 엔티티 연결 수)
        cypher_density = f"""
        MATCH (n:Note)-[m:MENTIONS]->(:Entity)
        {"WHERE " + folder_condition.replace('AND', '').strip() if folder_condition else ""}
        WITH n, count(m) as entity_count
        RETURN avg(entity_count) as avg_connections, max(entity_count) as max_connections
        """

        density_result = client.query(cypher_density, params)
        avg_connections = 0.0
        max_connections = 0

        if density_result and len(density_result) > 0:
            avg_connections = density_result[0].get("avg_connections", 0) or 0
            max_connections = density_result[0].get("max_connections", 0) or 0

        # 연결 밀도 점수 (0~1, 평균 5개 연결 기준)
        connection_density = min(1.0, avg_connections / 5) if avg_connections else 0

        # 완성도 점수 계산 (연결 밀도와 고립 비율 기반)
        completeness_score = (connection_density * 0.6) + ((1 - isolation_ratio) * 0.4)

        # 전체 건강도 점수 (0~100)
        overall_health = int(completeness_score * 100)

        # 개선 권장사항 생성
        health_recommendations = []
        if isolation_ratio > 0.3:
            isolated_count = int(total_notes_count * isolation_ratio)
            health_recommendations.append(f"고립 노트 {isolated_count}개를 다른 주제와 연결하세요")
        if connection_density < 0.5:
            health_recommendations.append("노트에 더 많은 개념/토픽을 추가하세요")
        if len(isolated_areas) > 10:
            health_recommendations.append(f"고립된 영역 {len(isolated_areas)}개를 검토하세요")
        if len(focus_areas) < 3:
            health_recommendations.append("집중 영역이 부족합니다. 더 많은 노트를 작성하세요")

        if not health_recommendations:
            health_recommendations.append("지식 그래프가 잘 관리되고 있습니다!")

        health_score = {
            "overall": overall_health,
            "connection_density": round(connection_density, 2),
            "isolation_ratio": round(isolation_ratio, 2),
            "completeness_score": round(completeness_score, 2),
            "metrics": {
                "total_notes": total_notes_count,
                "connected_notes": connected_notes_count,
                "avg_connections": round(avg_connections, 1),
                "max_connections": max_connections
            },
            "recommendations": health_recommendations
        }

        # 전체 통계
        total_entities = sum(t["entity_count"] for t in type_distribution.values())
        total_notes = max(t["note_count"] for t in type_distribution.values()) if type_distribution else 0

        return {
            "status": "success",
            "summary": {
                "total_entities": total_entities,
                "total_notes": total_notes,
                "focus_count": len(focus_areas),
                "bridge_count": len(bridge_concepts),
                "isolated_count": len(isolated_areas),
                "health_score": overall_health
            },
            "type_distribution": type_distribution,
            "focus_areas": focus_areas,
            "bridge_concepts": bridge_concepts,
            "isolated_areas": isolated_areas,
            "exploration_suggestions": exploration_suggestions,
            "time_trends": time_trends,
            "health_score": health_score
        }

    except Exception as e:
        logger.error(f"Thinking insights error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vault/reclassify-pkm-types")
async def reclassify_pkm_types(
    vault_id: str = Query(..., description="Vault ID"),
    user_token: str = Query(..., description="User token"),
    batch_size: int = Query(500, description="Batch size", ge=50, le=1000),
    client: Neo4jBoltClient = Depends(get_neo4j_client)
) -> Dict[str, Any]:
    """
    기존 Entity의 PKM Type 재분류 (Resync 필요 없음!)

    개선된 분류 로직을 기존 모든 Entity에 적용합니다.
    - Goal, Concept, Question, Insight, Resource 분류 개선
    - Summary 기반 키워드 매칭 강화
    - 이름 패턴 분석 추가

    **사용 시나리오:**
    - 분류 로직 업데이트 후 기존 데이터 재분류
    - 빈 타입(Goal=0, Concept=0 등) 채우기
    """
    try:
        from app.services.hybrid_graphiti_service import classify_entity_to_pkm_type

        # Step 1: 모든 Entity 조회
        cypher_all_entities = """
        MATCH (e:Entity)
        WHERE e.name IS NOT NULL
        RETURN e.uuid as uuid, e.name as name, e.summary as summary, e.pkm_type as current_type
        LIMIT $batch_size
        """

        entities = client.query(cypher_all_entities, {"batch_size": batch_size})

        if not entities:
            return {
                "status": "success",
                "message": "No entities to reclassify",
                "reclassified": 0
            }

        logger.info(f"Reclassifying {len(entities)} entities...")

        # Step 2: 재분류 및 업데이트
        stats = {
            "Goal": 0, "Project": 0, "Task": 0, "Topic": 0,
            "Concept": 0, "Question": 0, "Insight": 0, "Resource": 0,
            "Person": 0, "changed": 0, "unchanged": 0, "errors": 0
        }

        for entity in entities:
            try:
                uuid = entity["uuid"]
                name = entity["name"]
                summary = entity.get("summary", "")
                current_type = entity.get("current_type", "Topic")

                # 새 분류
                new_type = classify_entity_to_pkm_type(name, summary)

                # 통계 업데이트
                stats[new_type] = stats.get(new_type, 0) + 1

                if new_type != current_type:
                    stats["changed"] += 1

                    # 기존 PKM 레이블 제거하고 새 레이블 추가
                    cypher_update = f"""
                    MATCH (e:Entity {{uuid: $uuid}})
                    REMOVE e:Goal, e:Project, e:Task, e:Topic, e:Concept, e:Question, e:Insight, e:Resource, e:Person
                    SET e:{new_type}
                    SET e.pkm_type = $pkm_type
                    SET e.pkm_reclassified_at = datetime()
                    RETURN e.name as name
                    """

                    client.query(cypher_update, {"uuid": uuid, "pkm_type": new_type})
                else:
                    stats["unchanged"] += 1

            except Exception as e:
                logger.error(f"Error reclassifying {entity.get('name')}: {e}")
                stats["errors"] += 1

        logger.info(f"✅ Reclassification complete: {stats}")

        return {
            "status": "success",
            "message": f"Reclassified {len(entities)} entities",
            "total_processed": len(entities),
            "changed": stats["changed"],
            "unchanged": stats["unchanged"],
            "errors": stats["errors"],
            "type_distribution": {
                "Goal": stats["Goal"],
                "Project": stats["Project"],
                "Task": stats["Task"],
                "Topic": stats["Topic"],
                "Concept": stats["Concept"],
                "Question": stats["Question"],
                "Insight": stats["Insight"],
                "Resource": stats["Resource"],
                "Person": stats["Person"]
            }
        }

    except Exception as e:
        logger.error(f"Reclassification error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vault/migrate-note-mentions")
async def migrate_note_mentions(
    vault_id: str = Query(..., description="Vault ID"),
    user_token: str = Query(..., description="User token"),
    batch_size: int = Query(100, description="Batch size", ge=10, le=500),
    client: Neo4jBoltClient = Depends(get_neo4j_client)
) -> Dict[str, Any]:
    """
    Graphiti Episodic-Entity MENTIONS 관계를 Note-Entity MENTIONS로 마이그레이션

    Graphiti는 Episodic → Entity MENTIONS 관계를 사용하지만,
    2nd Brain 시각화를 위해서는 Note → Entity MENTIONS 관계가 필요합니다.

    이 엔드포인트는 기존 Episodic-Entity 관계를 Note-Entity 관계로 변환합니다.
    """
    try:
        from app.services.hybrid_graphiti_service import create_mentions_from_episodes, add_pkm_labels_to_graphiti_entities

        # Step 1: PKM 레이블 추가
        label_result = await add_pkm_labels_to_graphiti_entities(vault_id, batch_size)

        # Step 2: Note-Entity MENTIONS 관계 생성
        mentions_result = await create_mentions_from_episodes(vault_id, batch_size)

        return {
            "status": "success",
            "pkm_labels": label_result,
            "mentions": mentions_result
        }

    except Exception as e:
        logger.error(f"Migration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vault/debug-graph-structure")
async def debug_graph_structure(
    vault_id: str = Query(..., description="Vault ID"),
    user_token: str = Query(..., description="User token"),
    client: Neo4jBoltClient = Depends(get_neo4j_client)
) -> Dict[str, Any]:
    """
    디버그용: 그래프 데이터 구조 확인
    - Episodic 노드 샘플
    - Entity 노드 샘플
    - Note 노드 샘플
    - MENTIONS 관계 확인
    """
    try:
        # 1. Episodic 샘플
        episodic_sample = client.query("""
            MATCH (ep:Episodic)
            RETURN ep.name as name, ep.uuid as uuid, labels(ep) as labels
            LIMIT 5
        """, {})

        # 2. Episodic -> Entity MENTIONS 관계
        ep_entity_mentions = client.query("""
            MATCH (ep:Episodic)-[m:MENTIONS]->(e:Entity)
            RETURN ep.name as ep_name, e.name as entity_name, e.uuid as entity_uuid
            LIMIT 10
        """, {})

        # 3. Note -> Entity MENTIONS 관계
        note_entity_mentions = client.query("""
            MATCH (n:Note)-[m:MENTIONS]->(e:Entity)
            RETURN n.note_id as note_id, e.name as entity_name, e.uuid as entity_uuid
            LIMIT 10
        """, {})

        # 4. Note 샘플
        note_sample = client.query("""
            MATCH (n:Note)
            RETURN n.note_id as note_id, n.title as title
            LIMIT 5
        """, {})

        # 5. Entity 노드 수
        entity_count = client.query("""
            MATCH (e:Entity)
            RETURN count(e) as count
        """, {})

        return {
            "episodic_sample": episodic_sample or [],
            "ep_entity_mentions": ep_entity_mentions or [],
            "note_entity_mentions": note_entity_mentions or [],
            "note_sample": note_sample or [],
            "entity_count": entity_count[0]["count"] if entity_count else 0
        }
    except Exception as e:
        logger.error(f"Debug error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
