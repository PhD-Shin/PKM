"""
그래프 패턴 분석 서비스
- PageRank: 중요한 노트 찾기
- Community Detection: 클러스터 찾기
- Orphan Detection: 고립된 노트 찾기
"""
from typing import Dict, List, Any, Tuple
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


def calculate_pagerank(
    nodes: List[str],
    edges: List[Tuple[str, str]],
    damping: float = 0.85,
    iterations: int = 20
) -> Dict[str, float]:
    """
    PageRank 알고리즘으로 노드 중요도 계산

    Args:
        nodes: 노드 ID 리스트
        edges: (from, to) 튜플 리스트
        damping: damping factor (기본 0.85)
        iterations: 반복 횟수

    Returns:
        {node_id: pagerank_score} 딕셔너리
    """
    if not nodes:
        return {}

    # 그래프 구조 생성
    graph = defaultdict(list)
    out_degree = defaultdict(int)

    for from_node, to_node in edges:
        graph[from_node].append(to_node)
        out_degree[from_node] += 1

    # 초기 PageRank 값 (모든 노드 균등)
    n = len(nodes)
    pagerank = {node: 1.0 / n for node in nodes}

    # PageRank 반복 계산
    for _ in range(iterations):
        new_pagerank = {}

        for node in nodes:
            # Random surfer model
            rank = (1 - damping) / n

            # 들어오는 링크로부터 PageRank 누적
            for other_node in nodes:
                if node in graph[other_node]:
                    rank += damping * pagerank[other_node] / out_degree[other_node]

            new_pagerank[node] = rank

        pagerank = new_pagerank

    return pagerank


def detect_communities(
    nodes: List[str],
    edges: List[Tuple[str, str]]
) -> Dict[str, int]:
    """
    간단한 Community Detection (연결 요소 기반)

    Args:
        nodes: 노드 ID 리스트
        edges: (from, to) 튜플 리스트

    Returns:
        {node_id: community_id} 딕셔너리
    """
    if not nodes:
        return {}

    # 무향 그래프로 변환
    graph = defaultdict(set)
    for from_node, to_node in edges:
        graph[from_node].add(to_node)
        graph[to_node].add(from_node)

    # DFS로 연결 요소 찾기
    visited = set()
    communities = {}
    community_id = 0

    def dfs(node: str, community: int):
        visited.add(node)
        communities[node] = community
        for neighbor in graph[node]:
            if neighbor not in visited:
                dfs(neighbor, community)

    for node in nodes:
        if node not in visited:
            dfs(node, community_id)
            community_id += 1

    return communities


def find_orphan_notes(
    nodes: List[str],
    edges: List[Tuple[str, str]]
) -> List[str]:
    """
    고립된 노트 찾기 (연결이 없는 노트)

    Args:
        nodes: 노드 ID 리스트
        edges: (from, to) 튜플 리스트

    Returns:
        고립된 노트 ID 리스트
    """
    if not nodes:
        return []

    # 연결이 있는 노드 집합
    connected = set()
    for from_node, to_node in edges:
        connected.add(from_node)
        connected.add(to_node)

    # 연결이 없는 노트 반환
    orphans = [node for node in nodes if node not in connected]
    return orphans


def analyze_vault_patterns(
    user_id: str,
    vault_id: str
) -> Dict[str, Any]:
    """
    Vault 전체 패턴 분석

    Args:
        user_id: 사용자 ID
        vault_id: Vault ID

    Returns:
        패턴 분석 결과
    """
    from app.db.neo4j import get_neo4j_client

    client = get_neo4j_client()

    # 1. Vault의 모든 노트와 관계 가져오기
    cypher = """
    MATCH (u:User {id: $user_id})-[:OWNS]->(v:Vault {id: $vault_id})-[:HAS_NOTE]->(n:Note)
    OPTIONAL MATCH (n)-[r]->(related)
    WHERE related:Note OR related:Topic OR related:Project OR related:Task
    RETURN
        collect(DISTINCT n.note_id) AS notes,
        collect(DISTINCT {from: n.note_id, to: related.note_id, type: type(r)}) AS edges
    """

    result = client.query(cypher, {"user_id": user_id, "vault_id": vault_id})

    if not result or len(result) == 0:
        return {
            "important_notes": [],
            "communities": [],
            "orphan_notes": [],
            "stats": {
                "total_notes": 0,
                "total_connections": 0,
                "num_communities": 0,
                "num_orphans": 0
            }
        }

    notes = result[0].get("notes", [])
    edges_raw = result[0].get("edges", [])

    # None 제거
    notes = [n for n in notes if n is not None]
    edges = [(e["from"], e["to"]) for e in edges_raw
             if e and e.get("from") and e.get("to")]

    # 2. PageRank 계산
    pagerank_scores = calculate_pagerank(notes, edges)

    # 상위 10개 중요 노트
    important_notes = sorted(
        pagerank_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]

    # 3. Community Detection
    communities_map = detect_communities(notes, edges)

    # Community별로 그룹화
    community_groups = defaultdict(list)
    for note, comm_id in communities_map.items():
        community_groups[comm_id].append(note)

    # 크기순 정렬
    communities = sorted(
        [{"id": comm_id, "notes": note_list, "size": len(note_list)}
         for comm_id, note_list in community_groups.items()],
        key=lambda x: x["size"],
        reverse=True
    )

    # 4. 고립된 노트 찾기
    orphan_notes = find_orphan_notes(notes, edges)

    # 5. 통계
    stats = {
        "total_notes": len(notes),
        "total_connections": len(edges),
        "num_communities": len(communities),
        "num_orphans": len(orphan_notes),
        "avg_connections_per_note": len(edges) / len(notes) if notes else 0
    }

    return {
        "important_notes": [
            {"note_id": note, "score": round(score, 4)}
            for note, score in important_notes
        ],
        "communities": communities[:5],  # 상위 5개 커뮤니티
        "orphan_notes": orphan_notes[:20],  # 최대 20개
        "stats": stats
    }
