"""
Entity Cluster Service - Hybrid Graph + Embedding Clustering

Entity 노드들을 RELATES_TO 그래프 구조 + name_embedding 벡터 유사도로
하이브리드 클러스터링하여 2nd Brain 시각화 지원.

Flow:
1. Entity 노드와 name_embedding 가져오기
2. RELATES_TO 관계로 그래프 커뮤니티 탐지 (Louvain)
3. name_embedding 코사인 유사도로 시멘틱 클러스터링
4. 두 결과를 조합하여 최종 클러스터 결정

PKM Semantic Edge Types (PKM Type 조합 기반):
- Goal → Project: ACHIEVED_BY (목표 달성 프로젝트)
- Project → Task: REQUIRES (프로젝트 필수 태스크)
- Concept → Project/Task: USED_BY (개념 활용)
- Question → Insight: ANSWERED_BY (질문-답변)
- Insight → Resource: DERIVED_FROM (인사이트 출처)
- Topic → Topic: RELATED_TO (연관 주제)
- Resource → *: INFORMS (참고 자료)
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import numpy as np
from collections import defaultdict

logger = logging.getLogger(__name__)


# ============================================================
# PKM Semantic Edge Type Inference
# PKM Type 조합 기반으로 의미있는 관계 유형 추론
# ============================================================

# PKM Type 조합 → Semantic Edge Type 매핑
# (from_type, to_type) → (edge_type, edge_label_ko, description)
PKM_EDGE_TYPE_MATRIX = {
    # Goal 관계
    ("Goal", "Project"): ("ACHIEVED_BY", "달성 수단", "이 목표는 이 프로젝트로 달성"),
    ("Goal", "Task"): ("REQUIRES", "필요 태스크", "목표 달성에 필요한 작업"),
    ("Goal", "Goal"): ("CONTRIBUTES_TO", "기여", "하위 목표가 상위 목표에 기여"),
    ("Goal", "Topic"): ("FOCUSES_ON", "집중 영역", "목표가 집중하는 주제"),
    ("Goal", "Concept"): ("APPLIES", "적용 개념", "목표에 적용되는 개념"),

    # Project 관계
    ("Project", "Task"): ("REQUIRES", "필요 작업", "프로젝트 완료에 필요한 태스크"),
    ("Project", "Goal"): ("CONTRIBUTES_TO", "목표 기여", "프로젝트가 기여하는 목표"),
    ("Project", "Project"): ("DEPENDS_ON", "의존", "프로젝트 간 의존성"),
    ("Project", "Topic"): ("INVOLVES", "관련 주제", "프로젝트 관련 주제"),
    ("Project", "Concept"): ("USES", "사용 개념", "프로젝트에서 사용하는 개념"),
    ("Project", "Resource"): ("REFERENCES", "참고 자료", "프로젝트 참고 자료"),
    ("Project", "Question"): ("EXPLORES", "탐구 질문", "프로젝트에서 탐구하는 질문"),
    ("Project", "Insight"): ("PRODUCES", "도출 인사이트", "프로젝트에서 도출된 통찰"),

    # Task 관계
    ("Task", "Task"): ("BLOCKS", "선행 작업", "이 태스크가 선행되어야 함"),
    ("Task", "Project"): ("PART_OF", "소속 프로젝트", "태스크가 속한 프로젝트"),
    ("Task", "Topic"): ("INVOLVES", "관련 주제", "태스크 관련 주제"),
    ("Task", "Concept"): ("USES", "사용 개념", "태스크에서 사용하는 개념"),
    ("Task", "Resource"): ("REFERENCES", "참고 자료", "태스크 참고 자료"),
    ("Task", "Insight"): ("PRODUCES", "도출 인사이트", "태스크에서 얻은 통찰"),

    # Topic 관계
    ("Topic", "Topic"): ("RELATED_TO", "연관 주제", "연관된 주제 영역"),
    ("Topic", "Concept"): ("CONTAINS", "포함 개념", "주제에 포함된 개념"),
    ("Topic", "Project"): ("APPLIED_IN", "적용 프로젝트", "주제가 적용된 프로젝트"),
    ("Topic", "Resource"): ("DOCUMENTED_IN", "문서화", "주제가 문서화된 자료"),
    ("Topic", "Question"): ("RAISES", "제기 질문", "주제에서 제기되는 질문"),
    ("Topic", "Insight"): ("REVEALS", "드러난 통찰", "주제에서 드러난 인사이트"),

    # Concept 관계
    ("Concept", "Concept"): ("RELATES_TO", "관련 개념", "연관된 개념"),
    ("Concept", "Topic"): ("BELONGS_TO", "소속 주제", "개념이 속한 주제"),
    ("Concept", "Project"): ("APPLIED_IN", "적용처", "개념이 적용된 프로젝트"),
    ("Concept", "Task"): ("USED_IN", "사용처", "개념이 사용된 태스크"),
    ("Concept", "Resource"): ("DEFINED_IN", "정의 출처", "개념이 정의된 자료"),

    # Question 관계
    ("Question", "Insight"): ("ANSWERED_BY", "답변", "질문에 대한 답변 인사이트"),
    ("Question", "Topic"): ("ABOUT", "관련 주제", "질문의 주제"),
    ("Question", "Question"): ("LEADS_TO", "연결 질문", "이 질문이 이끄는 후속 질문"),
    ("Question", "Project"): ("EXPLORED_IN", "탐구처", "질문이 탐구되는 프로젝트"),
    ("Question", "Resource"): ("ADDRESSED_IN", "다룬 자료", "질문을 다루는 자료"),

    # Insight 관계
    ("Insight", "Resource"): ("DERIVED_FROM", "출처", "인사이트의 출처 자료"),
    ("Insight", "Insight"): ("SUPPORTS", "뒷받침", "인사이트 간 뒷받침 관계"),
    ("Insight", "Question"): ("ANSWERS", "답변 대상", "인사이트가 답변하는 질문"),
    ("Insight", "Project"): ("INFORMS", "적용처", "인사이트가 적용되는 프로젝트"),
    ("Insight", "Topic"): ("ABOUT", "관련 주제", "인사이트의 주제"),
    ("Insight", "Concept"): ("CLARIFIES", "명확화", "인사이트가 명확히 하는 개념"),

    # Resource 관계
    ("Resource", "Topic"): ("COVERS", "다루는 주제", "자료가 다루는 주제"),
    ("Resource", "Concept"): ("DEFINES", "정의 개념", "자료가 정의하는 개념"),
    ("Resource", "Resource"): ("CITES", "인용", "자료 간 인용 관계"),
    ("Resource", "Question"): ("ADDRESSES", "다루는 질문", "자료가 다루는 질문"),
    ("Resource", "Insight"): ("PROVIDES", "제공 인사이트", "자료에서 제공하는 통찰"),
    ("Resource", "Project"): ("INFORMS", "정보 제공", "프로젝트에 정보 제공"),

    # Person 관계 (하위 호환성)
    ("Person", "Project"): ("WORKS_ON", "작업 중", "사람이 작업 중인 프로젝트"),
    ("Person", "Task"): ("ASSIGNED_TO", "담당", "사람에게 할당된 태스크"),
    ("Person", "Topic"): ("INTERESTED_IN", "관심 분야", "사람의 관심 주제"),
    ("Person", "Person"): ("COLLABORATES_WITH", "협력", "협력 관계"),
}


def infer_semantic_edge_type(
    from_type: str,
    to_type: str,
    fact: str = None
) -> Dict[str, str]:
    """
    PKM Type 조합을 기반으로 semantic edge type 추론

    Args:
        from_type: source entity의 PKM Type
        to_type: target entity의 PKM Type
        fact: Graphiti가 추출한 fact (있으면 활용)

    Returns:
        {
            "edge_type": "ACHIEVED_BY",
            "edge_label": "달성 수단",
            "description": "이 목표는 이 프로젝트로 달성",
            "fact": "..." (있으면)
        }
    """
    # 정규화
    from_type = from_type or "Topic"
    to_type = to_type or "Topic"

    # Person → Topic 매핑 (하위 호환성)
    if from_type not in PKM_EDGE_TYPE_MATRIX.get((from_type, to_type), ("", "", ""))[0]:
        pass  # 그대로 사용

    # 매핑 조회
    edge_info = PKM_EDGE_TYPE_MATRIX.get((from_type, to_type))

    if edge_info:
        edge_type, edge_label, description = edge_info
    else:
        # 기본값: 범용 관계
        edge_type = "RELATES_TO"
        edge_label = "관련"
        description = f"{from_type}와 {to_type} 간의 관계"

    result = {
        "edge_type": edge_type,
        "edge_label": edge_label,
        "description": description
    }

    # fact가 있으면 추가 (Graphiti 추출 결과)
    if fact and fact.strip():
        result["fact"] = fact.strip()

    return result


def get_relates_to_edges_with_semantic_types(
    client,
    entity_uuids: List[str]
) -> List[Dict[str, Any]]:
    """
    Entity 간 RELATES_TO 관계 + PKM Type 기반 Semantic Edge Type 가져오기

    Returns:
        [{
            "from_uuid": str,
            "to_uuid": str,
            "from_name": str,
            "to_name": str,
            "from_type": str,
            "to_type": str,
            "weight": float,
            "fact": str (if exists),
            "semantic_type": {
                "edge_type": str,
                "edge_label": str,
                "description": str
            }
        }, ...]
    """
    cypher = """
    MATCH (e1:Entity)-[r:RELATES_TO]->(e2:Entity)
    WHERE e1.uuid IN $uuids AND e2.uuid IN $uuids
    RETURN e1.uuid as from_uuid,
           e1.name as from_name,
           e1.pkm_type as from_type,
           e2.uuid as to_uuid,
           e2.name as to_name,
           e2.pkm_type as to_type,
           COALESCE(r.weight, 1.0) as weight,
           r.fact as fact
    """

    results = client.query(cypher, {"uuids": entity_uuids})

    edges = []
    for row in results or []:
        from_type = row.get("from_type") or "Topic"
        to_type = row.get("to_type") or "Topic"
        fact = row.get("fact", "")

        # Semantic type 추론
        semantic_info = infer_semantic_edge_type(from_type, to_type, fact)

        edges.append({
            "from_uuid": row["from_uuid"],
            "to_uuid": row["to_uuid"],
            "from_name": row.get("from_name", row["from_uuid"]),
            "to_name": row.get("to_name", row["to_uuid"]),
            "from_type": from_type,
            "to_type": to_type,
            "weight": row.get("weight", 1.0),
            "fact": fact,
            "semantic_type": semantic_info
        })

    return edges


# ============================================================
# UMAP + HDBSCAN imports (lazy)
try:
    import hdbscan
    HDBSCAN_AVAILABLE = True
except ImportError:
    HDBSCAN_AVAILABLE = False
    logger.warning("HDBSCAN not available. Embedding clustering will use fallback.")

# NetworkX for Louvain community detection
try:
    import networkx as nx
    from networkx.algorithms.community import louvain_communities
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    logger.warning("NetworkX not available. Graph clustering will use fallback.")


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """두 벡터의 코사인 유사도 계산"""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def get_entities_with_embeddings(
    client,
    limit: int = 1000,
    folder_prefix: str = None,
    min_connections: int = 1
) -> List[Dict[str, Any]]:
    """
    Entity 노드들 가져오기 (embedding 옵션)

    두 가지 경로 지원:
    1. Note -[:MENTIONS]-> Entity (직접 관계)
    2. Episodic -[:MENTIONS]-> Entity (Graphiti 관계, Episodic.name = 'note_' + note_id)

    Args:
        client: Neo4j 클라이언트
        limit: 최대 엔티티 수
        folder_prefix: 폴더 경로 필터 (예: '1_프로젝트/'). 해당 폴더의 노트가 MENTIONS하는 엔티티만 반환
        min_connections: 최소 연결 노트 수 (기본 1). 2로 설정하면 2개 이상 노트에서 언급된 엔티티만 반환

    Returns:
        [{uuid, name, summary, pkm_type, name_embedding, mention_count}, ...]
    """
    folder_condition = "n.note_id STARTS WITH $folder_prefix AND" if folder_prefix else ""
    folder_condition2 = "n2.note_id STARTS WITH $folder_prefix AND" if folder_prefix else ""

    # 두 경로를 UNION으로 합침
    cypher = f"""
    // 방법1: 직접 MENTIONS 관계 (Note -> Entity)
    MATCH (n:Note)-[:MENTIONS]->(e:Entity)
    WHERE {folder_condition} e.name IS NOT NULL
    WITH e, collect(DISTINCT n.note_id) as note_ids
    RETURN e.uuid as uuid,
           e.name as name,
           e.summary as summary,
           e.pkm_type as pkm_type,
           e.name_embedding as embedding,
           note_ids

    UNION

    // 방법2: Episodic 통한 연결 (Graphiti)
    MATCH (ep:Episodic)-[:MENTIONS]->(e:Entity)
    WHERE e.name IS NOT NULL AND ep.name IS NOT NULL AND ep.name STARTS WITH 'note_'
    WITH e, ep, replace(ep.name, 'note_', '') as derived_note_id
    MATCH (n2:Note)
    WHERE {folder_condition2} n2.note_id = derived_note_id
    WITH e, collect(DISTINCT n2.note_id) as note_ids
    WHERE size(note_ids) > 0
    RETURN e.uuid as uuid,
           e.name as name,
           e.summary as summary,
           e.pkm_type as pkm_type,
           e.name_embedding as embedding,
           note_ids
    """

    results = client.query(cypher, {
        "folder_prefix": folder_prefix or "",
        "limit": limit,
        "min_connections": min_connections
    })

    # UNION 결과 병합 (같은 entity의 note_ids 합치기)
    entity_map = {}
    for row in results or []:
        uuid = row["uuid"]
        if uuid not in entity_map:
            entity_map[uuid] = {
                "uuid": uuid,
                "name": row["name"] or uuid,
                "summary": row.get("summary", ""),
                "pkm_type": row.get("pkm_type", "Topic"),
                "embedding": row.get("embedding"),
                "note_ids": set(row.get("note_ids", []) or [])
            }
        else:
            entity_map[uuid]["note_ids"].update(row.get("note_ids", []) or [])

    # min_connections 필터 및 정렬
    filtered = [
        {**data, "mention_count": len(data["note_ids"])}
        for data in entity_map.values()
        if len(data["note_ids"]) >= min_connections
    ]
    filtered.sort(key=lambda x: x["mention_count"], reverse=True)

    # note_ids는 set이므로 list로 변환하지 않고 제거 (필요 없음)
    entities = []
    for item in filtered[:limit]:
        entities.append({
            "uuid": item["uuid"],
            "name": item["name"],
            "summary": item["summary"],
            "pkm_type": item["pkm_type"],
            "embedding": item["embedding"],
            "mention_count": item["mention_count"]
        })

    return entities


def get_relates_to_edges(client, entity_uuids: List[str]) -> List[Tuple[str, str, float]]:
    """
    Entity 간 RELATES_TO 관계 가져오기

    Returns:
        [(from_uuid, to_uuid, weight), ...]
    """
    cypher = """
    MATCH (e1:Entity)-[r:RELATES_TO]->(e2:Entity)
    WHERE e1.uuid IN $uuids AND e2.uuid IN $uuids
    RETURN e1.uuid as from_uuid, e2.uuid as to_uuid,
           COALESCE(r.weight, 1.0) as weight
    """

    results = client.query(cypher, {"uuids": entity_uuids})

    edges = []
    for row in results or []:
        edges.append((row["from_uuid"], row["to_uuid"], row.get("weight", 1.0)))

    return edges


def cluster_by_graph_louvain(
    entity_uuids: List[str],
    edges: List[Tuple[str, str, float]],
    resolution: float = 1.0
) -> Dict[str, int]:
    """
    RELATES_TO 그래프 기반 Louvain 커뮤니티 탐지

    Args:
        entity_uuids: 엔티티 UUID 리스트
        edges: (from, to, weight) 튜플 리스트
        resolution: Louvain 해상도 파라미터 (높을수록 더 많은 클러스터)

    Returns:
        {entity_uuid: cluster_id}
    """
    if not NETWORKX_AVAILABLE:
        # Fallback: 모든 엔티티를 하나의 클러스터로
        return {uuid: 0 for uuid in entity_uuids}

    if not edges:
        # 엣지가 없으면 각 엔티티가 독립 클러스터
        return {uuid: i for i, uuid in enumerate(entity_uuids)}

    # NetworkX 그래프 생성
    G = nx.Graph()
    G.add_nodes_from(entity_uuids)

    for from_uuid, to_uuid, weight in edges:
        G.add_edge(from_uuid, to_uuid, weight=weight)

    # Louvain 커뮤니티 탐지
    try:
        communities = louvain_communities(G, weight='weight', resolution=resolution, seed=42)

        # 결과를 dict로 변환
        uuid_to_cluster = {}
        for cluster_id, community in enumerate(communities):
            for uuid in community:
                uuid_to_cluster[uuid] = cluster_id

        # 연결되지 않은 노드들은 새 클러스터로
        next_cluster = len(communities)
        for uuid in entity_uuids:
            if uuid not in uuid_to_cluster:
                uuid_to_cluster[uuid] = next_cluster
                next_cluster += 1

        return uuid_to_cluster

    except Exception as e:
        logger.error(f"Louvain clustering failed: {e}")
        return {uuid: i for i, uuid in enumerate(entity_uuids)}


def cluster_by_pkm_type(
    entities: List[Dict[str, Any]]
) -> Dict[str, int]:
    """
    PKM Core 8 Type 기반 클러스터링

    생산성 극대화를 위해 명확한 8개 카테고리로 분류:
    - Goal: 장기 목표
    - Project: 진행 중인 프로젝트
    - Task: 실행 가능한 할일
    - Topic: 주제/분야
    - Concept: 개념/아이디어
    - Question: 탐구할 질문
    - Insight: 통찰/발견
    - Resource: 참고 자료

    Note: Person은 Topic(3)으로 매핑됨 (하위 호환성)

    Args:
        entities: 엔티티 리스트

    Returns:
        {entity_uuid: cluster_id}
    """
    # PKM Core 8 Types (Person은 Topic으로 매핑)
    type_to_cluster = {
        "Goal": 0,
        "Project": 1,
        "Task": 2,
        "Topic": 3,
        "Concept": 4,
        "Question": 5,
        "Insight": 6,
        "Resource": 7,
        "Person": 3  # Person은 Topic으로 분류
    }

    return {
        e["uuid"]: type_to_cluster.get(e.get("pkm_type", "Topic"), 3)
        for e in entities
    }


def cluster_by_embedding_hdbscan(
    entities: List[Dict[str, Any]],
    min_cluster_size: int = 5,
    min_samples: int = 2
) -> Dict[str, int]:
    """
    name_embedding 기반 HDBSCAN 클러스터링 (레거시 - pkm_type 기반으로 대체됨)

    Args:
        entities: embedding이 포함된 엔티티 리스트
        min_cluster_size: 최소 클러스터 크기
        min_samples: 최소 샘플 수

    Returns:
        {entity_uuid: cluster_id} (노이즈는 -1)
    """
    if not HDBSCAN_AVAILABLE:
        # Fallback: pkm_type으로 클러스터링 (8 Core Types + Person)
        type_to_cluster = {
            "Goal": 0, "Project": 1, "Task": 2, "Topic": 3,
            "Concept": 4, "Question": 5, "Insight": 6, "Resource": 7,
            "Person": 8
        }
        return {
            e["uuid"]: type_to_cluster.get(e.get("pkm_type", "Topic"), 3)
            for e in entities
        }

    # 임베딩 추출
    valid_entities = [e for e in entities if e.get("embedding")]
    if len(valid_entities) < min_cluster_size:
        # embedding 없으면 pkm_type fallback 사용
        type_to_cluster = {
            "Goal": 0, "Project": 1, "Task": 2, "Topic": 3,
            "Concept": 4, "Question": 5, "Insight": 6, "Resource": 7,
            "Person": 8
        }
        return {
            e["uuid"]: type_to_cluster.get(e.get("pkm_type", "Topic"), 3)
            for e in entities
        }

    embeddings = np.array([e["embedding"] for e in valid_entities], dtype=float)

    # 파라미터 조정
    actual_min_cluster_size = max(3, min(min_cluster_size, len(valid_entities) // 10))

    try:
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=actual_min_cluster_size,
            min_samples=min_samples,
            metric='euclidean',
            cluster_selection_method='eom'
        )
        labels = clusterer.fit_predict(embeddings)

        result = {}
        for i, entity in enumerate(valid_entities):
            result[entity["uuid"]] = int(labels[i])

        # 임베딩 없는 엔티티는 노이즈로 표시
        for e in entities:
            if e["uuid"] not in result:
                result[e["uuid"]] = -1

        return result

    except Exception as e:
        logger.error(f"HDBSCAN clustering failed: {e}")
        return {e["uuid"]: 0 for e in entities}


def merge_cluster_assignments(
    graph_clusters: Dict[str, int],
    embedding_clusters: Dict[str, int],
    graph_weight: float = 0.4,
    embedding_weight: float = 0.6
) -> Dict[str, int]:
    """
    그래프 클러스터와 임베딩 클러스터를 병합

    전략:
    1. 임베딩 클러스터를 기본으로 사용 (시멘틱 유사도)
    2. 같은 그래프 클러스터에 있으면서 임베딩 클러스터가 다른 경우 병합 고려
    3. 노이즈(-1)는 그래프 클러스터 사용

    Returns:
        {entity_uuid: final_cluster_id}
    """
    all_uuids = set(graph_clusters.keys()) | set(embedding_clusters.keys())

    # 임베딩 클러스터를 기본으로
    final_clusters = {}

    # 먼저 임베딩 클러스터 할당
    for uuid in all_uuids:
        emb_cluster = embedding_clusters.get(uuid, -1)
        graph_cluster = graph_clusters.get(uuid, -1)

        if emb_cluster >= 0:
            # 임베딩 클러스터가 유효하면 그것 사용
            final_clusters[uuid] = emb_cluster
        elif graph_cluster >= 0:
            # 임베딩이 노이즈면 그래프 클러스터 사용 (오프셋 적용)
            max_emb = max(embedding_clusters.values()) if embedding_clusters else 0
            final_clusters[uuid] = max_emb + 1 + graph_cluster
        else:
            # 둘 다 없으면 독립 클러스터
            final_clusters[uuid] = -1

    # 노이즈(-1) 엔티티들을 가장 가까운 클러스터에 재할당
    # (그래프 연결이 있는 클러스터로)
    noise_uuids = [u for u, c in final_clusters.items() if c == -1]

    for uuid in noise_uuids:
        graph_cluster = graph_clusters.get(uuid, -1)
        if graph_cluster >= 0:
            # 같은 그래프 클러스터에 있는 다른 엔티티들의 클러스터 확인
            same_graph = [u for u, g in graph_clusters.items() if g == graph_cluster and u != uuid]
            if same_graph:
                # 가장 많이 등장하는 클러스터로 할당
                cluster_counts = defaultdict(int)
                for u in same_graph:
                    c = final_clusters.get(u, -1)
                    if c >= 0:
                        cluster_counts[c] += 1

                if cluster_counts:
                    final_clusters[uuid] = max(cluster_counts, key=cluster_counts.get)

    # 여전히 -1인 것들에게 새 클러스터 ID 부여
    max_cluster = max(c for c in final_clusters.values() if c >= 0) if any(c >= 0 for c in final_clusters.values()) else -1

    next_id = max_cluster + 1
    for uuid in final_clusters:
        if final_clusters[uuid] == -1:
            final_clusters[uuid] = next_id
            next_id += 1

    return final_clusters


def find_cluster_representative(
    entities: List[Dict[str, Any]],
    cluster_uuids: List[str]
) -> Tuple[str, str]:
    """
    클러스터의 대표 엔티티 찾기 (이름이 가장 짧고 명확한 것)

    Returns:
        (uuid, name)
    """
    cluster_entities = [e for e in entities if e["uuid"] in cluster_uuids]

    if not cluster_entities:
        return ("", "Unknown Cluster")

    # 요약이 있는 엔티티 우선, 그 다음 이름 길이로 정렬
    sorted_entities = sorted(
        cluster_entities,
        key=lambda e: (
            0 if e.get("summary") else 1,  # 요약 있으면 우선
            len(e.get("name", "") or ""),   # 이름 길이
        )
    )

    top = sorted_entities[0]
    return (top["uuid"], top.get("name", top["uuid"]))


def compute_entity_clusters_hybrid(
    client,
    min_cluster_size: int = 3,
    resolution: float = 1.0,
    folder_prefix: str = None,
    min_connections: int = 1
) -> Dict[str, Any]:
    """
    Entity 노드들을 PKM Core 8 Type 기반으로 클러스터링

    생산성 극대화를 위해 HDBSCAN 대신 PKM 8 Type 사용:
    - Goal, Project, Task: 실행 가능한 액션 흐름
    - Topic, Concept, Insight: 지식 관리
    - Question: 탐구 영역
    - Resource: 참고 자료
    - Person: 인맥 관리

    Args:
        client: Neo4j 클라이언트
        min_cluster_size: 최소 클러스터 크기 (pkm_type에서는 미사용)
        resolution: Louvain 해상도 (pkm_type에서는 미사용)
        folder_prefix: 폴더 경로 필터 (예: '1_프로젝트/'). 해당 폴더의 노트가 MENTIONS하는 엔티티만 클러스터링
        min_connections: 최소 연결 노트 수 (기본 1). 단일 노트 연결도 포함 (의미론적으로 중요할 수 있음)

    Returns:
        {
            "clusters": [...],
            "edges": [...],
            "total_entities": int,
            "method": str
        }
    """
    folder_info = f" for folder '{folder_prefix}'" if folder_prefix else ""
    logger.info(f"Starting PKM Type entity clustering{folder_info} (min_connections={min_connections})...")

    # PKM Core 8 Types 정의 (Person은 별도 처리)
    PKM_TYPES = {
        0: {"id": "Goal", "name": "🎯 Goal", "description": "장기 목표"},
        1: {"id": "Project", "name": "📁 Project", "description": "진행 중인 프로젝트"},
        2: {"id": "Task", "name": "✅ Task", "description": "실행 가능한 할일"},
        3: {"id": "Topic", "name": "📚 Topic", "description": "주제/분야"},
        4: {"id": "Concept", "name": "💡 Concept", "description": "개념/아이디어"},
        5: {"id": "Question", "name": "❓ Question", "description": "탐구할 질문"},
        6: {"id": "Insight", "name": "✨ Insight", "description": "통찰/발견"},
        7: {"id": "Resource", "name": "📎 Resource", "description": "참고 자료"}
    }

    try:
        # Step 1: Entity 데이터 가져오기 (min_connections 필터 적용)
        entities = get_entities_with_embeddings(
            client,
            limit=1000,
            folder_prefix=folder_prefix,
            min_connections=min_connections
        )

        if not entities:
            logger.warning("No entities found for clustering")
            return {
                "clusters": [],
                "edges": [],
                "total_entities": 0,
                "method": "pkm_type",
                "computed_at": datetime.utcnow().isoformat()
            }

        logger.info(f"Found {len(entities)} entities")

        entity_uuids = [e["uuid"] for e in entities]
        uuid_to_entity = {e["uuid"]: e for e in entities}

        # Step 2: RELATES_TO 엣지 가져오기 (클러스터 간 연결용)
        relates_to_edges = get_relates_to_edges(client, entity_uuids)
        logger.info(f"Found {len(relates_to_edges)} RELATES_TO edges")

        # Step 3: PKM Type 기반 클러스터링 (HDBSCAN 대체)
        pkm_clusters = cluster_by_pkm_type(entities)
        n_pkm_types = len(set(pkm_clusters.values()))
        logger.info(f"PKM Type clustering: {n_pkm_types} types found")

        # Step 4: 클러스터 데이터 구성
        cluster_groups = defaultdict(list)
        for uuid, cluster_id in pkm_clusters.items():
            cluster_groups[cluster_id].append(uuid)

        # 클러스터 정보 생성 (PKM 8 Core Type 모두 표시)
        clusters = []
        for cluster_id in range(8):  # 0-7: 8개 Core Type (Person 제외)
            uuids = cluster_groups.get(cluster_id, [])

            # PKM Type 정보
            type_info = PKM_TYPES.get(cluster_id, {"id": "Topic", "name": "📚 Topic", "description": "주제"})

            # 클러스터 내 엔티티들
            cluster_entities = [uuid_to_entity[u] for u in uuids if u in uuid_to_entity]

            # mention_count 기준 정렬 (상위 엔티티가 대표)
            cluster_entities.sort(key=lambda e: e.get("mention_count", 0), reverse=True)

            # 샘플 엔티티 이름 (상위 10개)
            sample_names = [e["name"] for e in cluster_entities[:10]]

            # 내부 연결 수 (RELATES_TO)
            uuid_set = set(uuids)
            internal_edges = sum(
                1 for f, t, _ in relates_to_edges
                if f in uuid_set and t in uuid_set
            )

            clusters.append({
                "id": f"cluster_{type_info['id'].lower()}",
                "name": type_info["name"],
                "pkm_type": type_info["id"],
                "description": type_info["description"],
                "entity_count": len(uuids),
                "entity_uuids": uuids,
                "sample_entities": sample_names,
                "type_distribution": {type_info["id"]: len(uuids)},
                "internal_edges": internal_edges,
                "cohesion_score": internal_edges / max(len(uuids), 1),
                "computed_at": datetime.utcnow().isoformat()
            })

        # 생산성 흐름 순서로 정렬: Goal → Project → Task → Topic → Concept → Question → Insight → Resource
        # (이미 range(8) 순서대로 생성됨, 정렬 불필요)

        # 클러스터 간 엣지 계산 (공유 RELATES_TO)
        cluster_edges = _compute_cluster_edges(clusters, relates_to_edges)

        return {
            "clusters": clusters,
            "edges": cluster_edges,
            "total_entities": len(entities),
            "clustered_entities": sum(c["entity_count"] for c in clusters),
            "method": "pkm_type",
            "pkm_types_found": n_pkm_types,
            "computed_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"PKM Type entity clustering failed: {e}")
        raise


def _compute_cluster_edges(
    clusters: List[Dict[str, Any]],
    relates_to_edges: List[Tuple[str, str, float]]
) -> List[Dict[str, Any]]:
    """클러스터 간 연결 관계 계산"""

    # UUID -> cluster_id 매핑
    uuid_to_cluster = {}
    for cluster in clusters:
        for uuid in cluster.get("entity_uuids", []):
            uuid_to_cluster[uuid] = cluster["id"]

    # 클러스터 간 엣지 카운트
    cluster_edge_counts = defaultdict(int)

    for from_uuid, to_uuid, weight in relates_to_edges:
        from_cluster = uuid_to_cluster.get(from_uuid)
        to_cluster = uuid_to_cluster.get(to_uuid)

        if from_cluster and to_cluster and from_cluster != to_cluster:
            # 정렬된 키로 저장 (방향 무시)
            edge_key = tuple(sorted([from_cluster, to_cluster]))
            cluster_edge_counts[edge_key] += 1

    # 클러스터 ID -> PKM Type 매핑
    cluster_types = {c["id"]: c.get("pkm_type", "Topic") for c in clusters}

    # 엣지 리스트 생성
    edges = []
    for (from_c, to_c), count in cluster_edge_counts.items():
        if count >= 1:  # 최소 1개 연결
            # PKM Type 기반 관계 추론
            from_type = cluster_types.get(from_c, "Topic")
            to_type = cluster_types.get(to_c, "Topic")
            
            semantic_info = infer_semantic_edge_type(from_type, to_type)
            
            edges.append({
                "from": from_c,
                "to": to_c,
                "weight": count,
                "relation_type": semantic_info["edge_type"],  # e.g., "REQUIRES"
                "label": semantic_info["edge_label"] or semantic_info["edge_type"] # e.g., "필요 태스크"
            })

    return edges


def get_cluster_detail(
    client,
    cluster_id: str,
    clusters_data: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    특정 클러스터의 상세 정보 가져오기

    Args:
        client: Neo4j 클라이언트
        cluster_id: 클러스터 ID
        clusters_data: compute_entity_clusters_hybrid 결과

    Returns:
        클러스터 상세 정보
    """
    clusters = clusters_data.get("clusters", [])
    target = next((c for c in clusters if c["id"] == cluster_id), None)

    if not target:
        return None

    # 클러스터 내 엔티티들의 상세 정보
    uuids = target.get("entity_uuids", [])

    cypher = """
    MATCH (e:Entity)
    WHERE e.uuid IN $uuids
    OPTIONAL MATCH (e)-[r:RELATES_TO]-(other:Entity)
    WHERE other.uuid IN $uuids
    OPTIONAL MATCH (n:Note)-[:MENTIONS]->(e)
    RETURN e.uuid as uuid,
           e.name as name,
           e.summary as summary,
           e.pkm_type as pkm_type,
           count(DISTINCT r) as internal_connections,
           collect(DISTINCT n.note_id)[..5] as connected_notes
    ORDER BY internal_connections DESC
    """

    results = client.query(cypher, {"uuids": uuids})

    entities = []
    for row in results or []:
        entities.append({
            "uuid": row["uuid"],
            "name": row["name"],
            "summary": row.get("summary", ""),
            "pkm_type": row.get("pkm_type", "Topic"),
            "connections": row.get("internal_connections", 0),
            "connected_notes": row.get("connected_notes", [])
        })

    # 내부 RELATES_TO 관계들 (PKM Type 포함 - Semantic Edge 추론용)
    cypher_edges = """
    MATCH (e1:Entity)-[r:RELATES_TO]->(e2:Entity)
    WHERE e1.uuid IN $uuids AND e2.uuid IN $uuids
    RETURN e1.uuid as from_uuid,
           e1.name as from_name,
           e1.pkm_type as from_type,
           e2.uuid as to_uuid,
           e2.name as to_name,
           e2.pkm_type as to_type,
           r.fact as fact,
           r.weight as weight
    """

    edge_results = client.query(cypher_edges, {"uuids": uuids})

    edges = []
    for row in edge_results or []:
        from_type = row.get("from_type") or "Topic"
        to_type = row.get("to_type") or "Topic"
        fact = row.get("fact", "")

        # Semantic Edge Type 추론
        semantic_info = infer_semantic_edge_type(from_type, to_type, fact)

        edges.append({
            "from": row["from_uuid"],
            "from_name": row.get("from_name", row["from_uuid"]),
            "from_type": from_type,
            "to": row["to_uuid"],
            "to_name": row.get("to_name", row["to_uuid"]),
            "to_type": to_type,
            "fact": fact,
            "weight": row.get("weight", 1.0),
            "semantic_type": semantic_info["edge_type"],
            "semantic_label": semantic_info["edge_label"],
            "semantic_description": semantic_info["description"]
        })

    return {
        **target,
        "entities": entities,
        "internal_edges": edges,
        "has_semantic_edges": True,
        "semantic_edge_count": len(edges)
    }
