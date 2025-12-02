"""
Knowledge Graph Clustering Schemas
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class HubEntity(BaseModel):
    """클러스터 허브 엔티티 (그래프 중심성 기반)"""
    id: str
    name: str
    centrality: float = Field(..., ge=0.0, le=1.0, description="중심성 점수 (0~1)")


class ClusterNode(BaseModel):
    """클러스터 노드"""
    id: str
    name: str
    level: int = Field(..., description="1=메타, 2=서브, 3=리프")
    node_count: int = Field(..., description="포함된 노드 수")
    summary: Optional[str] = Field(None, description="LLM 생성 요약")
    key_insights: List[str] = Field(default_factory=list, description="핵심 인사이트")
    sample_entities: List[str] = Field(default_factory=list, description="샘플 엔티티 이름")
    sample_notes: List[str] = Field(default_factory=list, description="샘플 노트 제목")
    note_ids: List[str] = Field(default_factory=list, description="클러스터에 포함된 노트 ID 샘플")
    entity_ids: List[str] = Field(default_factory=list, description="클러스터에 포함된 엔티티 ID")
    importance_score: float = Field(0.0, ge=0.0, le=10.0)
    recent_updates: int = Field(0, description="최근 7일 내 업데이트된 노트 수")
    last_updated: str
    last_computed: str
    clustering_method: str = Field("auto", description="auto, manual, hybrid")
    is_manual: bool = False
    contains_types: Dict[str, int] = Field(
        default_factory=dict,
        description="포함된 노드 타입별 카운트 (note: 10, topic: 3, ...)"
    )
    hub_entities: List[HubEntity] = Field(
        default_factory=list,
        description="그래프 중심성 기반 허브 엔티티 (클러스터의 핵심 개념)"
    )


class ClusterEdge(BaseModel):
    """클러스터 간 관계"""
    from_: str = Field(..., alias="from")
    to: str
    relation_type: str = Field(..., description="SUB_CLUSTER, RELATED_TO")
    weight: float = Field(1.0, description="관계 강도")

    class Config:
        populate_by_name = True


class ClusteredGraphResponse(BaseModel):
    """클러스터링된 그래프 응답"""
    status: str = "success"
    level: int = Field(..., description="현재 클러스터 레벨")
    cluster_count: int
    total_nodes: int = Field(..., description="원본 노드 총 개수")
    clusters: List[ClusterNode]
    edges: List[ClusterEdge]
    last_computed: str
    computation_method: str = Field(..., description="louvain, leiden, manual, hybrid")


class ClusterComputeRequest(BaseModel):
    """클러스터 재계산 요청"""
    vault_id: str
    method: str = Field("auto", description="auto, louvain, leiden")
    force_recompute: bool = Field(False, description="캐시 무시하고 재계산")
    target_clusters: int = Field(10, ge=3, le=50, description="목표 클러스터 개수")
    include_llm_summary: bool = Field(True, description="LLM 요약 생성 여부")


class ClusterUpdateRequest(BaseModel):
    """수동 클러스터 수정 요청"""
    cluster_id: str
    name: Optional[str] = None
    move_nodes: Optional[List[str]] = Field(None, description="다른 클러스터로 이동할 노드 ID 리스트")
    target_cluster_id: Optional[str] = Field(None, description="이동 대상 클러스터")
    merge_with: Optional[str] = Field(None, description="병합할 클러스터 ID")
