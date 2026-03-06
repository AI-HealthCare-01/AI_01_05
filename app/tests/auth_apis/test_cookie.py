from unittest.mock import AsyncMock, MagicMock, patch

from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.main import app
from app.models.users import Gender, User

KAKAO_ID = "cookie_test_kakao_001"
PATCH_TARGET = "app.services.auth.httpx.AsyncClient"


class TestRefreshTokenCookie(TestCase):
    async def test_cookie_has_no_domain_localhost(self):
        """refresh_token 쿠키에 domain=localhost가 설정되지 않아야 한다."""
        user = await User.create(
            kakao_id=KAKAO_ID,
            nickname="쿠키테스터",
            phone_number="01033334444",
            gender=Gender.UNKNOWN,
            terms_agreed=True,
            privacy_agreed=True,
            sensitive_agreed=True,
        )

        token_resp = AsyncMock()
        token_resp.raise_for_status = MagicMock()
        token_resp.json = MagicMock(return_value={"access_token": "fake_kakao_token"})

        user_resp = AsyncMock()
        user_resp.raise_for_status = MagicMock()
        user_resp.json = MagicMock(
            return_value={
                "id": KAKAO_ID,
                "kakao_account": {"profile": {"nickname": "쿠키테스터"}},
            }
        )

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=token_resp)
        mock_client.get = AsyncMock(return_value=user_resp)

        with patch(PATCH_TARGET, return_value=mock_client):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/v1/auth/kakao", json={"code": "valid_code"})

        assert response.status_code == status.HTTP_200_OK
        set_cookie = response.headers.get("set-cookie", "").lower()
        assert "domain=localhost" not in set_cookie
        assert "samesite=lax" in set_cookie

        await user.delete()
