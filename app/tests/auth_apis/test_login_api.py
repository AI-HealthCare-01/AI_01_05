from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.main import app
from app.models.users import Gender, User

KAKAO_ID = "test_kakao_123"
NICKNAME = "테스터"
PATCH_TARGET = "app.services.auth.httpx.AsyncClient"


def _make_kakao_mock(kakao_id: str = KAKAO_ID, nickname: str = NICKNAME):
    token_resp = AsyncMock()
    token_resp.raise_for_status = MagicMock()
    token_resp.json = MagicMock(return_value={"access_token": "fake_kakao_token"})

    user_resp = AsyncMock()
    user_resp.raise_for_status = MagicMock()
    user_resp.json = MagicMock(
        return_value={
            "id": kakao_id,
            "kakao_account": {"profile": {"nickname": nickname}},
        }
    )

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=token_resp)
    mock_client.get = AsyncMock(return_value=user_resp)
    return mock_client


class TestKakaoLoginAPI(TestCase):
    async def test_existing_user_returns_access_token(self):
        """기존 회원 카카오 로그인 시 access_token과 refresh_token 쿠키를 반환한다."""
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


class TestKakaoCallbackAPI(TestCase):
    async def test_existing_user_redirects_to_main_with_token(self):
        """GET /kakao/callback — 기존 회원은 /main?access_token=... 으로 리다이렉트한다."""
        user = await User.create(
            kakao_id="callback_kakao_001",
            nickname=NICKNAME,
            phone_number="01033334444",
            gender=Gender.UNKNOWN,
            terms_agreed=True,
            privacy_agreed=True,
            sensitive_agreed=True,
        )

        with patch(PATCH_TARGET, return_value=_make_kakao_mock(kakao_id="callback_kakao_001")):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
                follow_redirects=False,
            ) as client:
                response = await client.get("/api/v1/auth/kakao/callback", params={"code": "valid_code"})

        assert response.status_code == status.HTTP_302_FOUND
        location = response.headers["location"]
        assert "/main" in location
        assert "access_token=" in location
        assert any("refresh_token" in h for h in response.headers.get_list("set-cookie"))

        await user.delete()

    async def test_new_user_redirects_to_signup_with_temp_token(self):
        """GET /kakao/callback — 신규 회원은 /signup?temp_token=...&nickname=... 으로 리다이렉트한다."""
        with patch(PATCH_TARGET, return_value=_make_kakao_mock(kakao_id="callback_new_002")):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
                follow_redirects=False,
            ) as client:
                response = await client.get("/api/v1/auth/kakao/callback", params={"code": "valid_code"})

        assert response.status_code == status.HTTP_302_FOUND
        location = response.headers["location"]
        assert "/signup" in location
        assert "temp_token=" in location
        assert "nickname=" in location
