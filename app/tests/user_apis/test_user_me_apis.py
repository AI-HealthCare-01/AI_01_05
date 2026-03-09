from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.main import app
from app.models.users import Gender, User
from app.services.jwt import JwtService


async def _create_user_and_get_access_token(kakao_id: str, phone: str, nickname: str) -> tuple[User, str]:
    user = await User.create(
        kakao_id=kakao_id,
        nickname=nickname,
        phone_number=phone,
        gender=Gender.FEMALE,
        email="me@example.com",
        terms_agreed=True,
        privacy_agreed=True,
        sensitive_agreed=True,
    )
    tokens = JwtService().issue_jwt_pair(user)
    return user, str(tokens["access_token"])


class TestUserMeApis(TestCase):
    async def _create_user_with_token(self, kakao_id: str, phone: str) -> tuple[User, str]:
        user = await User.create(
            kakao_id=kakao_id,
            nickname="테스터",
            phone_number=phone,
            terms_agreed=True,
            privacy_agreed=True,
            sensitive_agreed=True,
        )
        at = JwtService().create_access_token(user)
        return user, str(at)

    async def test_get_user_me_success(self):
        """유효한 access_token으로 내 정보를 조회한다."""
        user, access_token = await _create_user_and_get_access_token("me_kakao_001", "01055556666", "내정보테스터")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {access_token}"})

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["nickname"] == "내정보테스터"
        await user.delete()

    async def test_get_user_me_unauthorized(self):
        """토큰 없이 내 정보 조회 시 401을 반환한다."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/users/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
