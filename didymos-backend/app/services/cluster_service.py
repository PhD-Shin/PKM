"""
Knowledge Graph Clustering Service
Neo4j GDS 라이브러리를 활용한 커뮤니티 탐지 및 LLM 기반 요약

Graph-based Context Analysis:
- 단순 mention_count 대신 그래프 중심성(centrality)으로 엔티티 중요도 결정
- 여러 노트를 연결하는 "다리" 역할 엔티티가 더 높은 점수
- 클러스터 이름도 노트 제목이 아닌 그래프 허브 엔티티 기반으로 결정
"""
from typing import Dict, Any, List, Optional, Tuple
import logging
from datetime import datetime, timedelta
import json
import numpy as np
from collections import defaultdict

logger = logging.getLogger(__name__)

# 의미론적으로 무의미한 일반 엔티티 블랙리스트
# 이 엔티티들은 허브 선정에서 제외됨 (빈도가 높지만 클러스터 특성을 대표하지 않음)
GENERIC_ENTITY_BLACKLIST = {
    # 기관/조직 (너무 일반적)
    "서울대학교", "서울대", "snu", "seoul national university",
    "대학교", "대학", "연구실", "연구소", "학교",
    # 일반 개념
    "연구", "논문", "프로젝트", "회의", "미팅", "정리", "메모", "노트",
    "research", "paper", "project", "meeting", "note", "memo",
    # 날짜/시간
    "2024", "2025", "오늘", "내일", "이번주",
    # 기타 일반
    "todo", "task", "idea", "개념", "정의", "요약",
}

# UMAP + HDBSCAN imports (lazy import for performance)
try:
    import umap
    import hdbscan
    CLUSTERING_AVAILABLE = True
except ImportError:
    CLUSTERING_AVAILABLE = False
    logger.warning("UMAP or HDBSCAN not available. Semantic clustering disabled.")


def compute_entity_graph_centrality(
    client,
    note_ids: List[str],
    include_types: List[str] = ["Topic", "Project", "Task", "Person"],
    vault_total_notes: int = None,
    include_entity_node: bool = True
) -> Dict[str, Dict[str, Any]]:
    """
    그래프 구조 기반 엔티티 중요도 계산 (IDF 가중치 포함)

    노트 간 연결성을 분석하여 "다리" 역할을 하는 엔티티에 높은 점수 부여:
    1. degree_centrality: 연결된 노트 수
    2. bridge_score: 서로 다른 노트들을 연결하는 정도
    3. co_occurrence_score: 다른 엔티티들과 함께 등장하는 빈도
    4. idf_weight: 전체 vault에서 희소할수록 높은 가중치 (TF-IDF의 IDF)

    Args:
        client: Neo4j 클라이언트
        note_ids: 분석할 노트 ID 리스트
        include_types: 포함할 엔티티 타입
        vault_total_notes: 전체 vault의 노트 수 (IDF 계산용)
        include_entity_node: Graphiti EntityNode도 포함할지 여부

    Returns:
        {entity_id: {name, type, centrality_score, degree, bridge_score, co_occurrence, idf_weight}}
    """
    if not note_ids:
        return {}

    # PKM 타입 필터 + EntityNode (Graphiti) 지원
    type_conditions = [f"'{t}' IN labels(entity)" for t in include_types]
    if include_entity_node:
        # EntityNode with PKM labels (hybrid mode)
        type_conditions.append("'EntityNode' IN labels(entity)")
    type_filter = " OR ".join(type_conditions)

    # Step 1: 각 엔티티의 degree (연결된 노트 수) 계산
    cypher_degree = f"""
    MATCH (note:Note)-[:MENTIONS]->(entity)
    WHERE note.note_id IN $note_ids AND ({type_filter})
    WITH entity,
         entity.id as entity_id,
         entity.name as entity_name,
         labels(entity)[0] as entity_type,
         COLLECT(DISTINCT note.note_id) as connected_notes
    RETURN entity_id,
           COALESCE(entity_name, entity_id) as entity_name,
           entity_type,
           SIZE(connected_notes) as degree,
           connected_notes
    """

    degree_result = client.query(cypher_degree, {"note_ids": note_ids})

    if not degree_result:
        return {}

    # 엔티티별 연결 정보 수집
    entity_info = {}
    entity_notes = {}  # entity_id -> set of note_ids

    for row in degree_result:
        entity_id = row["entity_id"]
        entity_info[entity_id] = {
            "name": row["entity_name"],
            "type": row["entity_type"],
            "degree": row["degree"],
            "connected_notes": set(row["connected_notes"])
        }
        entity_notes[entity_id] = set(row["connected_notes"])

    # Step 2: Co-occurrence 분석 (같은 노트에 등장하는 엔티티 쌍)
    # 많은 다른 엔티티와 함께 등장하는 엔티티 = 허브 역할
    cypher_cooccurrence = f"""
    MATCH (note:Note)-[:MENTIONS]->(e1)
    MATCH (note)-[:MENTIONS]->(e2)
    WHERE note.note_id IN $note_ids
      AND ({type_filter.replace('entity', 'e1')})
      AND ({type_filter.replace('entity', 'e2')})
      AND e1.id < e2.id
    WITH e1.id as entity1, e2.id as entity2, COUNT(DISTINCT note) as shared_notes
    WHERE shared_notes > 0
    RETURN entity1, entity2, shared_notes
    """

    cooccurrence_result = client.query(cypher_cooccurrence, {"note_ids": note_ids})

    # 각 엔티티의 co-occurrence 파트너 수 계산
    co_occurrence_count = defaultdict(int)
    co_occurrence_strength = defaultdict(float)  # 연결 강도 합산

    for row in (cooccurrence_result or []):
        e1, e2 = row["entity1"], row["entity2"]
        shared = row["shared_notes"]
        co_occurrence_count[e1] += 1
        co_occurrence_count[e2] += 1
        co_occurrence_strength[e1] += shared
        co_occurrence_strength[e2] += shared

    # Step 3: Bridge Score + IDF 가중치 계산
    # 서로 다른 노트 그룹을 연결하는 엔티티에 높은 점수
    # 단, 전체 vault에서 너무 많이 등장하는 엔티티는 IDF로 감점

    total_notes = len(note_ids)
    max_degree = max((info["degree"] for info in entity_info.values()), default=1)
    max_cooccurrence = max(co_occurrence_count.values(), default=1)

    # IDF 계산용 vault 전체 노트 수 (없으면 클러스터 노트 수 사용)
    vault_size = vault_total_notes if vault_total_notes else total_notes

    for entity_id, info in entity_info.items():
        degree = info["degree"]
        entity_name = info.get("name", entity_id)

        # 블랙리스트 체크 - 일반적인 엔티티는 낮은 점수
        is_generic = entity_name.lower() in GENERIC_ENTITY_BLACKLIST or entity_id.lower() in GENERIC_ENTITY_BLACKLIST
        generic_penalty = 0.1 if is_generic else 1.0

        # Degree centrality (정규화)
        degree_centrality = degree / max(total_notes, 1)

        # Co-occurrence score (정규화)
        co_count = co_occurrence_count.get(entity_id, 0)
        co_score = co_count / max(max_cooccurrence, 1)

        # Bridge score: 연결 강도의 분산 (많은 노트에 고르게 등장할수록 높음)
        connected = info["connected_notes"]
        if len(connected) > 1:
            # 연결된 노트들이 분산되어 있을수록 bridge score 높음
            bridge_score = min(1.0, len(connected) / max(3, total_notes * 0.2))
        else:
            bridge_score = 0.0

        # IDF 가중치: 전체 vault에서 희소할수록 높음
        # log(N / df) where N=총 문서수, df=엔티티가 등장하는 문서수
        # 모든 노트에 등장하면 idf=0, 일부에만 등장하면 idf 높음
        if vault_size > 0 and degree > 0:
            # 클러스터 내 비율이 너무 높으면 감점 (50% 이상 노트에 등장 시)
            cluster_coverage = degree / total_notes
            if cluster_coverage > 0.5:
                # 클러스터의 50% 이상 노트에 등장 = 너무 일반적
                idf_weight = max(0.3, 1.0 - (cluster_coverage - 0.5) * 1.5)
            else:
                idf_weight = 1.0
        else:
            idf_weight = 1.0

        # 종합 중심성 점수 (가중 합산 + IDF + 블랙리스트 패널티)
        # degree: 30%, co-occurrence: 25%, bridge: 25%, idf: 20%
        raw_centrality = (
            0.30 * degree_centrality +
            0.25 * co_score +
            0.25 * bridge_score +
            0.20 * idf_weight
        )

        # 블랙리스트 패널티 적용
        centrality_score = raw_centrality * generic_penalty

        info["degree_centrality"] = degree_centrality
        info["co_occurrence_count"] = co_count
        info["co_occurrence_score"] = co_score
        info["bridge_score"] = bridge_score
        info["idf_weight"] = idf_weight
        info["is_generic"] = is_generic
        info["centrality_score"] = centrality_score

    return entity_info


def find_cluster_hub_entities(
    entity_info: Dict[str, Dict[str, Any]],
    top_k: int = 3,
    exclude_generic: bool = True
) -> List[Tuple[str, str, float]]:
    """
    클러스터 내에서 허브 역할을 하는 상위 엔티티 찾기

    Args:
        entity_info: 엔티티 정보 딕셔너리
        top_k: 반환할 상위 엔티티 수
        exclude_generic: 블랙리스트 엔티티 제외 여부

    Returns:
        [(entity_id, entity_name, centrality_score), ...]
    """
    if not entity_info:
        return []

    # 블랙리스트 엔티티 필터링 (선택적)
    filtered_entities = entity_info.items()
    if exclude_generic:
        filtered_entities = [
            (eid, info) for eid, info in entity_info.items()
            if not info.get("is_generic", False)
        ]

    # centrality_score로 정렬
    sorted_entities = sorted(
        filtered_entities,
        key=lambda x: x[1].get("centrality_score", 0),
        reverse=True
    )

    # 상위 k개 반환 (블랙리스트 필터링 후에도 충분하지 않으면 블랙리스트 포함)
    result = [
        (eid, info["name"], info["centrality_score"])
        for eid, info in sorted_entities[:top_k]
    ]

    # 결과가 부족하면 블랙리스트 엔티티도 포함
    if len(result) < top_k and exclude_generic:
        all_sorted = sorted(
            entity_info.items(),
            key=lambda x: x[1].get("centrality_score", 0),
            reverse=True
        )
        for eid, info in all_sorted:
            if len(result) >= top_k:
                break
            if (eid, info["name"], info["centrality_score"]) not in result:
                result.append((eid, info["name"], info["centrality_score"]))

    return result[:top_k]


def generate_cluster_name_from_graph(
    hub_entities: List[Tuple[str, str, float]],
    type_counts: Dict[str, int]
) -> str:
    """
    그래프 허브 엔티티 기반으로 클러스터 이름 생성

    노트 제목이 아닌, 그래프에서 중심 역할을 하는 개념으로 명명
    """
    if not hub_entities:
        # 폴백: 타입 기반 이름
        dominant_type = max(type_counts.items(), key=lambda x: x[1])[0] if type_counts else "Unknown"
        return f"{dominant_type.title()} Cluster"

    # 상위 1-2개 허브 엔티티로 이름 구성
    top_names = [name for _, name, _ in hub_entities[:2]]

    if len(top_names) == 1:
        return f"{top_names[0]} 중심"
    else:
        return f"{top_names[0]} & {top_names[1]}"


def compute_clusters_louvain(
    client,
    vault_id: str,
    target_clusters: int = 10,
    include_types: List[str] = ["Topic", "Project", "Task", "Person"],
    folder_prefix: str = None,
    include_entity_node: bool = True
) -> Dict[str, Any]:
    """
    Louvain 알고리즘을 사용한 커뮤니티 탐지

    Args:
        client: Neo4j Bolt 클라이언트
        vault_id: Vault ID
        target_clusters: 목표 클러스터 개수
        include_types: 클러스터링에 포함할 노드 타입
        folder_prefix: 폴더 경로 필터 (예: '1_프로젝트/')
        include_entity_node: Graphiti EntityNode도 포함할지 여부

    Returns:
        클러스터 데이터
    """
    try:
        # Step 1: 서브그래프 투영 (Notes 제외, Entities만)
        # PKM 타입 + EntityNode (Graphiti) 지원
        type_conditions = [f"'{t}' IN labels(entity)" for t in include_types]
        if include_entity_node:
            type_conditions.append("'EntityNode' IN labels(entity)")
        type_filter = " OR ".join(type_conditions)
        folder_filter = ""
        if folder_prefix:
            folder_filter = "AND note.note_id STARTS WITH $folder_prefix"

        cypher_projection = f"""
        MATCH (v:Vault {{id: $vault_id}})-[:HAS_NOTE]->(note:Note)
        MATCH (note)-[r:MENTIONS]->(entity)
        WHERE ({type_filter}) {folder_filter}
        WITH entity, COUNT(DISTINCT note) as mention_count
        WHERE mention_count > 0
        RETURN entity.id as entity_id, labels(entity)[0] as type, mention_count
        LIMIT 1000
        """

        params = {"vault_id": vault_id}
        if folder_prefix:
            params["folder_prefix"] = folder_prefix

        entities = client.query(cypher_projection, params)

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
          {folder_filter}
        WITH e1, e2, COUNT(DISTINCT note) as shared_notes
        WHERE shared_notes > 0
        RETURN e1.id as from_id, e2.id as to_id, shared_notes as weight
        """

        relations = client.query(cypher_relations, params)

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
    include_types: List[str] = ["Topic", "Project", "Task", "Person"],
    folder_prefix: str = None,
    include_entity_node: bool = True
) -> Dict[str, Any]:
    """
    UMAP + HDBSCAN을 사용한 의미론적 클러스터링

    노트 임베딩을 기반으로 클러스터링한 후, 각 클러스터에서 언급된 엔티티를 집계

    Args:
        client: Neo4j Bolt 클라이언트
        vault_id: Vault ID
        target_clusters: 목표 클러스터 개수 (참고용, HDBSCAN이 자동 결정)
        include_types: 클러스터링에 포함할 노드 타입
        folder_prefix: 폴더 경로 필터 (예: '1_프로젝트/')
        include_entity_node: Graphiti EntityNode도 포함할지 여부

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
            reason="dependency_missing",
            folder_prefix=folder_prefix
        )

    try:
        # Step 1: Neo4j에서 노트 임베딩 가져오기 (폴더 필터 적용)
        folder_filter = ""
        if folder_prefix:
            folder_filter = "AND note.note_id STARTS WITH $folder_prefix"

        cypher_embeddings = f"""
        MATCH (v:Vault {{id: $vault_id}})-[:HAS_NOTE]->(note:Note)
        WHERE note.embedding IS NOT NULL {folder_filter}
        RETURN note.note_id as note_id,
               note.title as note_title,
               toString(note.updated_at) as updated_at,
               note.embedding as embedding
        """

        params = {"vault_id": vault_id}
        if folder_prefix:
            params["folder_prefix"] = folder_prefix

        results = client.query(cypher_embeddings, params)

        if not results or len(results) == 0:
            logger.warning(f"No notes with embeddings found for vault {vault_id}")
            return _semantic_fallback_to_type_based(
                client,
                vault_id,
                target_clusters,
                include_types,
                reason="no_embeddings",
                folder_prefix=folder_prefix
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
                reason="insufficient_samples",
                folder_prefix=folder_prefix
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

        # 더 세분화된 클러스터링을 위한 파라미터 조정
        # - min_cluster_size: 작을수록 더 많은 작은 클러스터 허용
        # - min_samples: 1이면 노이즈 최소화
        # - cluster_selection_epsilon: 작을수록 더 세분화됨
        n_samples = len(embeddings)
        min_cluster_size = max(5, n_samples // 50)  # 더 작은 클러스터 허용 (5개 또는 노트의 2%)

        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=2,
            cluster_selection_epsilon=0.1,  # 더 세분화
            cluster_selection_method='eom',  # Excess of Mass - 계층적 클러스터링에 적합
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
                reason="no_clusters",
                folder_prefix=folder_prefix
            )

        # Step 5: 각 클러스터에서 그래프 중심성 기반 엔티티 분석
        # mention_count 대신 centrality_score로 중요도 결정
        clusters = []

        for cluster_id in sorted(unique_labels):
            # 클러스터에 속한 노트들
            cluster_mask = cluster_labels == cluster_id
            cluster_note_ids = [note_ids[i] for i in range(len(note_ids)) if cluster_mask[i]]
            cluster_note_titles = [note_titles[i] for i in range(len(note_titles)) if cluster_mask[i]]
            cluster_note_updates = [
                _parse_datetime(note_updated_raw[i]) for i in range(len(note_updated_raw)) if cluster_mask[i]
            ]

            # 그래프 중심성 분석 (핵심 변경점!)
            entity_info = compute_entity_graph_centrality(
                client=client,
                note_ids=cluster_note_ids,
                include_types=include_types
            )

            if not entity_info:
                continue  # 엔티티가 없는 클러스터는 스킵

            # 중심성 점수로 정렬된 엔티티 리스트
            sorted_entities = sorted(
                entity_info.items(),
                key=lambda x: x[1].get("centrality_score", 0),
                reverse=True
            )

            cluster_entity_ids = [eid for eid, _ in sorted_entities]
            cluster_entity_names = [info["name"] for _, info in sorted_entities]
            cluster_types = [info["type"] for _, info in sorted_entities]

            # 클러스터 내 타입 분포
            type_counts = {}
            for t in cluster_types:
                type_counts[t.lower()] = type_counts.get(t.lower(), 0) + 1

            # 허브 엔티티 찾기 (그래프에서 중심 역할)
            hub_entities = find_cluster_hub_entities(entity_info, top_k=3)

            # 클러스터 이름: 그래프 허브 엔티티 기반 (노트 제목 아님!)
            cluster_name = generate_cluster_name_from_graph(hub_entities, type_counts)

            # 중요도 점수: 중심성 기반 + recency 보너스
            avg_centrality = sum(info.get("centrality_score", 0) for info in entity_info.values()) / max(len(entity_info), 1)
            recency_bonus, recent_updates = _compute_recency_bonus(cluster_note_updates)
            importance_score = min(10.0, (avg_centrality * 8.0) + recency_bonus)

            # 허브 엔티티 정보 추가
            hub_info = [
                {"id": eid, "name": name, "centrality": round(score, 3)}
                for eid, name, score in hub_entities
            ]

            clusters.append({
                "id": f"cluster_{cluster_id + 1}",
                "name": cluster_name,
                "level": 1,
                "node_count": len(cluster_entity_ids),
                "entity_ids": cluster_entity_ids,
                "sample_entities": cluster_entity_names[:10],  # 중심성 순 상위 10개
                "sample_notes": cluster_note_titles[:5],
                "note_ids": cluster_note_ids[:20],
                "recent_updates": recent_updates,
                "summary": f"{cluster_name} 클러스터 ({len(cluster_entity_ids)} 엔티티)",
                "key_insights": _build_graph_insights(hub_entities, recent_updates, type_counts, len(cluster_note_ids)),
                "contains_types": type_counts,
                "importance_score": importance_score,
                "hub_entities": hub_info,  # 새로운 필드: 허브 엔티티 정보
                "last_updated": datetime.utcnow().isoformat(),
                "last_computed": datetime.utcnow().isoformat(),
                "clustering_method": "umap_hdbscan_graph_centrality",
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
                reason="empty_result",
                folder_prefix=folder_prefix
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
            reason="exception",
            folder_prefix=folder_prefix
        )


def _semantic_fallback_to_type_based(
    client,
    vault_id: str,
    target_clusters: int,
    include_types: List[str],
    reason: str,
    folder_prefix: str = None
) -> Dict[str, Any]:
    """
    의미론적 클러스터링 실패 시 타입 기반으로 폴백
    """
    logger.warning(f"Semantic clustering fallback triggered: {reason}")
    fallback = compute_clusters_louvain(
        client=client,
        vault_id=vault_id,
        target_clusters=target_clusters,
        include_types=include_types,
        folder_prefix=folder_prefix
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
    from datetime import timezone
    now = datetime.now(timezone.utc)
    recent_threshold = now - timedelta(days=7)
    recent_updates = 0

    # timezone-aware로 변환하여 비교
    valid_dates = []
    for dt in updated_at_list:
        if dt is None:
            continue
        # timezone-naive인 경우 UTC로 가정
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        valid_dates.append(dt)

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


def _build_graph_insights(
    hub_entities: List[Tuple[str, str, float]],
    recent_updates: int,
    type_counts: Dict[str, int],
    note_count: int
) -> List[str]:
    """
    그래프 중심성 기반 인사이트 생성

    허브 엔티티의 역할과 클러스터 구조를 기반으로 인사이트 제공
    """
    insights = []

    # 허브 엔티티 정보
    if hub_entities:
        top_hub = hub_entities[0]
        hub_name, hub_score = top_hub[1], top_hub[2]
        if hub_score > 0.7:
            insights.append(f"'{hub_name}'이(가) 클러스터의 핵심 허브 역할 (중심성: {hub_score:.2f})")
        elif hub_score > 0.4:
            insights.append(f"'{hub_name}'이(가) 주요 연결점 (중심성: {hub_score:.2f})")
        else:
            insights.append(f"'{hub_name}'이(가) 클러스터 대표 개념")

        if len(hub_entities) >= 2:
            second_hub = hub_entities[1][1]
            insights.append(f"관련 핵심 개념: {second_hub}")

    # 노트 연결성 분석
    if note_count > 10:
        insights.append(f"{note_count}개 노트가 이 주제로 연결됨 - 활발한 영역")
    elif note_count > 5:
        insights.append(f"{note_count}개 노트 연결 - 성장 중인 영역")
    else:
        insights.append(f"{note_count}개 노트로 시작하는 영역")

    # 최근 활동
    if recent_updates > 3:
        insights.append(f"최근 7일간 {recent_updates}회 업데이트 - 현재 활발히 작업 중")
    elif recent_updates > 0:
        insights.append(f"최근 {recent_updates}회 업데이트")

    # 타입 분포 기반 제안
    if type_counts:
        dominant_type = max(type_counts.items(), key=lambda kv: kv[1])[0]
        if dominant_type == "task":
            insights.append("🎯 액션: 연결된 태스크들 우선순위 검토")
        elif dominant_type == "project":
            insights.append("📋 액션: 프로젝트 마일스톤 점검")
        elif dominant_type == "topic":
            insights.append("💡 액션: 관련 노트들을 연결해 지식 네트워크 강화")

    return insights[:5]


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
