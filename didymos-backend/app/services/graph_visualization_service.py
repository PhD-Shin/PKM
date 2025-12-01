"""
그래프 시각화 서비스
"""
from app.db.neo4j import get_neo4j_client
import logging

logger = logging.getLogger(__name__)


def get_note_graph(note_id: str, depth: int = 1):
    """
    기존 간단 그래프 조회 (raw)
    """
    try:
        client = get_neo4j_client()

        cypher = """
        MATCH path = (n:Note {note_id: $note_id})-[r*1..2]-(connected)
        WITH nodes(path) AS pathNodes, relationships(path) AS pathRels
        UNWIND pathNodes AS node
        WITH DISTINCT node, pathRels
        OPTIONAL MATCH (node)-[rel]-(other)
        WHERE other IN pathNodes
        RETURN
            COLLECT(DISTINCT {
                id: COALESCE(node.note_id, node.id),
                label: COALESCE(node.title, node.id, labels(node)[0]),
                type: labels(node)[0],
                properties: properties(node)
            }) AS nodes,
            COLLECT(DISTINCT {
                from: COALESCE(startNode(rel).note_id, startNode(rel).id),
                to: COALESCE(endNode(rel).note_id, endNode(rel).id),
                type: type(rel),
                label: type(rel)
            }) AS edges
        """

        params = {"note_id": note_id}
        results = client.query(cypher, params)

        if not results or len(results) == 0:
            logger.warning(f"No graph data found for note: {note_id}")
            return {"nodes": [], "edges": []}

        result = results[0]
        nodes = result.get("nodes", [])
        edges = result.get("edges", [])

        unique_nodes = {}
        for node in nodes:
            if node and node.get("id"):
                node_id = node["id"]
                if node_id not in unique_nodes:
                    unique_nodes[node_id] = node

        unique_edges = []
        seen_edges = set()
        for edge in edges:
            if edge and edge.get("from") and edge.get("to"):
                edge_key = (edge["from"], edge["to"], edge.get("type", ""))
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    unique_edges.append(edge)

        return {
            "nodes": list(unique_nodes.values()),
            "edges": unique_edges
        }

    except Exception as e:
        logger.error(f"Error getting note graph: {e}")
        return {"nodes": [], "edges": []}


def get_note_graph_vis(note_id: str, hops: int = 1):
    """
    vis-network 친화적인 스타일 포함 그래프 데이터
    """
    try:
        client = get_neo4j_client()
        nodes = []
        edges = []

        center = _get_center_node(client, note_id)
        if center:
            nodes.append(center)

        topic_nodes, topic_edges = _get_topics(client, note_id)
        nodes.extend(topic_nodes)
        edges.extend(topic_edges)

        project_nodes, project_edges = _get_projects(client, note_id)
        nodes.extend(project_nodes)
        edges.extend(project_edges)

        task_nodes, task_edges = _get_tasks(client, note_id)
        nodes.extend(task_nodes)
        edges.extend(task_edges)

        if hops >= 2:
            related_nodes, related_edges = _get_related_notes(client, note_id)
            nodes.extend(related_nodes)
            edges.extend(related_edges)

        uniq_nodes = {}
        for n in nodes:
            if n and n.get("id"):
                uniq_nodes[n["id"]] = n

        uniq_edges = []
        seen = set()
        for e in edges:
            key = (e.get("from"), e.get("to"), e.get("label", ""))
            if e.get("from") and e.get("to") and key not in seen:
                seen.add(key)
                uniq_edges.append(e)

        return {"nodes": list(uniq_nodes.values()), "edges": uniq_edges}
    except Exception as e:
        logger.error(f"Error building vis graph for note {note_id}: {e}")
        return {"nodes": [], "edges": []}


def _get_center_node(client, note_id: str):
    cypher = """
    MATCH (n:Note {note_id: $note_id})
    RETURN n.note_id AS id, coalesce(n.title, n.note_id) AS label
    """
    res = client.query(cypher, {"note_id": note_id}) or []
    if not res:
        return None
    record = res[0]
    return {
        "id": record.get("id"),
        "label": record.get("label"),
        "shape": "box",
        "color": {"background": "#6366F1", "border": "#4F46E5"},
        "font": {"color": "#FFFFFF"},
        "size": 30,
        "group": "note",
    }


def _get_topics(client, note_id: str):
    cypher = """
    MATCH (n:Note {note_id: $note_id})-[r:MENTIONS]->(t:Topic)
    RETURN t.id AS id, coalesce(t.name, t.id) AS label, coalesce(r.confidence, 1.0) AS weight
    """
    records = client.query(cypher, {"note_id": note_id}) or []
    nodes = []
    edges = []
    for record in records:
        base_id = record.get("id")
        nodes.append({
            "id": f"topic_{base_id}",
            "label": record.get("label"),
            "shape": "dot",
            "color": {"background": "#10B981", "border": "#059669"},
            "size": 20,
            "group": "topic",
        })
        edges.append({
            "from": note_id,
            "to": f"topic_{base_id}",
            "label": "mentions",
            "arrows": "to",
            "color": "#9CA3AF",
        })
    return nodes, edges


def _get_projects(client, note_id: str):
    cypher = """
    MATCH (n:Note {note_id: $note_id})-[:MENTIONS]->(p:Project)
    RETURN p.id AS id, coalesce(p.name, p.id) AS label, coalesce(p.status, 'unknown') AS status
    """
    records = client.query(cypher, {"note_id": note_id}) or []
    nodes = []
    edges = []
    for record in records:
        status = record.get("status", "unknown")
        color = {
            "active": {"background": "#F59E0B", "border": "#D97706"},
            "paused": {"background": "#6B7280", "border": "#4B5563"},
            "done": {"background": "#10B981", "border": "#059669"},
        }.get(status, {"background": "#F59E0B", "border": "#D97706"})
        base_id = record.get("id")
        nodes.append({
            "id": f"project_{base_id}",
            "label": record.get("label"),
            "shape": "box",
            "color": color,
            "size": 20,
            "group": "project",
        })
        edges.append({
            "from": note_id,
            "to": f"project_{base_id}",
            "label": "project",
            "arrows": "to",
            "color": "#9CA3AF",
            "dashes": True,
        })
    return nodes, edges


def _get_tasks(client, note_id: str):
    cypher = """
    MATCH (n:Note {note_id: $note_id})-[:MENTIONS]->(t:Task)
    RETURN t.id AS id, coalesce(t.title, t.id) AS label, coalesce(t.priority, 'normal') AS priority
    LIMIT 10
    """
    records = client.query(cypher, {"note_id": note_id}) or []
    nodes = []
    edges = []
    for record in records:
        priority = record.get("priority", "normal")
        color = {
            "high": {"background": "#EF4444", "border": "#DC2626"},
            "medium": {"background": "#F59E0B", "border": "#D97706"},
            "low": {"background": "#6B7280", "border": "#4B5563"},
        }.get(priority, {"background": "#6B7280", "border": "#4B5563"})
        base_id = record.get("id")
        nodes.append({
            "id": f"task_{base_id}",
            "label": (record.get("label") or "")[:30],
            "shape": "diamond",
            "color": color,
            "size": 15,
            "group": "task",
        })
        edges.append({
            "from": note_id,
            "to": f"task_{base_id}",
            "label": "task",
            "arrows": "to",
            "color": "#9CA3AF",
        })
    return nodes, edges


def _get_related_notes(client, note_id: str):
    cypher = """
    MATCH (n:Note {note_id: $note_id})-[:MENTIONS]->(t:Topic)<-[:MENTIONS]-(related:Note)
    WHERE n <> related
    WITH related, COUNT(t) AS common
    ORDER BY common DESC
    LIMIT 5
    RETURN related.note_id AS id, coalesce(related.title, related.note_id) AS label
    """
    records = client.query(cypher, {"note_id": note_id}) or []
    nodes = []
    edges = []
    for record in records:
        rid = record.get("id")
        nodes.append({
            "id": rid,
            "label": record.get("label"),
            "shape": "box",
            "color": {"background": "#818CF8", "border": "#6366F1"},
            "size": 20,
            "group": "note",
        })
        edges.append({
            "from": note_id,
            "to": rid,
            "label": "related",
            "arrows": "to",
            "color": "#9CA3AF",
            "dashes": True,
        })
    return nodes, edges


def get_user_graph(user_id: str, vault_id: str = None, limit: int = 100):
    """
    사용자의 전체 그래프 데이터 조회

    Args:
        user_id: 사용자 ID
        vault_id: Vault ID (optional)
        limit: 최대 노드 개수

    Returns:
        {
            "nodes": [...],
            "edges": [...]
        }
    """
    try:
        client = get_neo4j_client()

        # Use EXACT same query as get_all_notes which works
        cypher_notes = """
        MATCH (u:User {id: $user_id})-[:OWNS]->(v:Vault {id: $vault_id})-[:HAS_NOTE]->(n:Note)
        RETURN n.note_id AS note_id, n.title AS title
        ORDER BY n.updated_at DESC
        LIMIT $limit
        """

        params = {
            "user_id": user_id,
            "vault_id": vault_id if vault_id else "obsidian",
            "limit": limit
        }

        note_results = client.query(cypher_notes, params)

        if not note_results:
            logger.warning(f"No notes found")
            return {"nodes": [], "edges": []}

        # Now get the graph for these notes
        note_ids = [r["note_id"] for r in note_results]
        logger.info(f"Found {len(note_ids)} notes, first 5: {note_ids[:5]}")

        # Simpler query: get notes and their direct entities
        cypher_graph = """
        MATCH (n:Note)
        WHERE n.note_id IN $note_ids
        WITH n
        OPTIONAL MATCH (n)-[r:MENTIONS]->(entity)

        WITH n, COLLECT(DISTINCT entity) AS entities, COLLECT(DISTINCT r) AS relationships

        RETURN
            COLLECT(DISTINCT {
                id: n.note_id,
                label: COALESCE(n.title, n.note_id),
                type: 'Note',
                properties: properties(n)
            }) AS noteNodes,

            REDUCE(s = [], entity IN entities |
                CASE WHEN entity IS NOT NULL
                THEN s + [{
                    id: entity.id,
                    label: COALESCE(entity.name, entity.title, entity.id),
                    type: labels(entity)[0],
                    properties: properties(entity)
                }]
                ELSE s END
            ) AS entityNodes,

            REDUCE(s = [], rel IN relationships |
                CASE WHEN rel IS NOT NULL
                THEN s + [{
                    from: startNode(rel).note_id,
                    to: endNode(rel).id,
                    type: type(rel),
                    label: type(rel)
                }]
                ELSE s END
            ) AS edges
        """

        graph_results = client.query(cypher_graph, {"note_ids": note_ids})

        if not graph_results or len(graph_results) == 0:
            logger.warning(f"Graph query returned no results for {len(note_ids)} note_ids")
            return {"nodes": [], "edges": []}

        result = graph_results[0]
        # Combine noteNodes and entityNodes
        note_nodes = result.get("noteNodes", [])
        entity_nodes = result.get("entityNodes", [])
        edges = result.get("edges", [])

        all_nodes = note_nodes + entity_nodes

        logger.info(f"Graph query result: {len(note_nodes)} note nodes, {len(entity_nodes)} entity nodes, {len(edges)} edges")
        if len(all_nodes) == 0:
            logger.warning(f"Graph query returned empty nodes list. Result keys: {result.keys()}")

        return {
            "nodes": all_nodes,
            "edges": edges
        }

    except Exception as e:
        logger.error(f"Error getting user graph: {e}", exc_info=True)
        return {"nodes": [], "edges": []}


def get_entity_graph(entity_type: str = None, limit: int = 50):
    """
    엔티티 중심 그래프 조회

    Args:
        entity_type: 엔티티 타입 (Topic, Project, Task, Person 등)
        limit: 최대 엔티티 개수

    Returns:
        {
            "nodes": [...],
            "edges": [...]
        }
    """
    try:
        client = get_neo4j_client()

        # 엔티티 타입 조건
        entity_match = f"(entity:{entity_type})" if entity_type else "(entity)"

        cypher = f"""
        MATCH {entity_match}
        WITH entity LIMIT $limit
        OPTIONAL MATCH (entity)<-[r:MENTIONS]-(note:Note)
        WITH COLLECT(DISTINCT entity) AS entities, COLLECT(DISTINCT note) AS notes, COLLECT(DISTINCT r) AS rels

        // 노드 변환
        WITH
            [entity IN entities | {{
                id: entity.id,
                label: entity.id,
                type: labels(entity)[0],
                properties: properties(entity)
            }}] +
            [note IN notes WHERE note IS NOT NULL | {{
                id: note.note_id,
                label: note.title,
                type: 'Note',
                properties: properties(note)
            }}] AS allNodes,
            rels

        // 관계 변환
        WITH allNodes,
            [rel IN rels WHERE rel IS NOT NULL | {{
                from: startNode(rel).note_id,
                to: endNode(rel).id,
                type: type(rel),
                label: type(rel)
            }}] AS allEdges

        RETURN allNodes AS nodes, allEdges AS edges
        """

        params = {"limit": limit}
        results = client.query(cypher, params)

        if not results or len(results) == 0:
            logger.warning(f"No graph data found for entity type: {entity_type}")
            return {"nodes": [], "edges": []}

        result = results[0]
        return {
            "nodes": result.get("nodes", []),
            "edges": result.get("edges", [])
        }

    except Exception as e:
        logger.error(f"Error getting entity graph: {e}")
        return {"nodes": [], "edges": []}
