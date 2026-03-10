from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.main import app
from app.models.medicine import Medicine
from app.models.users import User
from app.services.jwt import JwtService


class TestMedicineSearchAPI(TestCase):
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

    async def test_search_returns_empty_list_for_unknown_keyword(self):
        token = await self._make_token("med_s_001", "01011110001")
        with patch("app.services.medicine_service.MfdsClient.search", new_callable=AsyncMock, return_value=[]):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get(
                    "/api/v1/medicines/search?keyword=존재하지않는약xyz",
                    headers={"Authorization": f"Bearer {token}"},
                )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    async def test_search_returns_200_with_db_results(self):
        token = await self._make_token("med_s_002", "01011110002")
        await Medicine.create(
            item_seq="TEST001",
            item_name="테스트정10mg",
            search_keyword="테스트정",
        )
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/medicines/search?keyword=테스트정",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 1
        assert data[0]["item_seq"] == "TEST001"

    async def test_search_missing_keyword_returns_400(self):
        token = await self._make_token("med_s_003", "01011110003")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/medicines/search",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_search_unauthorized_returns_401(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/medicines/search?keyword=타이레놀")
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    async def test_get_detail_returns_200(self):
        token = await self._make_token("med_s_004", "01011110004")
        await Medicine.create(item_seq="DETAIL001", item_name="상세조회정", search_keyword="상세조회정")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/medicines/DETAIL001",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["item_seq"] == "DETAIL001"

    async def test_get_detail_unknown_returns_404(self):
        token = await self._make_token("med_s_005", "01011110005")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/medicines/NOTEXIST999",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_search_caches_result_on_second_call(self):
        """DB 캐시 히트 시 외부 API 미호출 검증"""
        token = await self._make_token("med_s_006", "01011110006")
        await Medicine.create(item_seq="CACHE001", item_name="캐시테스트정", search_keyword="캐시테스트정")
        with patch("app.services.medicine_service.MfdsClient.search", new_callable=AsyncMock) as mock_api:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                await client.get(
                    "/api/v1/medicines/search?keyword=캐시테스트정",
                    headers={"Authorization": f"Bearer {token}"},
                )
                await client.get(
                    "/api/v1/medicines/search?keyword=캐시테스트정",
                    headers={"Authorization": f"Bearer {token}"},
                )
        mock_api.assert_not_called()
