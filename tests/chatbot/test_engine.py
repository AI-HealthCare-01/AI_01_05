"""MedicationChatbot 단위 테스트.

Design spec: chat-core.design.md §8.2
시스템 페르소나, 면책 조항, KFDAClient, RAGService 테스트.
"""

import pytest

from app.services.chatbot_service import DISCLAIMER, SYSTEM_PERSONA
from app.services.kfda_service import KFDAClient
from app.services.rag_service import RAGService

# ──────────────────────────────────────────────
# SYSTEM_PERSONA 테스트 (FR-04)
# ──────────────────────────────────────────────


class TestSystemPersona:
    def test_persona_contains_name(self):
        """페르소나에 '도닥이' 이름이 포함되어야 함."""
        assert "도닥이" in SYSTEM_PERSONA

    def test_persona_contains_pharmacist_role(self):
        """페르소나에 약사 역할이 명시되어야 함."""
        assert "약사" in SYSTEM_PERSONA

    def test_persona_prohibits_diagnosis(self):
        """진단/처방 변경 금지 규칙이 포함되어야 함."""
        assert "진단" in SYSTEM_PERSONA
        assert "처방 변경" in SYSTEM_PERSONA

    def test_persona_includes_offlabel(self):
        """오프라벨 처방 설명 가이드가 포함되어야 함."""
        assert "오프라벨" in SYSTEM_PERSONA

    def test_persona_empathy_first(self):
        """공감 우선 규칙이 포함되어야 함."""
        assert "공감" in SYSTEM_PERSONA


# ──────────────────────────────────────────────
# DISCLAIMER 테스트 (FR-05)
# ──────────────────────────────────────────────


class TestDisclaimer:
    def test_disclaimer_contains_warning(self):
        """면책 조항에 참고용 안내가 포함되어야 함."""
        assert "참고용" in DISCLAIMER

    def test_disclaimer_contains_consult(self):
        """면책 조항에 의사/약사 상담 권고가 포함되어야 함."""
        assert "의사" in DISCLAIMER or "약사" in DISCLAIMER

    def test_disclaimer_has_medical_symbol(self):
        """면책 조항에 의료 심볼이 포함되어야 함."""
        assert "⚕️" in DISCLAIMER


# ──────────────────────────────────────────────
# KFDAClient 테스트 (FR-07)
# ──────────────────────────────────────────────


class TestKFDAClient:
    def test_init_without_api_key(self):
        """API 키 없이도 초기화 가능해야 함 (graceful degradation)."""
        import os

        original = os.environ.pop("KFDA_API_KEY", None)
        try:
            client = KFDAClient()
            assert client.api_key is None
        finally:
            if original:
                os.environ["KFDA_API_KEY"] = original

    @pytest.mark.asyncio
    async def test_get_drug_context_without_key(self):
        """API 키 없으면 빈 문자열을 반환해야 함."""
        import os

        original = os.environ.pop("KFDA_API_KEY", None)
        try:
            client = KFDAClient()
            result = await client.get_drug_context(["타이레놀"])
            assert result == ""
        finally:
            if original:
                os.environ["KFDA_API_KEY"] = original

    @pytest.mark.asyncio
    async def test_get_drug_context_empty_list(self):
        """빈 약물 리스트에 대해 빈 문자열을 반환해야 함."""
        client = KFDAClient()
        result = await client.get_drug_context([])
        assert result == ""


# ──────────────────────────────────────────────
# RAGService 테스트 (FR-08)
# ──────────────────────────────────────────────


class TestRAGService:
    @pytest.mark.asyncio
    async def test_search_returns_list(self):
        """검색 결과는 항상 리스트여야 함 (비활성 시에도)."""
        rag = RAGService()
        result = await rag.search("혈압약 부작용")
        assert isinstance(result, list)

    def test_ingest_unavailable_returns_zero(self):
        """비활성 상태에서 ingest는 0을 반환해야 함."""
        rag = RAGService()
        if not rag.available:
            result = rag.ingest_pdf("nonexistent.pdf")
            assert result == 0
