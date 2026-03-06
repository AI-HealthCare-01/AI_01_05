from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.main import app
from app.services.jwt import JwtService


def _make_temp_token(kakao_id: str) -> str:
    return str(JwtService().create_temp_token({"kakao_id": kakao_id}))


class TestKakaoSignupAPI(TestCase):
    async def test_signup_success(self):
        """유효한 temp_token과 전화번호 인증 토큰으로 회원가입이 성공한다."""
        from app.core import config

        kakao_id = "signup_kakao_001"
        temp_token = _make_temp_token(kakao_id)

        with patch(
            "app.services.phone_auth.PhoneAuthService.validate_verified_token",
            new_callable=AsyncMock,
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/auth/kakao/signup",
                    json={
                        "nickname": "신규유저",
                        "phone_number": "01012345678",
                        "phone_verification_token": config.TEST_VERIFICATION_TOKEN,
                        "email": "new@example.com",
                        "gender": "male",
                        "birthday": "1995-01-01",
                        "agreements": {
                            "terms_of_service": True,
                            "privacy_policy": True,
                            "sensitive_policy": True,
                            "terms_of_marketing": False,
                        },
                    },
                    headers={"Authorization": f"Bearer {temp_token}"},
                )

        assert response.status_code == status.HTTP_201_CREATED
        assert "access_token" in response.json()
        assert any("refresh_token" in h for h in response.headers.get_list("set-cookie"))

    async def test_signup_duplicate_kakao_id_returns_409(self):
        """이미 가입된 카카오 ID로 회원가입 시 409를 반환한다."""
        from app.models.users import Gender, User

        kakao_id = "dup_kakao_002"
        await User.create(
            kakao_id=kakao_id,
            nickname="기존유저",
            phone_number="01099998888",
            gender=Gender.UNKNOWN,
            terms_agreed=True,
            privacy_agreed=True,
            sensitive_agreed=True,
        )
        temp_token = _make_temp_token(kakao_id)

        with patch(
            "app.services.phone_auth.PhoneAuthService.validate_verified_token",
            new_callable=AsyncMock,
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/auth/kakao/signup",
                    json={
                        "nickname": "중복유저",
                        "phone_number": "01011110000",
                        "phone_verification_token": "any",
                        "email": "dup@example.com",
                        "gender": "male",
                        "birthday": None,
                        "agreements": {
                            "terms_of_service": True,
                            "privacy_policy": True,
                            "sensitive_policy": True,
                            "terms_of_marketing": False,
                        },
                    },
                    headers={"Authorization": f"Bearer {temp_token}"},
                )

        assert response.status_code == status.HTTP_409_CONFLICT

    async def test_signup_invalid_temp_token_returns_401(self):
        """유효하지 않은 temp_token으로 회원가입 시 401을 반환한다."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/kakao/signup",
                json={
                    "nickname": "테스터",
                    "phone_number": "01012345678",
                    "phone_verification_token": "any",
                    "email": "x@example.com",
                    "gender": "male",
                    "birthday": None,
                    "agreements": {
                        "terms_of_service": True,
                        "privacy_policy": True,
                        "sensitive_policy": True,
                        "terms_of_marketing": False,
                    },
                },
                headers={"Authorization": "Bearer invalid.token.here"},
            )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
