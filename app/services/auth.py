from datetime import date
from typing import Annotated

import httpx
from fastapi import Depends, status
from fastapi.exceptions import HTTPException

from app.core import config
from app.core.logger import setup_logger
from app.dtos.auth import (
    KakaoLoginResponse,
    KakaoSignUpRequest,
    KakaoUserInfo,
    LoginResponse,
)
from app.models.users import Gender, User
from app.repositories.user_repository import UserRepository
from app.services.jwt import JwtService
from app.services.phone_auth import PhoneAuthService
from app.utils.jwt.tokens import AccessToken, RefreshToken

logger = setup_logger(__name__)


class AuthService:
    """인증/회원가입 유스케이스 오케스트레이션 레이어.

    Router에서는 입출력(HTTP)만 처리하고,
    실제 인증 절차(카카오 연동, 중복 검사, 토큰 발급)는 이 서비스에서 담당한다.
    """

    def __init__(
        self,
        user_repo: Annotated[UserRepository, Depends(UserRepository)],
        jwt_service: Annotated[JwtService, Depends(JwtService)],
        phone_auth_service: Annotated[PhoneAuthService, Depends(PhoneAuthService)],
    ):
        self.user_repo = user_repo
        self.jwt_service = jwt_service
        self.phone_auth_service = phone_auth_service

    async def login(self, user: User) -> dict[str, AccessToken | RefreshToken]:
        await self.user_repo.update_last_login(user.user_id)
        return self.jwt_service.issue_jwt_pair(user)

    async def check_phone_number_exists(self, phone_number: str) -> None:
        if await self.user_repo.exists_by_phone_number(phone_number):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 사용중인 휴대폰 번호입니다.",
            )

    async def _fetch_kakao_user_data(self, code: str) -> dict:
        """카카오 인가코드 → 유저 데이터 dict 반환."""
        kakao_token_url = "https://kauth.kakao.com/oauth/token"
        kakao_user_info_url = "https://kapi.kakao.com/v2/user/me"
        token_data = {
            "grant_type": "authorization_code",
            "client_id": config.KAKAO_REST_API_KEY,
            "redirect_uri": config.KAKAO_REDIRECT_URI,
            "client_secret": config.KAKAO_CLIENT_SECRET,
            "code": code,
        }
        async with httpx.AsyncClient() as client:
            try:
                token_response = await client.post(kakao_token_url, data=token_data, timeout=5.0)
                token_response.raise_for_status()
                kakao_access_token = token_response.json().get("access_token")
            except httpx.HTTPStatusError as e:
                error_data = e.response.json()
                logger.error(f"[Kakao Token API Error] {e.response.status_code}: {error_data}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"카카오 인증 실패: {error_data.get('error_description', '알 수 없는 오류')}",
                ) from e
            except httpx.RequestError as e:
                logger.error(f"[Kakao Token Network Error] {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="카카오 인증 서버와 통신이 원활하지 않습니다.",
                ) from e

            try:
                user_info_response = await client.get(
                    kakao_user_info_url, headers={"Authorization": f"Bearer {kakao_access_token}"}, timeout=5.0
                )
                user_info_response.raise_for_status()
                return user_info_response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"[Kakao User Info API Error] {e.response.status_code}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="카카오 유저 정보를 가져올 권한이 없거나 토큰이 만료되었습니다.",
                ) from e
            except httpx.RequestError as e:
                logger.error(f"[Kakao User Info Network Error] {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="카카오 유저 정보 서버와 통신이 원활하지 않습니다.",
                ) from e

    async def process_kakao_login(self, code: str) -> KakaoLoginResponse:
        # 1) 카카오 인가코드로 사용자 식별 정보 조회
        kakao_user_data = await self._fetch_kakao_user_data(code)
        kakao_id = str(kakao_user_data.get("id"))
        nickname = kakao_user_data.get("kakao_account", {}).get("profile", {}).get("nickname")

        # 2) 기존 회원이면 즉시 로그인 토큰 발급
        user = await self.user_repo.get_user_by_kakao_id(kakao_id)
        if user:
            tokens = await self.login(user)
            return KakaoLoginResponse(
                is_new_user=False,
                access_token=str(tokens["access_token"]),
                refresh_token=str(tokens["refresh_token"]),
            )
        # 3) 신규 회원이면 임시 회원가입 토큰 발급
        temp_token = self.jwt_service.create_temp_token({"kakao_id": kakao_id})
        return KakaoLoginResponse(
            is_new_user=True,
            temp_token=str(temp_token),
            kakao_info=KakaoUserInfo(nickname=nickname),
        )

    async def complete_kakao_signup(self, request: KakaoSignUpRequest, temp_token: str) -> LoginResponse:
        # 1) 임시 토큰 검증 후 카카오 ID 복원
        verified_temp_token = self.jwt_service.verify_jwt(temp_token, "temp")

        try:
            kakao_id_from_token = verified_temp_token["kakao_id"]
        except KeyError as e:
            raise HTTPException(
                status_code=400,
                detail="임시 토큰이 유효하지 않거나 카카오 ID 정보가 누락되었습니다.",
            ) from e

        # 2. 필수 약관 동의 검증
        agreements = request.agreements
        if not agreements.terms_of_service or not agreements.privacy_policy or not agreements.sensitive_policy:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="필수 서비스 이용 약관, 개인정보 수집 및 민감정보 처리에 모두 동의해야 합니다.",
            )

        # 3. 전화번호 인증 토큰 검증
        await self.phone_auth_service.validate_verified_token(
            phone_number=request.phone_number,
            verification_token=request.phone_verification_token,
        )

        # 4. 방어 로직: 카카오 ID 중복 가입 확인
        existing_kakao_user = await self.user_repo.get_user_by_kakao_id(kakao_id_from_token)
        if existing_kakao_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 가입된 카카오 계정입니다.",
            )

        # 5. 방어 로직: 전화번호 중복 가입 확인
        existing_phone_user = await User.get_or_none(phone_number=request.phone_number)
        if existing_phone_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 해당 전화번호로 가입된 계정이 존재합니다.",
            )

        # 6. 데이터 타입 변환 (Type Casting)
        # 6-1. 성별(Gender) Enum 매핑
        try:
            user_gender = Gender(request.gender.upper())
        except ValueError:
            user_gender = Gender.UNKNOWN

        # 6-2. 생년월일(Date) 매핑
        user_birthday = None
        if request.birthday:
            try:
                user_birthday = date.fromisoformat(request.birthday)
            except ValueError as e:
                raise HTTPException(status_code=400, detail="생년월일 형식이 올바르지 않습니다.") from e

        # 7. 검증된 데이터만 모아서 User 엔티티 생성 준비
        user_data = {
            "kakao_id": kakao_id_from_token,
            "email": request.email,
            "nickname": request.nickname,
            "gender": user_gender,
            "birthday": user_birthday,
            "phone_number": request.phone_number,
            "terms_agreed": request.agreements.terms_of_service,
            "privacy_agreed": request.agreements.privacy_policy,
            "sensitive_agreed": request.agreements.sensitive_policy,
            "marketing_agreed": request.agreements.terms_of_marketing,
        }

        # 8. DB INSERT 및 로그인 토큰 발급
        new_user = await self.user_repo.create_kakao_user(user_data)

        # 9. 토큰 발급 및 LoginResponse 객체 반환
        tokens = self.jwt_service.issue_jwt_pair(new_user)
        return LoginResponse(
            access_token=str(tokens["access_token"]),
            refresh_token=str(tokens["refresh_token"]),
        )
