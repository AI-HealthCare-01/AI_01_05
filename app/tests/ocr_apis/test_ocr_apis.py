import io
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.main import app
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
