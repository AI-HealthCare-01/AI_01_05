"""HyDE (Hypothetical Document Embeddings) 서비스.

사용자 질문을 GPT로 가설 답변 생성 후 임베딩하여 검색 정확도 향상.
원본 질문보다 실제 문서와 유사한 가설 답변으로 벡터 검색 품질 개선.

Pipeline:
Query → GPT 가설 답변 생성 → 가설 답변 임베딩 → Vector Search
"""

from __future__ import annotations

import logging
import os

from openai import AsyncOpenAI

logger = logging.getLogger("dodaktalk.hyde")

HYDE_SYSTEM_PROMPT = """당신은 의약품 전문가입니다.
사용자 질문에 대해 전문적인 답변을 2-3문장으로 작성하세요.
답변은 임베딩 검색에 사용될 것이므로 핵심 키워드를 포함하세요.

예시:
- 질문: "졸피뎀 부작용이 뭐야?"
- 답변: "졸피뎀은 비벤조디아제핀계 수면제로, 주요 부작용으로 어지러움, 기억력 저하, 의존성, 다음날 졸음, 낙상 위험이 있습니다. 특히 노인에서 낙상 및 인지기능 저하 위험이 증가합니다."

- 질문: "발프로산 임신 중 먹어도 돼?"
- 답변: "발프로산은 임부금기 1등급 약물로, 임신 중 복용 시 태아 신경관 결손, 기형 위험이 현저히 증가합니다. 임신 계획 시 반드시 대체 약물로 전환해야 합니다."

답변만 작성하세요. 추가 설명이나 질문은 하지 마세요."""


class HyDEService:
    """HyDE (Hypothetical Document Embeddings) 서비스."""

    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY 미설정. HyDE 비활성화.")
            self._available = False
            return

        self._client = AsyncOpenAI(api_key=api_key)
        self._model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self._available = True
        logger.info("HyDE 서비스 초기화 완료 (model=%s)", self._model)

    @property
    def available(self) -> bool:
        return self._available

    async def generate_hypothesis(self, query: str) -> str:
        """사용자 질문에 대한 가설 답변을 생성합니다.

        Args:
            query: 사용자 질문

        Returns:
            가설 답변 문자열. 실패 시 원본 질문 반환.
        """
        if not self._available:
            logger.debug("HyDE 비활성 상태. 원본 질문 반환.")
            return query

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": HYDE_SYSTEM_PROMPT},
                    {"role": "user", "content": query},
                ],
                temperature=0.3,
                max_tokens=200,
            )
            hypothesis = response.choices[0].message.content
            if hypothesis:
                logger.debug("HyDE 가설 생성 완료: %s...", hypothesis[:50])
                return hypothesis.strip()
            return query
        except Exception as e:
            logger.warning("HyDE 가설 생성 실패: %s. 원본 질문으로 fallback.", e)
            return query


# ── 싱글턴 인스턴스 ───────────────────────────────────────────
_hyde_service: HyDEService | None = None


def get_hyde_service() -> HyDEService:
    """HyDE 서비스 싱글턴 반환."""
    global _hyde_service
    if _hyde_service is None:
        _hyde_service = HyDEService()
    return _hyde_service
