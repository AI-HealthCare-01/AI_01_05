from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.main import app
from app.models.medicine import Medicine
from app.models.users import User
from app.services.jwt import JwtService


class TestUserMedicationAPI(TestCase):
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

    async def _make_medicine(self, item_seq: str = "MED001") -> Medicine:
        return await Medicine.create(
            item_seq=item_seq,
            item_name="테스트정10mg",
            search_keyword="테스트정",
        )

    async def test_create_user_medication_returns_201(self):
        _, token = await self._make_user_token("um_001", "01022220001")
        await self._make_medicine("UM_MED001")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/user-medications",
                json={
                    "item_seq": "UM_MED001",
                    "dose_per_intake": 1.0,
                    "daily_frequency": 2,
                    "total_days": 14,
                    "start_date": "2026-01-01",
                    "time_slots": ["MORNING", "EVENING"],
                },
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "medication_id" in data
        assert data["item_seq"] == "UM_MED001"
        assert data["status"] == "ACTIVE"

    async def test_create_with_invalid_item_seq_returns_404(self):
        _, token = await self._make_user_token("um_002", "01022220002")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/user-medications",
                json={
                    "item_seq": "NOTEXIST_SEQ",
                    "dose_per_intake": 1.0,
                    "daily_frequency": 1,
                    "total_days": 7,
                    "start_date": "2026-01-01",
                    "time_slots": ["MORNING"],
                },
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_create_missing_required_field_returns_422(self):
        _, token = await self._make_user_token("um_003", "01022220003")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/user-medications",
                json={"dose_per_intake": 1.0},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_create_unauthorized_returns_401(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/user-medications", json={})
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    async def test_list_active_medications_returns_200(self):
        _, token = await self._make_user_token("um_004", "01022220004")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/user-medications",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)
