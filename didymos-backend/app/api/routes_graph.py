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
