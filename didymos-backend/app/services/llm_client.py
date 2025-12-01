"""
LLM 클라이언트: 노트 요약 & 클러스터 인사이트 생성
Phase 11: GPT-5 Mini를 사용한 클러스터 요약
"""
import logging
import json
from typing import Dict, List, Any
from app.config import settings

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
except Exception as e:
    client = None
    logger.error(f"OpenAI client init failed: {e}")


def summarize_content(content: str) -> str:
    """
    프라이버시 모드용 노트 요약 (2-3문장)
    Model: gpt-5-mini
    """
    if not content:
        return ""
    if client is None:
        return content[:200]
    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Summarize the following note in 2-3 sentences. Focus on key concepts and topics only.",
                },
                {"role": "user", "content": content[:1000]},
            ],
        )
        summary = response.choices[0].message.content
        logger.info(f"Content summarized: {len(content)} -> {len(summary)} chars")
        return summary
    except Exception as e:
        logger.error(f"Summarization error: {e}")
        return content[:200]


def generate_cluster_summary(cluster_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    클러스터 요약 및 인사이트 생성 (Phase 11)
    Model: gpt-5-mini (고품질 추론)

    Args:
        cluster_data: 클러스터 정보
            - id: 클러스터 ID
            - name: 클러스터 이름
            - node_count: 노드 개수
            - contains_types: 포함된 노드 타입 (예: {"topic": 80, "note": 65})
            - sample_entities: 샘플 엔티티 이름들 (최대 10개)
            - recent_updates: 최근 7일 업데이트 수

    Returns:
        {
            "summary": "2-3문장 요약",
            "key_insights": ["인사이트1", "인사이트2", "인사이트3"],
            "next_actions": ["액션1", "액션2"]
        }
    """
    if client is None:
        logger.warning("OpenAI client not available, returning placeholder")
        return {
            "summary": f"이 클러스터는 {cluster_data.get('node_count', 0)}개의 노드로 구성되어 있습니다.",
            "key_insights": [
                "OpenAI API 연결이 필요합니다.",
                "환경 변수를 확인하세요.",
                "Placeholder 인사이트입니다."
            ],
            "next_actions": [
                "OpenAI API 설정을 완료하세요."
            ]
        }

    try:
        # 프롬프트 구성
        recent_updates = cluster_data.get('recent_updates', 0)
        sample_notes = cluster_data.get('sample_notes', [])

        cluster_info = f"""
클러스터 정보:
- 이름: {cluster_data.get('name', 'Unknown')}
- 노드 수: {cluster_data.get('node_count', 0)}개
- 구성: {cluster_data.get('contains_types', {})}
- 샘플 엔티티: {', '.join(cluster_data.get('sample_entities', [])[:10])}
- 최근 7일 업데이트: {recent_updates}개
- 샘플 노트: {', '.join(sample_notes[:5])}
"""

        system_prompt = """당신은 지식 관리 및 의사결정 지원 전문가입니다.
사용자의 지식 베이스에서 발견된 클러스터를 분석하여, 사용자가 이 클러스터에서 주목해야 할 점과 다음 행동을 명확하게 제안해야 합니다.

응답 형식 (JSON):
{
  "summary": "이 클러스터의 핵심 주제를 2-3문장으로 요약",
  "key_insights": [
    "사용자가 주목해야 할 인사이트 1 (데이터 기반)",
    "사용자가 주목해야 할 인사이트 2 (패턴 발견)",
    "사용자가 주목해야 할 인사이트 3 (잠재적 기회)"
  ],
  "next_actions": [
    "구체적이고 실행 가능한 다음 행동 1",
    "구체적이고 실행 가능한 다음 행동 2"
  ]
}

요구사항:
- summary는 구체적이고 실용적으로 작성
- key_insights는 데이터 기반의 통찰을 제공 (예: "최근 업데이트가 많아 활발한 작업 영역입니다")
- next_actions는 즉시 실행 가능한 구체적 행동 제안 (예: "관련 노트들을 하나의 프로젝트로 통합하세요")
- 한국어로 작성"""

        response = client.chat.completions.create(
            model="gpt-5-mini",  # Phase 11: GPT-5 Mini
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": cluster_info}
            ],
            response_format={"type": "json_object"}  # JSON 모드
        )

        result = json.loads(response.choices[0].message.content)

        # 토큰 사용량 로깅
        usage = response.usage
        cost = (usage.prompt_tokens * 0.00015 + usage.completion_tokens * 0.0006) / 1000
        logger.info(f"Cluster summary generated: {usage.prompt_tokens} in, "
                   f"{usage.completion_tokens} out, cost: ${cost:.4f}")

        return {
            "summary": result.get("summary", "요약 생성 실패"),
            "key_insights": result.get("key_insights", [
                "인사이트 생성 실패",
                "응답 형식을 확인하세요.",
                "다시 시도해주세요."
            ]),
            "next_actions": result.get("next_actions", [
                "다시 시도해주세요."
            ])
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse GPT-5 response as JSON: {e}")
        return {
            "summary": f"클러스터 '{cluster_data.get('name')}'는 {cluster_data.get('node_count')}개의 노드로 구성되어 있습니다.",
            "key_insights": ["JSON 파싱 오류", "다시 시도하세요."]
        }

    except Exception as e:
        logger.error(f"Cluster summary generation error: {e}")
        return {
            "summary": f"이 클러스터는 {cluster_data.get('node_count', 0)}개의 노드로 구성되어 있습니다.",
            "key_insights": [
                "요약 생성 중 오류 발생",
                str(e)[:100],
                "나중에 다시 시도하세요."
            ]
        }


def generate_batch_cluster_summaries(clusters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    여러 클러스터에 대해 일괄 요약 생성 (병렬 처리)

    Args:
        clusters: 클러스터 리스트

    Returns:
        요약이 추가된 클러스터 리스트
    """
    if not clusters:
        return clusters

    logger.info(f"Generating summaries for {len(clusters)} clusters (parallel batch)...")

    # 병렬 처리를 위해 asyncio 사용하지 않고 ThreadPoolExecutor 사용
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import time

    start_time = time.time()

    def process_cluster(idx_cluster):
        idx, cluster = idx_cluster
        try:
            logger.info(f"Processing cluster {idx+1}/{len(clusters)}: {cluster.get('name')}")
            result = generate_cluster_summary(cluster)
            cluster["summary"] = result["summary"]
            cluster["key_insights"] = result["key_insights"]
            cluster["next_actions"] = result.get("next_actions", [])
            return cluster, None
        except Exception as e:
            logger.error(f"Failed to generate summary for cluster {cluster.get('id')}: {e}")
            cluster["summary"] = f"요약 생성 실패: {str(e)[:100]}"
            cluster["key_insights"] = ["요약 생성 실패"]
            cluster["next_actions"] = []
            return cluster, str(e)

    # 최대 3개씩 병렬 처리 (OpenAI API rate limit 고려)
    max_workers = min(3, len(clusters))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_cluster, (i, cluster)): i
                  for i, cluster in enumerate(clusters)}

        completed = 0
        for future in as_completed(futures):
            completed += 1
            cluster, error = future.result()
            if error:
                logger.warning(f"Cluster processing had error: {error}")

    elapsed = time.time() - start_time
    logger.info(f"✅ Batch summary generation completed for {len(clusters)} clusters in {elapsed:.2f}s")
    return clusters
