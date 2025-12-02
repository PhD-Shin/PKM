"""
Graphiti-based Temporal Knowledge Graph Service

Graphiti (Zep AI)를 활용한 시간 인식 지식 그래프 서비스
- Bi-temporal 모델: valid_at, invalid_at, created_at, expired_at
- 자동 엔티티 해결 및 요약 생성
- 하이브리드 검색 (시맨틱 + BM25 + 그래프 순회)

Reference: https://github.com/getzep/graphiti
Paper: arXiv 2501.13956
"""

import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType

from app.config import settings

logger = logging.getLogger(__name__)


class GraphitiService:
    """
    Graphiti 기반 시간 지식 그래프 서비스

    Features:
    - Episode-based 처리: 노트 수정 → Episode 생성 → 자동 엔티티 추출
    - Bi-temporal 엣지: 모든 관계에 시간 정보 기록
    - 엔티티 요약: 자동 생성 및 업데이트
    - 하이브리드 검색: 시맨틱 + 구조적 검색 결합
    """

    _instance: Optional['GraphitiService'] = None
    _graphiti: Optional[Graphiti] = None

    def __init__(self):
        """GraphitiService 초기화 - 싱글톤 패턴 사용"""
        pass

    @classmethod
    async def get_instance(cls) -> 'GraphitiService':
        """싱글톤 인스턴스 반환"""
        if cls._instance is None:
            cls._instance = cls()
            await cls._instance._initialize()
        return cls._instance

    async def _initialize(self):
        """Graphiti 클라이언트 초기화"""
        try:
            logger.info("Initializing Graphiti client...")

            # Graphiti 클라이언트 생성
            # NOTE: Graphiti는 내부적으로 Neo4j Bolt 드라이버 사용
            self._graphiti = Graphiti(
                uri=settings.neo4j_uri,
                user=settings.neo4j_username,
                password=settings.neo4j_password,
            )

            # 인덱스 및 제약조건 생성
            await self._graphiti.build_indices_and_constraints()

            logger.info("✅ Graphiti client initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Graphiti: {e}")
            raise e

    async def close(self):
        """Graphiti 클라이언트 종료"""
        if self._graphiti:
            await self._graphiti.close()
            self._graphiti = None
            GraphitiService._instance = None
            logger.info("Graphiti client closed")

    async def process_note(
        self,
        note_id: str,
        content: str,
        updated_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        노트를 Graphiti Episode로 처리

        Graphiti의 add_episode를 사용하여:
        1. 엔티티 자동 추출 및 요약 생성
        2. 관계 추출 (fact 포함)
        3. 기존 엔티티와 병합/업데이트
        4. Bi-temporal 시간 정보 기록

        Args:
            note_id: 노트 ID
            content: 노트 내용
            updated_at: 노트 수정 시간 (reference_time으로 사용)
            metadata: 추가 메타데이터 (tags, path 등)

        Returns:
            처리 결과 (추출된 엔티티/관계 수 등)
        """
        if not content or len(content.strip()) < 10:
            logger.info(f"Content too short for {note_id}, skipping")
            return {"status": "skipped", "reason": "content_too_short"}

        try:
            # reference_time: 노트 수정 시간 (지식이 실제로 유효했던 시점)
            reference_time = updated_at or datetime.now()

            # 메타데이터 준비
            meta = metadata or {}
            source_description = f"Obsidian note: {meta.get('path', note_id)}"

            logger.info(f"Processing note via Graphiti: {note_id}")

            # Graphiti Episode 추가
            # - 자동으로 엔티티/관계 추출
            # - 기존 엔티티와 중복 해결
            # - valid_at, created_at 등 시간 정보 기록
            episode_result = await self._graphiti.add_episode(
                name=f"note_{note_id}",
                episode_body=content,
                source_description=source_description,
                reference_time=reference_time,
                source=EpisodeType.text,
            )

            # 결과 파싱
            result = {
                "status": "success",
                "note_id": note_id,
                "episode_id": episode_result.episode.uuid if episode_result.episode else None,
                "nodes_extracted": len(episode_result.nodes) if episode_result.nodes else 0,
                "edges_extracted": len(episode_result.edges) if episode_result.edges else 0,
                "reference_time": reference_time.isoformat(),
            }

            logger.info(f"✅ Graphiti processed {note_id}: "
                       f"{result['nodes_extracted']} nodes, {result['edges_extracted']} edges")

            return result

        except Exception as e:
            logger.error(f"Error processing note {note_id} via Graphiti: {e}")
            return {
                "status": "error",
                "note_id": note_id,
                "error": str(e)
            }

    async def process_notes_bulk(
        self,
        notes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        여러 노트를 일괄 처리

        Args:
            notes: 노트 목록 [{"note_id": str, "content": str, "updated_at": datetime, ...}]

        Returns:
            일괄 처리 결과
        """
        results = {
            "total": len(notes),
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "details": []
        }

        for note in notes:
            result = await self.process_note(
                note_id=note["note_id"],
                content=note["content"],
                updated_at=note.get("updated_at"),
                metadata=note.get("metadata")
            )

            if result["status"] == "success":
                results["success"] += 1
            elif result["status"] == "skipped":
                results["skipped"] += 1
            else:
                results["failed"] += 1

            results["details"].append(result)

        return results

    async def search(
        self,
        query: str,
        num_results: int = 10,
        center_node_uuid: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        하이브리드 검색 (시맨틱 + BM25 + 그래프 순회)

        Args:
            query: 검색 쿼리
            num_results: 반환할 결과 수
            center_node_uuid: 중심 노드 UUID (그래프 순회 시작점)

        Returns:
            검색 결과 (nodes, edges, episodes)
        """
        try:
            logger.info(f"Searching: '{query}' (num_results={num_results})")

            search_result = await self._graphiti.search(
                query=query,
                num_results=num_results,
                center_node_uuid=center_node_uuid
            )

            # 결과 변환
            result = {
                "status": "success",
                "query": query,
                "nodes": [
                    {
                        "uuid": node.uuid,
                        "name": node.name,
                        "summary": getattr(node, 'summary', None),
                        "labels": node.labels if hasattr(node, 'labels') else [],
                        "created_at": node.created_at.isoformat() if hasattr(node, 'created_at') and node.created_at else None,
                    }
                    for node in (search_result.nodes or [])
                ],
                "edges": [
                    {
                        "uuid": edge.uuid,
                        "source_uuid": edge.source_node_uuid,
                        "target_uuid": edge.target_node_uuid,
                        "fact": getattr(edge, 'fact', None),
                        "valid_at": edge.valid_at.isoformat() if hasattr(edge, 'valid_at') and edge.valid_at else None,
                        "invalid_at": edge.invalid_at.isoformat() if hasattr(edge, 'invalid_at') and edge.invalid_at else None,
                        "created_at": edge.created_at.isoformat() if hasattr(edge, 'created_at') and edge.created_at else None,
                    }
                    for edge in (search_result.edges or [])
                ],
            }

            logger.info(f"Search found: {len(result['nodes'])} nodes, {len(result['edges'])} edges")
            return result

        except Exception as e:
            logger.error(f"Search error: {e}")
            return {
                "status": "error",
                "query": query,
                "error": str(e)
            }

    async def get_temporal_evolution(
        self,
        entity_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        엔티티의 시간에 따른 변화 조회

        "2024년 1월에 내가 관심 있었던 주제는?" 같은 쿼리 지원

        Args:
            entity_name: 엔티티 이름
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            시간에 따른 관계 변화 정보
        """
        try:
            # Graphiti 검색 + 시간 필터링
            search_result = await self._graphiti.search(
                query=entity_name,
                num_results=50  # 충분한 결과 확보
            )

            # 시간 범위에 해당하는 엣지 필터링
            filtered_edges = []
            for edge in (search_result.edges or []):
                valid_at = getattr(edge, 'valid_at', None)
                invalid_at = getattr(edge, 'invalid_at', None)

                # 시간 범위 체크
                if start_date and valid_at and valid_at < start_date:
                    continue
                if end_date and invalid_at and invalid_at > end_date:
                    continue

                filtered_edges.append({
                    "uuid": edge.uuid,
                    "fact": getattr(edge, 'fact', None),
                    "valid_at": valid_at.isoformat() if valid_at else None,
                    "invalid_at": invalid_at.isoformat() if invalid_at else None,
                    "is_current": invalid_at is None,
                })

            return {
                "status": "success",
                "entity_name": entity_name,
                "time_range": {
                    "start": start_date.isoformat() if start_date else None,
                    "end": end_date.isoformat() if end_date else None,
                },
                "evolution": filtered_edges,
                "total_changes": len(filtered_edges)
            }

        except Exception as e:
            logger.error(f"Temporal evolution error: {e}")
            return {
                "status": "error",
                "entity_name": entity_name,
                "error": str(e)
            }

    async def invalidate_relationship(
        self,
        note_id: str,
        entity_name: str
    ) -> Dict[str, Any]:
        """
        관계 무효화 (invalid_at 설정)

        노트에서 엔티티 언급이 삭제된 경우, 관계를 무효화합니다.
        실제로 삭제하지 않고 invalid_at을 설정하여 히스토리 보존.

        Args:
            note_id: 노트 ID
            entity_name: 엔티티 이름

        Returns:
            무효화 결과
        """
        # TODO: Graphiti의 remove_episode 또는 직접 Neo4j 쿼리로 구현
        logger.info(f"Invalidating relationship: {note_id} -> {entity_name}")
        return {
            "status": "pending",
            "message": "Relationship invalidation not yet implemented"
        }


# 동기 래퍼 함수들 (기존 API와의 호환성을 위해)

def process_note_to_graph(note_id: str, content: str, metadata: dict = None) -> int:
    """
    동기 래퍼: 기존 ontology_service와 호환되는 인터페이스

    내부적으로 Graphiti의 비동기 처리를 사용합니다.
    """
    async def _async_process():
        service = await GraphitiService.get_instance()
        result = await service.process_note(
            note_id=note_id,
            content=content,
            metadata=metadata
        )
        return result.get("nodes_extracted", 0)

    # 이벤트 루프에서 실행
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 이미 실행 중인 루프가 있으면 새 태스크로 스케줄
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _async_process())
                return future.result()
        else:
            return loop.run_until_complete(_async_process())
    except RuntimeError:
        # 이벤트 루프가 없으면 새로 생성
        return asyncio.run(_async_process())


async def async_process_note(note_id: str, content: str, updated_at: datetime = None, metadata: dict = None) -> Dict[str, Any]:
    """
    비동기 노트 처리 (권장)

    FastAPI 라우터에서 직접 호출 가능
    """
    service = await GraphitiService.get_instance()
    return await service.process_note(
        note_id=note_id,
        content=content,
        updated_at=updated_at,
        metadata=metadata
    )


async def async_search(query: str, num_results: int = 10) -> Dict[str, Any]:
    """
    비동기 검색
    """
    service = await GraphitiService.get_instance()
    return await service.search(query=query, num_results=num_results)


async def async_get_temporal_evolution(entity_name: str, start_date: datetime = None, end_date: datetime = None) -> Dict[str, Any]:
    """
    비동기 시간 변화 조회
    """
    service = await GraphitiService.get_instance()
    return await service.get_temporal_evolution(
        entity_name=entity_name,
        start_date=start_date,
        end_date=end_date
    )
