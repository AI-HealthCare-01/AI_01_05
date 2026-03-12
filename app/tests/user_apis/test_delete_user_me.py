from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.main import app
from app.models.character import UserCharacter
from app.models.user_medication import UserMedication
from app.models.users import User
from app.services.jwt import JwtService


async def _make_user(kakao_id: str, phone: str) -> tuple[User, str]:
    user = await User.create(
        kakao_id=kakao_id,
        nickname="탈퇴테스터",
        phone_number=phone,
        terms_agreed=True,
        privacy_agreed=True,
        sensitive_agreed=True,
    )
    token = JwtService().create_access_token(user)
    return user, str(token)


class TestDeleteUserMe(TestCase):
    async def test_delete_success_removes_user_and_relations(self):
        """정상 탈퇴: user, user_characters 모두 삭제됨."""
        user, token = await _make_user("del_kakao_001", "01011110001")
        await UserCharacter.create(user=user, character_id=1)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.delete(
                "/api/v1/users/me",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert await User.filter(user_id=user.user_id).exists() is False
        assert await UserCharacter.filter(user_id=user.user_id).count() == 0

    async def test_delete_unauthorized(self):
        """토큰 없이 탈퇴 시도 → 401."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.delete("/api/v1/users/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_delete_user_with_no_relations(self):
        """캐릭터/약 기록 없는 사용자도 정상 탈퇴."""
        user, token = await _make_user("del_kakao_002", "01011110002")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.delete(
                "/api/v1/users/me",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert await User.filter(user_id=user.user_id).exists() is False
