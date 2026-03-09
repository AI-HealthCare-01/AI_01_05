from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.main import app
from app.models.users import User
from app.services.jwt import JwtService


class TestMedicationAPI(TestCase):
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

    async def test_create_prescription(self):
        _, token = await self._make_user_token("med_user_001", "01088880001")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/medications",
                json={
                    "drug_name": "세로토닌정",
                    "dosage": "1정",
                    "frequency": "하루 1회",
                    "start_date": "2026-01-01",
                },
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["drug_name"] == "세로토닌정"

    async def test_get_prescriptions(self):
        _, token = await self._make_user_token("med_user_002", "01088880002")
        headers = {"Authorization": f"Bearer {token}"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post(
                "/api/v1/medications",
                json={"drug_name": "비타민D", "dosage": "1캡슐", "frequency": "하루 1회", "start_date": "2026-01-01"},
                headers=headers,
            )
            response = await client.get("/api/v1/medications", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()["prescriptions"]) >= 1

    async def test_create_medication_log(self):
        _, token = await self._make_user_token("med_user_003", "01088880003")
        headers = {"Authorization": f"Bearer {token}"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            create_res = await client.post(
                "/api/v1/medications",
                json={"drug_name": "오메가3", "dosage": "2캡슐", "frequency": "하루 2회", "start_date": "2026-01-01"},
                headers=headers,
            )
            prescription_id = create_res.json()["prescription_id"]
            response = await client.post(
                f"/api/v1/medications/{prescription_id}/logs",
                json={"log_date": "2026-07-01", "is_taken": True},
                headers=headers,
            )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["is_taken"] is True

    async def test_duplicate_log_returns_409(self):
        """복약 기록 중복 방지 — 같은 날짜 같은 처방 409"""
        _, token = await self._make_user_token("med_user_004", "01088880004")
        headers = {"Authorization": f"Bearer {token}"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            create_res = await client.post(
                "/api/v1/medications",
                json={"drug_name": "마그네슘", "dosage": "1정", "frequency": "하루 1회", "start_date": "2026-01-01"},
                headers=headers,
            )
            prescription_id = create_res.json()["prescription_id"]
            await client.post(
                f"/api/v1/medications/{prescription_id}/logs",
                json={"log_date": "2026-07-02", "is_taken": True},
                headers=headers,
            )
            response = await client.post(
                f"/api/v1/medications/{prescription_id}/logs",
                json={"log_date": "2026-07-02", "is_taken": True},
                headers=headers,
            )
        assert response.status_code == status.HTTP_409_CONFLICT

    async def test_medication_unauthorized(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/medications")
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
