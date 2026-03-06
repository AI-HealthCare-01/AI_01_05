from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.main import app
from app.models.users import User
from app.services.jwt import JwtService


class TestAppointmentAPI(TestCase):
    async def _make_user_token(self, kakao_id: str, phone: str) -> tuple[User, str]:
        user = await User.create(
            kakao_id=kakao_id, nickname="테스터", phone_number=phone,
            terms_agreed=True, privacy_agreed=True, sensitive_agreed=True,
        )
        return user, str(JwtService().create_access_token(user))

    async def test_create_appointment(self):
        _, token = await self._make_user_token("appt_user_001", "01077770001")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/appointments",
                json={"appointment_date": "2026-08-01", "hospital_name": "서울정신건강의학과", "notes": "첫 방문"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["hospital_name"] == "서울정신건강의학과"

    async def test_get_appointments(self):
        _, token = await self._make_user_token("appt_user_002", "01077770002")
        headers = {"Authorization": f"Bearer {token}"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post(
                "/api/v1/appointments",
                json={"appointment_date": "2026-08-10", "hospital_name": "강남병원"},
                headers=headers,
            )
            response = await client.get("/api/v1/appointments", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()["appointments"]) >= 1

    async def test_patch_appointment(self):
        _, token = await self._make_user_token("appt_user_003", "01077770003")
        headers = {"Authorization": f"Bearer {token}"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            create_res = await client.post(
                "/api/v1/appointments",
                json={"appointment_date": "2026-09-01", "hospital_name": "원래병원"},
                headers=headers,
            )
            appt_id = create_res.json()["appointment_id"]
            response = await client.patch(
                f"/api/v1/appointments/{appt_id}",
                json={"hospital_name": "바뀐병원"},
                headers=headers,
            )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["hospital_name"] == "바뀐병원"

    async def test_delete_appointment(self):
        _, token = await self._make_user_token("appt_user_004", "01077770004")
        headers = {"Authorization": f"Bearer {token}"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            create_res = await client.post(
                "/api/v1/appointments",
                json={"appointment_date": "2026-10-01", "hospital_name": "삭제병원"},
                headers=headers,
            )
            appt_id = create_res.json()["appointment_id"]
            response = await client.delete(f"/api/v1/appointments/{appt_id}", headers=headers)
        assert response.status_code == status.HTTP_204_NO_CONTENT

    async def test_appointment_unauthorized(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/appointments")
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
