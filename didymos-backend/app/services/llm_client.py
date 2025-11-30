"""
경량 LLM/요약 유틸
"""
import logging
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
    """
    if not content:
        return ""
    if client is None:
        return content[:200]
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Summarize the following note in 2-3 sentences. Focus on key concepts and topics only.",
                },
                {"role": "user", "content": content[:1000]},
            ],
            temperature=0.3,
            max_tokens=150,
        )
        summary = response.choices[0].message.content
        logger.info(f"Content summarized: {len(content)} -> {len(summary)} chars")
        return summary
    except Exception as e:
        logger.error(f"Summarization error: {e}")
        return content[:200]
