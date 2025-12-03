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
