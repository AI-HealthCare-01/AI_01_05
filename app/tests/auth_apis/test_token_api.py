from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.main import app
from app.models.users import Gender, User
from app.services.jwt import JwtService


async def _create_user_and_get_refresh_token(kakao_id: str, phone: str) -> tuple[User, str]:
    user = await User.create(
        kakao_id=kakao_id,
        nickname="토큰테스터",
        phone_number=phone,
        gender=Gender.UNKNOWN,
        terms_agreed=True,
        privacy_agreed=True,
        sensitive_agreed=True,
    )
    jwt_service = JwtService()
    tokens = jwt_service.issue_jwt_pair(user)
    return user, str(tokens["refresh_token"])


class TestJWTTokenRefreshAPI(TestCase):
    async def test_token_refresh_success(self):
        """유효한 refresh_token 쿠키로 새 access_token을 발급받고, 응답에 refresh_token은 없어야 한다."""
        user, refresh_token = await _create_user_and_get_refresh_token("rt_kakao_001", "01011112222")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            client.cookies["refresh_token"] = refresh_token
            response = await client.get("/api/v1/auth/token/refresh")

        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.json()
        assert "refresh_token" not in response.json()
        await user.delete()

    async def test_token_refresh_missing_token(self):
        """refresh_token 쿠키 없이 요청 시 401을 반환한다."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/auth/token/refresh")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Refresh token is missing."
