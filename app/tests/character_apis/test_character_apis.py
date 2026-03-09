from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.main import app
from app.models.users import User
from app.services.jwt import JwtService


class TestCharacterAPI(TestCase):
    async def _make_user_token(self, kakao_id: str, phone: str) -> tuple[User, str]:
        user = await User.create(
            kakao_id=kakao_id,
            nickname="테스터",
            phone_number=phone,
            terms_agreed=True,
            privacy_agreed=True,
            sensitive_agreed=True,
        )
        return user, str(JwtService().create_access_token(user))

    async def test_get_characters_list(self):
        """캐릭터 목록 조회 — 4개 반환"""
        _, token = await self._make_user_token("char_user_001", "01055550001")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/characters", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()["characters"]) == 4

    async def test_select_character_success(self):
        """캐릭터 최초 선택 — 201, onboarding_completed True"""
        user, token = await self._make_user_token("char_user_002", "01055550002")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/characters/me",
                json={"character_id": 1},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["character_id"] == 1
        await user.refresh_from_db()
        assert user.onboarding_completed is True

    async def test_select_character_duplicate_returns_409(self):
        """캐릭터 중복 선택 — 409"""
        user, token = await self._make_user_token("char_user_003", "01055550003")
        headers = {"Authorization": f"Bearer {token}"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/api/v1/characters/me", json={"character_id": 1}, headers=headers)
            response = await client.post("/api/v1/characters/me", json={"character_id": 2}, headers=headers)
        assert response.status_code == status.HTTP_409_CONFLICT

    async def test_get_my_character(self):
        """내 캐릭터 조회"""
        user, token = await self._make_user_token("char_user_004", "01055550004")
        headers = {"Authorization": f"Bearer {token}"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/api/v1/characters/me", json={"character_id": 2}, headers=headers)
            response = await client.get("/api/v1/characters/me", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["character_id"] == 2

    async def test_change_character(self):
        """캐릭터 변경 — PATCH"""
        user, token = await self._make_user_token("char_user_005", "01055550005")
        headers = {"Authorization": f"Bearer {token}"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/api/v1/characters/me", json={"character_id": 1}, headers=headers)
            response = await client.patch("/api/v1/characters/me", json={"character_id": 3}, headers=headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["character_id"] == 3

    async def test_unauthenticated_returns_403(self):
        """미인증 요청 — 401/403"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/characters")
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
