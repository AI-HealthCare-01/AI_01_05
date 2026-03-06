import httpx
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.main import app

KAKAO_ID = "test_kakao_123"
NICKNAME = "테스터"
PATCH_TARGET = "app.services.auth.httpx.AsyncClient"


def _make_kakao_mock(kakao_id: str = KAKAO_ID, nickname: str = NICKNAME):
    token_resp = AsyncMock()
    token_resp.raise_for_status = MagicMock()
    token_resp.json = MagicMock(return_value={"access_token": "fake_kakao_token"})

    user_resp = AsyncMock()
    user_resp.raise_for_status = MagicMock()
    user_resp.json = MagicMock(return_value={
        "id": kakao_id,
        "kakao_account": {"profile": {"nickname": nickname}},
    })

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=token_resp)
    mock_client.get = AsyncMock(return_value=user_resp)
    return mock_client


class TestKakaoLoginAPI(TestCase):
    async def test_existing_user_returns_access_token(self):
        """기존 회원 카카오 로그인 시 access_token과 refresh_token 쿠키를 반환한다."""
        from app.models.users import Gender, User

        user = await User.create(
            kakao_id=KAKAO_ID,
            nickname=NICKNAME,
            phone_number="01011112222",
            gender=Gender.UNKNOWN,
            terms_agreed=True,
            privacy_agreed=True,
            sensitive_agreed=True,
        )

        with patch(PATCH_TARGET, return_value=_make_kakao_mock()):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/v1/auth/kakao", json={"code": "valid_code"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_new_user"] is False
        assert data["access_token"] is not None
        assert any("refresh_token" in h for h in response.headers.get_list("set-cookie"))

        await user.delete()

    async def test_new_user_returns_temp_token(self):
        """신규 회원 카카오 로그인 시 temp_token과 kakao_info를 반환한다."""
        with patch(PATCH_TARGET, return_value=_make_kakao_mock(kakao_id="new_kakao_999")):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/v1/auth/kakao", json={"code": "valid_code"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_new_user"] is True
        assert data["temp_token"] is not None
        assert data["access_token"] is None

    async def test_invalid_code_returns_401(self):
        """유효하지 않은 인가 코드 시 401을 반환한다."""
        error_resp = AsyncMock()
        error_resp.status_code = 400
        error_resp.json = MagicMock(return_value={"error_description": "authorization code not found"})
        error_resp.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("error", request=MagicMock(), response=error_resp)
        )

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=error_resp)

        with patch(PATCH_TARGET, return_value=mock_client):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/v1/auth/kakao", json={"code": "invalid_code"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
