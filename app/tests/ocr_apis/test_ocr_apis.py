from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.main import app
from app.models.medicine import Medicine
from app.models.users import User
from app.services.jwt import JwtService


class TestOcrParseAPI(TestCase):
    async def _make_token(self, kakao_id: str, phone: str) -> str:
        user = await User.create(
            kakao_id=kakao_id,
            nickname="테스터",
            phone_number=phone,
            terms_agreed=True,
            privacy_agreed=True,
            sensitive_agreed=True,
        )
        return str(JwtService().create_access_token(user))

    def _make_image_file(self) -> bytes:
        return b"\xff\xd8\xff\xe0" + b"\x00" * 100  # minimal JPEG header

    async def test_ocr_parse_prescription_stub_returns_200(self):
        """stub 모드 → 200 + items:[] + raw_text 반환"""
        token = await self._make_token("ocr_001", "01033330001")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/ocr/parse-prescription",
                files={"file": ("test.jpg", self._make_image_file(), "image/jpeg")},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "raw_text" in data
        assert isinstance(data["items"], list)

    async def test_ocr_parse_prescription_unauthorized_returns_401(self):
        """토큰 없음 → 401"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/ocr/parse-prescription",
                files={"file": ("test.jpg", self._make_image_file(), "image/jpeg")},
            )
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    async def test_ocr_parse_prescription_invalid_file_returns_400(self):
        """지원하지 않는 파일 형식 → 400"""
        token = await self._make_token("ocr_003", "01033330003")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/ocr/parse-prescription",
                files={"file": ("test.pdf", b"%PDF-1.4", "application/pdf")},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_ocr_parse_prescription_returns_items_with_inline_pattern(self):
        """인라인 패턴 파싱 검증"""
        from app.services.ocr_service import OcrService
        service = OcrService()
        parsed = service._parse_prescription_text(["렉사프로정 1.0 2 15"])
        assert len(parsed) == 1
        assert parsed[0]["drug_name"] == "렉사프로정"
        assert parsed[0]["dose_per_intake"] == 1.0
        assert parsed[0]["daily_frequency"] == 2
        assert parsed[0]["total_days"] == 15

    async def test_ocr_parse_prescription_returns_items_with_label_pattern(self):
        """레이블 패턴 OCR 텍스트 → items 파싱"""
        from app.services.ocr_service import OcrService
        service = OcrService()
        lines = ["렉사프로정", "1회투약량 1.00", "1일투여횟수 3", "총투약일수 7"]
        parsed = service._parse_prescription_text(lines)
        assert len(parsed) == 1
        assert parsed[0]["dose_per_intake"] == 1.0
        assert parsed[0]["daily_frequency"] == 3
        assert parsed[0]["total_days"] == 7

    async def test_ocr_parse_prescription_matches_medicine_in_db(self):
        """DB에 약품 존재 시 confidence HIGH, item_seq 반환"""
        token = await self._make_token("ocr_006", "01033330006")
        await Medicine.create(
            item_seq="OCR_MED001",
            item_name="렉사프로정10밀리그램",
            search_keyword="렉사프로정",
            is_active=True,
        )
        from app.services.ocr_service import OcrService
        service = OcrService()
        candidates = await service._smart_verify_drug("렉사프로정")
        assert len(candidates) >= 1
        result = service._verify_drug_with_mfds(candidates, "렉사프로정10밀리그램")
        assert result is not None
        assert result["item_seq"] == "OCR_MED001"

    async def test_ocr_parse_prescription_no_match_returns_low_confidence(self):
        """DB 매칭 실패 시 confidence LOW"""
        from app.services.ocr_service import OcrService
        service = OcrService()
        result = service._verify_drug_with_mfds([], "존재하지않는약xyz")
        assert result is None
