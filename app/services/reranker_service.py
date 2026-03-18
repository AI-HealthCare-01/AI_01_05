"""Cross-Encoder Re-ranking 서비스.

Vector Search 결과를 Cross-Encoder 모델로 재점수화하여 정확도 향상.
원본 질문과 각 후보 청크 간 관련도를 직접 계산.

Pipeline:
Vector Search Top-20 → Cross-Encoder Re-score → Top-5 반환
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentence_transformers import CrossEncoder

logger = logging.getLogger("dodaktalk.reranker")

# Cross-Encoder 모델 (다국어 지원, 빠른 추론)
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class RerankerService:
    """Cross-Encoder 기반 Re-ranking 서비스."""

    def __init__(self) -> None:
        self._available = False
        self._model: CrossEncoder | None = None

        try:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(RERANKER_MODEL)
            self._available = True
            logger.info("Reranker 서비스 초기화 완료 (model=%s)", RERANKER_MODEL)
        except ImportError:
            logger.warning("sentence-transformers 미설치. Reranker 비활성화.")
        except Exception as e:
            logger.warning("Reranker 모델 로드 실패: %s", e)

    @property
    def available(self) -> bool:
        return self._available

    def _rerank_sync(
        self,
        query: str,
        candidates: list[str],
        top_k: int = 5,
    ) -> list[dict]:
        """동기 방식 재정렬 (내부용).

        Args:
            query: 원본 사용자 질문
            candidates: 벡터 검색 결과 청크 목록
            top_k: 반환할 상위 결과 수

        Returns:
            재정렬된 결과 리스트 [{"text": str, "score": float}, ...]
        """
        if not self._available or not self._model or not candidates:
            # Fallback: 원본 순서 유지
            return [{"text": c, "score": 1.0 - i * 0.1} for i, c in enumerate(candidates[:top_k])]

        try:
            # Cross-Encoder는 (query, candidate) 쌍의 관련도 점수 계산
            pairs = [(query, candidate) for candidate in candidates]
            scores = self._model.predict(pairs)

            # 점수와 텍스트를 묶어서 정렬
            scored_results = [
                {"text": candidate, "score": float(score)} for candidate, score in zip(candidates, scores, strict=True)
            ]
            scored_results.sort(key=lambda x: x["score"], reverse=True)

            return scored_results[:top_k]
        except Exception as e:
            logger.warning("Re-ranking 실패: %s. 원본 순서 반환.", e)
            return [{"text": c, "score": 1.0 - i * 0.1} for i, c in enumerate(candidates[:top_k])]

    async def rerank(
        self,
        query: str,
        candidates: list[str],
        top_k: int = 5,
    ) -> list[str]:
        """비동기 재정렬 - 원본 질문 기준으로 후보 청크 재정렬.

        Args:
            query: 원본 사용자 질문
            candidates: 벡터 검색 결과 청크 목록 (Top-20 권장)
            top_k: 반환할 상위 결과 수

        Returns:
            재정렬된 텍스트 리스트 (top_k개)
        """
        if not candidates:
            return []

        # 동기 모델을 비동기로 래핑
        results = await asyncio.to_thread(self._rerank_sync, query, candidates, top_k)

        logger.debug(
            "Re-ranking 완료: %d → %d (top score=%.3f)",
            len(candidates),
            len(results),
            results[0]["score"] if results else 0,
        )

        return [r["text"] for r in results]

    async def rerank_with_scores(
        self,
        query: str,
        candidates: list[str],
        top_k: int = 5,
    ) -> list[dict]:
        """비동기 재정렬 - 점수 포함 반환.

        Returns:
            [{"text": str, "score": float}, ...]
        """
        if not candidates:
            return []

        return await asyncio.to_thread(self._rerank_sync, query, candidates, top_k)


# ── 싱글턴 인스턴스 ───────────────────────────────────────────
_reranker_service: RerankerService | None = None


def get_reranker_service() -> RerankerService:
    """Reranker 서비스 싱글턴 반환."""
    global _reranker_service
    if _reranker_service is None:
        _reranker_service = RerankerService()
    return _reranker_service
