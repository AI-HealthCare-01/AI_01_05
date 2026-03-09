from io import BytesIO

from httpx import ASGITransport, AsyncClient
from starlette import status

from app.core import memory_db
from app.main import app
from app.models.users import Gender, User
from app.services.jwt import JwtService


def _reset_memory() -> None:
    memory_db.fake_diary_entries.clear()
    memory_db.fake_report_db.clear()
    memory_db.fake_ocr_pending.clear()
    memory_db.fake_chatbot_pending.clear()
    memory_db.diary_entry_sequence = 1
    memory_db.report_sequence = 1

    async def _get_auth_headers(self) -> dict[str, str]:
        user = await User.create(
            kakao_id="diary_test_kakao",
            nickname="다이어리테스터",
            phone_number="01044445555",
            gender=Gender.UNKNOWN,
            terms_agreed=True,
            privacy_agreed=True,
            sensitive_agreed=True,
        )
        tokens = JwtService().issue_jwt_pair(user)
        return {"Authorization": f"Bearer {tokens['access_token']}"}

    async def test_diary_unauthorized(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/diary/calendar?year=2026&month=2")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_create_and_get_diary_by_date(self):
        self._reset_memory()
        headers = await self._get_auth_headers()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            create_response = await client.post(
                "/api/v1/diary/2026-02-27/text",
                json={"title": "테스트 제목", "content": "테스트 내용"},
                headers=headers,
            )
            get_response = await client.get("/api/v1/diary/2026-02-27", headers=headers)

        assert create_response.status_code == status.HTTP_201_CREATED
        assert create_response.json()["entryId"] == 1
        assert get_response.status_code == status.HTTP_200_OK
        assert get_response.json()["entries"][0]["title"] == "테스트 제목"

    async def test_ocr_upload_and_confirm(self):
        self._reset_memory()
        headers = await self._get_auth_headers()
        files = {"image": ("handwriting.png", BytesIO(b"png-binary-data"), "image/png")}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            upload_response = await client.post("/api/v1/diary/2026-02-27/photo/ocr", files=files, headers=headers)
            entry_id = upload_response.json()["entryId"]
            confirm_response = await client.post(
                "/api/v1/diary/2026-02-27/photo/ocr/confirm",
                json={"entryId": entry_id, "title": "OCR 제목", "content": "OCR 내용"},
                headers=headers,
            )

        assert upload_response.status_code == status.HTTP_200_OK
        assert "extractedText" in upload_response.json()
        assert confirm_response.status_code == status.HTTP_201_CREATED
        assert confirm_response.json()["message"] == "일기가 저장되었습니다."

    async def test_report_crud_flow(self):
        self._reset_memory()
        headers = await self._get_auth_headers()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            create_response = await client.post(
                "/api/v1/diary/report",
                json={"startDate": "2026-02-19", "endDate": "2026-02-26"},
                headers=headers,
            )
            report_id = create_response.json()["reportId"]
            list_response = await client.get("/api/v1/diary/report", headers=headers)
            detail_response = await client.get(f"/api/v1/diary/report/{report_id}", headers=headers)
            update_response = await client.put(
                f"/api/v1/diary/report/{report_id}",
                json={"summary": "수정된 리포트 내용"},
                headers=headers,
            )

        assert create_response.status_code == status.HTTP_201_CREATED
        assert list_response.status_code == status.HTTP_200_OK
        assert detail_response.status_code == status.HTTP_200_OK
        assert update_response.status_code == status.HTTP_200_OK
