from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.main import app
from app.models.users import User
from app.services.jwt import JwtService


class TestMoodAPI(TestCase):
    async def _make_user_token(self, kakao_id: str, phone: str) -> tuple[User, str]:
        user = await User.create(
            kakao_id=kakao_id, nickname="테스터", phone_number=phone,
            terms_agreed=True, privacy_agreed=True, sensitive_agreed=True,
        )
        return user, str(JwtService().create_access_token(user))

    async def test_create_mood(self):
        _, token = await self._make_user_token("mood_user_001", "01066660001")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/moods",
                json={"mood_score": 4, "note": "오늘은 좋았어요"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["mood_score"] == 4

    async def test_get_moods_by_date(self):
        _, token = await self._make_user_token("mood_user_002", "01066660002")
        headers = {"Authorization": f"Bearer {token}"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/api/v1/moods", json={"mood_score": 3, "note": "보통"}, headers=headers)
            response = await client.get("/api/v1/moods", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()["moods"]) >= 1

    async def test_patch_mood(self):
        _, token = await self._make_user_token("mood_user_003", "01066660003")
        headers = {"Authorization": f"Bearer {token}"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            create_res = await client.post("/api/v1/moods", json={"mood_score": 2}, headers=headers)
            mood_id = create_res.json()["mood_id"]
            response = await client.patch(
                f"/api/v1/moods/{mood_id}",
                json={"mood_score": 5},
                headers=headers,
            )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["mood_score"] == 5

    async def test_mood_unauthorized(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/moods", json={"mood_score": 3})
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
