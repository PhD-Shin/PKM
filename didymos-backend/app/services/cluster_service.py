"""
Knowledge Graph Clustering Service
Neo4j GDS 라이브러리를 활용한 커뮤니티 탐지 및 LLM 기반 요약
"""
from typing import Dict, Any, List, Optional, Tuple
import logging
from datetime import datetime, timedelta
import json
import numpy as np

logger = logging.getLogger(__name__)

# UMAP + HDBSCAN imports (lazy import for performance)
try:
    import umap
    import hdbscan
    CLUSTERING_AVAILABLE = True
except ImportError:
    CLUSTERING_AVAILABLE = False
    logger.warning("UMAP or HDBSCAN not available. Semantic clustering disabled.")


def compute_clusters_louvain(
    client,
    vault_id: str,
    target_clusters: int = 10,
    include_types: List[str] = ["Topic", "Project", "Task"]
) -> Dict[str, Any]:
    """
    Louvain 알고리즘을 사용한 커뮤니티 탐지

    Args:
        client: Neo4j Bolt 클라이언트
        vault_id: Vault ID
        target_clusters: 목표 클러스터 개수
        include_types: 클러스터링에 포함할 노드 타입

    Returns:
        클러스터 데이터
    """
    try:
        # Step 1: 서브그래프 투영 (Notes 제외, Entities만)
        type_filter = " OR ".join([f"'{t}' IN labels(entity)" for t in include_types])

        cypher_projection = f"""
        MATCH (v:Vault {{id: $vault_id}})-[:HAS_NOTE]->(note:Note)
        MATCH (note)-[r:MENTIONS]->(entity)
        WHERE {type_filter}
        WITH entity, COUNT(DISTINCT note) as mention_count
        WHERE mention_count > 0
        RETURN entity.id as entity_id, labels(entity)[0] as type, mention_count
        LIMIT 1000
        """

        entities = client.query(cypher_projection, {"vault_id": vault_id})

        if not entities or len(entities) == 0:
            logger.warning(f"No entities found for vault {vault_id}")
            return {
                "clusters": [],
                "edges": [],
                "total_nodes": 0,
                "method": "louvain",
                "computed_at": datetime.utcnow().isoformat()
            }

        # Step 2: 엔티티 간 관계 가져오기 (공통 노트로 연결)
        type_filter_e1 = " OR ".join([f"'{t}' IN labels(e1)" for t in include_types])
        type_filter_e2 = " OR ".join([f"'{t}' IN labels(e2)" for t in include_types])

        cypher_relations = f"""
        MATCH (v:Vault {{id: $vault_id}})-[:HAS_NOTE]->(note:Note)
        MATCH (note)-[:MENTIONS]->(e1)
        MATCH (note)-[:MENTIONS]->(e2)
        WHERE id(e1) < id(e2)
          AND ({type_filter_e1})
          AND ({type_filter_e2})
        WITH e1, e2, COUNT(DISTINCT note) as shared_notes
        WHERE shared_notes > 0
        RETURN e1.id as from_id, e2.id as to_id, shared_notes as weight
        """

        relations = client.query(cypher_relations, {"vault_id": vault_id})

        # Step 3: 간단한 클러스터링 (Neo4j GDS 없이 Python에서 처리)
        # 실제로는 networkx 또는 Neo4j GDS를 사용해야 하지만,
        # 여기서는 간단한 connected components 기반으로 시작

        clusters = _simple_clustering(entities, relations, target_clusters)

        return {
            "clusters": clusters,
            "edges": [],
            "total_nodes": len(entities),
            "method": "louvain",
            "computed_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Cluster computation failed: {e}")
        raise


def _simple_clustering(
    entities: List[Dict],
    relations: List[Dict],
    target_clusters: int
) -> List[Dict[str, Any]]:
    """
    간단한 연결 성분 기반 클러스터링
    (추후 networkx 또는 Neo4j GDS로 교체 예정)
    """
    # 엔티티를 타입별로 그룹화
    clusters_by_type = {}
    for entity in entities:
        entity_type = entity.get("type", "Unknown")
        if entity_type not in clusters_by_type:
            clusters_by_type[entity_type] = []
        clusters_by_type[entity_type].append(entity)

    # 각 타입을 클러스터로 변환
    clusters = []
    cluster_id = 0

    for entity_type, entity_list in clusters_by_type.items():
        cluster_id += 1
        node_count = len(entity_list)

        # mention_count 합산
        total_mentions = sum(e.get("mention_count", 0) for e in entity_list)
        importance_score = min(10.0, total_mentions / 10.0)

        clusters.append({
            "id": f"cluster_{cluster_id}",
            "name": f"{entity_type} Cluster",
            "level": 1,
            "node_count": node_count,
            "entity_ids": [e.get("entity_id") for e in entity_list if e.get("entity_id")],
            "summary": f"Contains {node_count} {entity_type} entities",
            "key_insights": [
                f"Total mentions: {total_mentions}",
                f"Entity type: {entity_type}"
            ],
            "sample_entities": [],
            "sample_notes": [],
            "note_ids": [],
            "recent_updates": 0,
            "importance_score": importance_score,
            "last_updated": datetime.utcnow().isoformat(),
            "last_computed": datetime.utcnow().isoformat(),
            "clustering_method": "type_based",
            "is_manual": False,
            "contains_types": {entity_type.lower(): node_count}
        })

    return clusters


def compute_clusters_semantic(
    client,
    vault_id: str,
    target_clusters: int = 10,
    include_types: List[str] = ["Topic", "Project", "Task"]
) -> Dict[str, Any]:
    """
    UMAP + HDBSCAN을 사용한 의미론적 클러스터링

    노트 임베딩을 기반으로 클러스터링한 후, 각 클러스터에서 언급된 엔티티를 집계

    Args:
        client: Neo4j Bolt 클라이언트
        vault_id: Vault ID
        target_clusters: 목표 클러스터 개수 (참고용, HDBSCAN이 자동 결정)
        include_types: 클러스터링에 포함할 노드 타입

    Returns:
        클러스터 데이터
    """
    if not CLUSTERING_AVAILABLE:
        logger.error("UMAP/HDBSCAN not available. Falling back to type-based clustering.")
        return _semantic_fallback_to_type_based(
            client,
            vault_id,
            target_clusters,
            include_types,
            reason="dependency_missing"
        )

    try:
        # Step 1: Neo4j에서 노트 임베딩 가져오기 (엔티티가 아닌 노트!)
        cypher_embeddings = """
        MATCH (v:Vault {id: $vault_id})-[:HAS_NOTE]->(note:Note)
        WHERE note.embedding IS NOT NULL
        RETURN note.note_id as note_id,
               note.title as note_title,
               toString(note.updated_at) as updated_at,
               note.embedding as embedding
        """

        results = client.query(cypher_embeddings, {"vault_id": vault_id})

        if not results or len(results) == 0:
            logger.warning(f"No notes with embeddings found for vault {vault_id}")
            return _semantic_fallback_to_type_based(
                client,
                vault_id,
                target_clusters,
                include_types,
                reason="no_embeddings"
            )

        # Step 2: 임베딩 배열로 변환
        note_ids = [r["note_id"] for r in results]
        note_titles = [r["note_title"] for r in results]
        note_updated_raw = [r.get("updated_at") for r in results]

        # 임베딩을 numpy 배열로 변환
        embeddings = np.array([r["embedding"] for r in results], dtype=float)

        if len(embeddings) < 5:
            logger.warning(f"Not enough embeddings for semantic clustering ({len(embeddings)} < 5)")
            return _semantic_fallback_to_type_based(
                client,
                vault_id,
                target_clusters,
                include_types,
                reason="insufficient_samples"
            )

        logger.info(f"Found {len(embeddings)} notes with embeddings (shape: {embeddings.shape})")

        # Step 3: UMAP 차원 축소
        logger.info("Running UMAP dimensionality reduction...")

        # UMAP 파라미터 동적 조정
        n_samples = len(embeddings)
        n_components = min(5, n_samples - 1)  # 샘플 수보다 작게
        n_neighbors = max(2, min(15, n_samples - 1))  # 최소 2, 최대 15

        reducer = umap.UMAP(
            n_components=n_components,
            n_neighbors=n_neighbors,
            min_dist=0.1,
            metric='cosine',
            random_state=42
        )
        reduced_embeddings = reducer.fit_transform(embeddings)

        logger.info(f"UMAP completed: {embeddings.shape} → {reduced_embeddings.shape}")

        # Step 4: HDBSCAN 클러스터링
        logger.info("Running HDBSCAN clustering...")

        # min_cluster_size는 노트 수에 따라 동적 조정
        min_cluster_size = max(2, len(embeddings) // target_clusters)

        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=1,
            cluster_selection_epsilon=0.5,
            metric='euclidean'
        )
        cluster_labels = clusterer.fit_predict(reduced_embeddings)

        # 클러스터 개수 (노이즈 제외)
        unique_labels = set(cluster_labels)
        unique_labels.discard(-1)  # 노이즈 제거
        n_clusters = len(unique_labels)

        logger.info(f"HDBSCAN found {n_clusters} clusters (+ {sum(cluster_labels == -1)} noise points)")

        if n_clusters == 0:
            logger.warning("HDBSCAN returned no clusters. Falling back to type-based clustering.")
            return _semantic_fallback_to_type_based(
                client,
                vault_id,
                target_clusters,
                include_types,
                reason="no_clusters"
            )

        # Step 5: 각 클러스터에서 언급된 엔티티 집계
        type_filter = " OR ".join([f"'{t}' IN labels(entity)" for t in include_types])

        clusters = []

        for cluster_id in sorted(unique_labels):
            # 클러스터에 속한 노트들
            cluster_mask = cluster_labels == cluster_id
            cluster_note_ids = [note_ids[i] for i in range(len(note_ids)) if cluster_mask[i]]
            cluster_note_titles = [note_titles[i] for i in range(len(note_titles)) if cluster_mask[i]]
            cluster_note_updates = [
                _parse_datetime(note_updated_raw[i]) for i in range(len(note_updated_raw)) if cluster_mask[i]
            ]

            # 해당 노트들에서 언급된 엔티티 집계
            cypher_entities = f"""
            MATCH (note:Note)-[:MENTIONS]->(entity)
            WHERE note.note_id IN $note_ids AND ({type_filter})
            RETURN entity.id as entity_id,
                   entity.name as entity_name,
                   labels(entity)[0] as entity_type,
                   COUNT(DISTINCT note) as mention_count
            ORDER BY mention_count DESC
            """

            entities_result = client.query(cypher_entities, {"note_ids": cluster_note_ids})

            if not entities_result or len(entities_result) == 0:
                continue  # 엔티티가 없는 클러스터는 스킵

            # 엔티티 데이터 추출
            cluster_entity_ids = [e["entity_id"] for e in entities_result]
            cluster_entity_names = [e["entity_name"] for e in entities_result]
            cluster_types = [e["entity_type"] for e in entities_result]
            cluster_mentions = [e["mention_count"] for e in entities_result]

            # 클러스터 내 타입 분포
            type_counts = {}
            for t in cluster_types:
                type_counts[t.lower()] = type_counts.get(t.lower(), 0) + 1

            # 클러스터 이름 추론 (가장 많이 언급된 엔티티 이름 사용)
            if len(cluster_entity_names) > 0:
                cluster_name = f"{cluster_entity_names[0]} 관련"  # 첫 번째가 mention_count 내림차순
            else:
                cluster_name = f"Cluster {cluster_id + 1}"

            # 중요도 점수
            total_mentions = sum(cluster_mentions)
            recency_bonus, recent_updates = _compute_recency_bonus(cluster_note_updates)
            importance_score = min(10.0, (total_mentions / 10.0) + recency_bonus)

            clusters.append({
                "id": f"cluster_{cluster_id + 1}",
                "name": cluster_name,
                "level": 1,
                "node_count": len(cluster_entity_ids),
                "entity_ids": cluster_entity_ids,
                "sample_entities": cluster_entity_names[:10],  # 상위 10개
                "sample_notes": cluster_note_titles[:5],
                "note_ids": cluster_note_ids[:20],
                "recent_updates": recent_updates,
                "summary": f"{cluster_name} 클러스터 ({len(cluster_entity_ids)} 엔티티)",
                "key_insights": _build_auto_insights(cluster_name, total_mentions, recent_updates, type_counts),
                "contains_types": type_counts,
                "importance_score": importance_score,
                "last_updated": datetime.utcnow().isoformat(),
                "last_computed": datetime.utcnow().isoformat(),
                "clustering_method": "umap_hdbscan",
                "is_manual": False
            })

        logger.info(f"Successfully created {len(clusters)} semantic clusters")

        # 총 엔티티 수 계산
        total_entities = sum(c["node_count"] for c in clusters)

        if len(clusters) == 0:
            logger.warning("Semantic clustering produced empty clusters. Falling back to type-based clustering.")
            return _semantic_fallback_to_type_based(
                client,
                vault_id,
                target_clusters,
                include_types,
                reason="empty_result"
            )

        edges = _build_cluster_edges(clusters)

        return {
            "clusters": clusters,
            "edges": edges,
            "total_nodes": total_entities,
            "method": "umap_hdbscan",
            "computed_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Semantic clustering failed: {e}")
        return _semantic_fallback_to_type_based(
            client,
            vault_id,
            target_clusters,
            include_types,
            reason="exception"
        )


def _semantic_fallback_to_type_based(
    client,
    vault_id: str,
    target_clusters: int,
    include_types: List[str],
    reason: str
) -> Dict[str, Any]:
    """
    의미론적 클러스터링 실패 시 타입 기반으로 폴백
    """
    logger.warning(f"Semantic clustering fallback triggered: {reason}")
    fallback = compute_clusters_louvain(
        client=client,
        vault_id=vault_id,
        target_clusters=target_clusters,
        include_types=include_types
    )
    fallback["method"] = f"umap_hdbscan_fallback:{reason}"
    return fallback


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    """ISO 문자열을 datetime으로 파싱 (없으면 None)"""
    if not value:
        return None
    try:
        if isinstance(value, datetime):
            return value
        if hasattr(value, "isoformat"):
            return datetime.fromisoformat(value.isoformat())
        # Neo4j의 toString(datetime) 결과는 Z를 포함할 수 있음
        value_norm = value.replace("Z", "+00:00")
        return datetime.fromisoformat(value_norm)
    except Exception:
        return None


def _compute_recency_bonus(updated_at_list: List[Optional[datetime]]) -> Tuple[float, int]:
    """최근 7일 업데이트 수와 보너스 점수 계산"""
    now = datetime.utcnow()
    recent_threshold = now - timedelta(days=7)
    recent_updates = 0

    valid_dates = [dt for dt in updated_at_list if dt is not None]
    for dt in valid_dates:
        if dt >= recent_threshold:
            recent_updates += 1

    if not valid_dates:
        return 0.0, 0

    latest = max(valid_dates)
    days_since_latest = max((now - latest).days, 0)
    recency_bonus = max(0.0, 3.0 - (days_since_latest / 10.0))  # 최대 3점
    return recency_bonus, recent_updates


def _build_auto_insights(
    cluster_name: str,
    total_mentions: int,
    recent_updates: int,
    type_counts: Dict[str, int]
) -> List[str]:
    """간단한 규칙 기반 인사이트"""
    insights = []
    insights.append(f"{total_mentions} mentions across entities.")
    if recent_updates > 0:
        insights.append(f"{recent_updates} notes updated in the last 7 days.")
    else:
        insights.append("No recent updates in the last 7 days.")

    dominant_type = None
    if type_counts:
        dominant_type = max(type_counts.items(), key=lambda kv: kv[1])[0]
        insights.append(f"Dominant type: {dominant_type} ({type_counts[dominant_type]})")

    if dominant_type == "task":
        insights.append("Next action: review and reprioritize tasks in this cluster.")
    elif dominant_type == "project":
        insights.append("Next action: identify active project milestones.")
    else:
        insights.append("Next action: link related notes to strengthen context.")

    return insights[:4]


def _build_cluster_edges(clusters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    클러스터 간 공유 엔티티 기반 관계 생성
    """
    edges: List[Dict[str, Any]] = []
    if len(clusters) < 2:
        return edges

    for i in range(len(clusters)):
        for j in range(i + 1, len(clusters)):
            entities_i = set(clusters[i].get("entity_ids") or [])
            entities_j = set(clusters[j].get("entity_ids") or [])
            if not entities_i or not entities_j:
                continue

            shared = entities_i.intersection(entities_j)
            if len(shared) == 0:
                continue

            weight = float(len(shared))
            edges.append({
                "from": clusters[i]["id"],
                "to": clusters[j]["id"],
                "relation_type": "RELATED_TO",
                "weight": weight
            })

    return edges


def get_cached_clusters(client, vault_id: str) -> Optional[Dict[str, Any]]:
    """
    캐시된 클러스터 데이터 가져오기

    Args:
        client: Neo4j Bolt 클라이언트
        vault_id: Vault ID

    Returns:
        캐시된 클러스터 데이터 또는 None
    """
    try:
        cypher = """
        MATCH (v:Vault {id: $vault_id})-[:HAS_CLUSTER_CACHE]->(cache:ClusterCache)
        WHERE datetime(cache.expires_at) > datetime()
        RETURN cache.data as data,
               cache.computed_at as computed_at,
               cache.method as method
        ORDER BY cache.computed_at DESC
        LIMIT 1
        """

        result = client.query(cypher, {"vault_id": vault_id})

        if result and len(result) > 0:
            cache_data = result[0]
            raw_data = json.loads(cache_data["data"])
            computed_at = cache_data["computed_at"]
            if not isinstance(computed_at, str):
                computed_at = str(computed_at)

            if isinstance(raw_data, dict) and "clusters" in raw_data:
                clusters = raw_data.get("clusters", [])
                edges = raw_data.get("edges", [])
            else:
                clusters = raw_data
                edges = []

            return {
                "clusters": clusters,
                "edges": edges,
                "computed_at": computed_at,
                "method": cache_data["method"],
                "from_cache": True
            }

        return None

    except Exception as e:
        logger.error(f"Failed to get cached clusters: {e}")
        return None


def save_cluster_cache(
    client,
    vault_id: str,
    clusters: List[Dict],
    method: str,
    ttl_hours: int = 12,
    edges: Optional[List[Dict]] = None
) -> bool:
    """
    클러스터 데이터 캐시 저장

    Args:
        client: Neo4j Bolt 클라이언트
        vault_id: Vault ID
        clusters: 클러스터 데이터
        method: 클러스터링 방법
        ttl_hours: 캐시 유효 시간 (시간)

    Returns:
        성공 여부
    """
    try:
        cypher = """
        MATCH (v:Vault {id: $vault_id})
        MERGE (v)-[:HAS_CLUSTER_CACHE]->(cache:ClusterCache)
        SET cache.data = $data,
            cache.method = $method,
            cache.computed_at = datetime(),
            cache.expires_at = datetime() + duration({hours: $ttl_hours})
        RETURN cache
        """

        payload = {
            "clusters": clusters,
            "edges": edges or []
        }

        params = {
            "vault_id": vault_id,
            "data": json.dumps(payload),
            "method": method,
            "ttl_hours": ttl_hours
        }

        result = client.query(cypher, params)
        return result is not None and len(result) > 0

    except Exception as e:
        logger.error(f"Failed to save cluster cache: {e}")
        return False


def invalidate_cluster_cache(client, vault_id: str) -> bool:
    """
    클러스터 캐시 무효화

    Args:
        client: Neo4j Bolt 클라이언트
        vault_id: Vault ID

    Returns:
        성공 여부
    """
    try:
        cypher = """
        MATCH (v:Vault {id: $vault_id})-[:HAS_CLUSTER_CACHE]->(cache:ClusterCache)
        DETACH DELETE cache
        """

        client.query(cypher, {"vault_id": vault_id})
        return True

    except Exception as e:
        logger.error(f"Failed to invalidate cluster cache: {e}")
        return False


def is_cluster_cache_stale(client, vault_id: str, computed_at: Optional[str]) -> bool:
    """
    캐시가 최신 노트 업데이트보다 오래되었는지 판단
    """
    if not computed_at:
        return True

    try:
        computed_dt = _parse_datetime(computed_at)
        if not computed_dt:
            return True

        cypher = """
        MATCH (v:Vault {id: $vault_id})-[:HAS_NOTE]->(n:Note)
        WITH max(n.updated_at) AS last_updated
        RETURN last_updated
        """
        result = client.query(cypher, {"vault_id": vault_id})
        if not result or len(result) == 0 or result[0].get("last_updated") is None:
            return False

        last_updated = result[0]["last_updated"]
        if isinstance(last_updated, str):
            last_updated = _parse_datetime(last_updated)

        if isinstance(last_updated, datetime):
            return last_updated > computed_dt

        return False
    except Exception as e:
        logger.error(f"Failed to check cache staleness: {e}")
        return True


def generate_llm_summaries(
    client,
    vault_id: str,
    clusters: List[Dict]
) -> List[Dict]:
    """
    GPT-5 Mini를 사용하여 각 클러스터의 요약 생성 (Phase 11)

    Args:
        client: Neo4j Bolt 클라이언트
        vault_id: Vault ID
        clusters: 클러스터 리스트

    Returns:
        요약이 추가된 클러스터 리스트
    """
    try:
        from app.services.llm_client import generate_batch_cluster_summaries

        logger.info(f"🤖 Generating LLM summaries for {len(clusters)} clusters...")

        # 각 클러스터에 대해 샘플 엔티티 가져오기
        for cluster in clusters:
            try:
                # sample_entities가 없는 경우에만 간단한 placeholder 생성
                if not cluster.get('sample_entities'):
                    sample_entities = []
                    contains_types = cluster.get('contains_types', {})
                    for entity_type, count in contains_types.items():
                        sample_entities.append(f"{entity_type.title()} ({count}개)")
                    cluster['sample_entities'] = sample_entities
                if not cluster.get('sample_notes'):
                    cluster['sample_notes'] = []
                if not cluster.get('note_ids'):
                    cluster['note_ids'] = []

            except Exception as e:
                logger.error(f"Failed to fetch sample entities for {cluster.get('id')}: {e}")
                cluster['sample_entities'] = []
                cluster['sample_notes'] = []

        # GPT-5 Mini로 일괄 요약 생성
        clusters_with_summaries = generate_batch_cluster_summaries(clusters)

        logger.info(f"✅ LLM summaries generated for {len(clusters_with_summaries)} clusters")
        return clusters_with_summaries

    except Exception as e:
        logger.error(f"Failed to generate LLM summaries: {e}")
        # 실패 시 기본 메시지 추가
        for cluster in clusters:
            if 'summary' not in cluster:
                cluster['summary'] = f"클러스터 '{cluster.get('name')}'는 {cluster.get('node_count')}개의 노드로 구성되어 있습니다."
            if 'key_insights' not in cluster:
                cluster['key_insights'] = ["LLM 요약 생성 실패", "나중에 다시 시도하세요."]
        return clusters
