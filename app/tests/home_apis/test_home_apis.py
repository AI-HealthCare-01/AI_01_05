from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.main import app
from app.models.users import User
from app.services.jwt import JwtService


class TestHomeAPI(TestCase):
    async def _make_user_token(self, kakao_id: str, phone: str) -> tuple[User, str]:
        user = await User.create(
            kakao_id=kakao_id,
            nickname="홈테스터",
            phone_number=phone,
            terms_agreed=True,
            privacy_agreed=True,
            sensitive_agreed=True,
        )
        return user, str(JwtService().create_access_token(user))

    async def test_home_summary_returns_200(self):
        """홈 요약 API — 기본 구조 반환"""
        _, token = await self._make_user_token("home_user_001", "01099990001")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/home/summary?date=2026-07-01",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "user" in data
        assert "today_mood" in data
        assert "today_diary" in data
        assert "upcoming_appointment" in data
        assert "today_medications" in data

    async def test_home_summary_unauthorized(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/home/summary?date=2026-07-01")
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
