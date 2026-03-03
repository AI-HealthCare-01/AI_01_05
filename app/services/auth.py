from datetime import datetime
from fastapi import status, Depends
from fastapi.exceptions import HTTPException
from pydantic import EmailStr
from tortoise.transactions import in_transaction
import httpx

from app.dtos.auth import KakaoSignUpRequest
from app.models.users import User, Gender
from app.repositories.user_repository import UserRepository
from app.services.jwt import JwtService
from app.services.phone_auth import PhoneAuthService
from app.utils.common import normalize_phone_number
from app.utils.jwt.tokens import AccessToken, RefreshToken
from app.utils.security import hash_password, verify_password
from app.core import config


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository = Depends(),
        jwt_service: JwtService = Depends(),
        phone_auth_service: PhoneAuthService = Depends(),
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

    async def process_kakao_login(self, code: str) -> dict:
        """
        카카오 인가 코드를 받아 액세스 토큰으로 교환하고, 유저 정보를 조회합니다.
        """
        kakao_token_url = "https://kauth.kakao.com/oauth/token"
        kakao_user_info_url = "https://kapi.kakao.com/v2/user/me"

        # 1. 인가 코드로 카카오 Access Token 발급 요청
        token_data = {
            "grant_type": "authorization_code",
            "client_id": config.KAKAO_REST_API_KEY,
            "redirect_uri": config.KAKAO_REDIRECT_URI,
            "client_secret": config.KAKAO_CLIENT_SECRET,
            "code": code,
        }

        async with httpx.AsyncClient() as client:
            try:
                # 타임아웃을 명시적으로 설정하여 외부 API 장애가 우리 서버로 전파되는 것을 막습니다.
                token_response = await client.post(
                    kakao_token_url, data=token_data, timeout=5.0
                )
                token_response.raise_for_status()
                kakao_access_token = token_response.json().get("access_token")
            except httpx.HTTPStatusError as e:
                error_data = e.response.json()
                print(
                    f"[Kakao Token Error] 상태코드: {e.response.status_code}, 상세: {error_data}"
                )

                # 카카오가 제공한 실제 에러 설명을 클라이언트로 반환
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"카카오 인증 실패: {error_data.get('error_description', '알 수 없는 오류')}",
                )

            # 2. 발급받은 Access Token으로 카카오 유저 프로필 조회
            headers = {"Authorization": f"Bearer {kakao_access_token}"}
            try:
                user_info_response = await client.get(
                    kakao_user_info_url, headers=headers, timeout=5.0
                )
                user_info_response.raise_for_status()
                kakao_user_data = user_info_response.json()
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="카카오 유저 정보를 가져오는데 실패했습니다.",
                )

        # 3. 받아온 데이터 파싱 (카카오 API 응답 구조에 맞춤)
        kakao_id = str(kakao_user_data.get("id"))
        kakao_account = kakao_user_data.get("kakao_account", {})

        # 와이어프레임에서 보여주기로 한 정보들 및 DB 저장용 정보 추출
        email = kakao_account.get("email")
        gender = kakao_account.get("gender")
        birthyear = kakao_account.get("birthyear")  # 예: "1999"
        birthday = kakao_account.get("birthday")  # 예: "1120"

        # [수정됨] DB 저장을 위해 "YYYY-MM-DD" 형태의 문자열로 안전하게 조립합니다.
        formatted_birthday = None
        if birthyear and birthday:
            formatted_birthday = f"{birthyear}-{birthday[:2]}-{birthday[2:]}"

        # 4. DB에서 기존 유저인지 확인
        user = await self.user_repo.get_user_by_kakao_id(kakao_id)

        if user:
            # Case A: 이미 가입된 유저 -> 정상 로그인 처리
            tokens = await self.login(user)
            return {
                "is_new_user": False,
                "access_token": str(tokens["access_token"]),
                "refresh_token": str(tokens["refresh_token"]),
            }
        else:
            # Case B: 신규 유저 -> 임시 토큰 발급 및 정보 반환

            # [핵심 보안 수정] 다음 가입 단계에서 꺼내 쓸 수 있도록
            # 프론트엔드에서 받지 않을 정보들을 토큰 페이로드에 꽉 채워 넣습니다!
            token_payload = {
                "kakao_id": kakao_id,
                "email": email,
                "gender": gender,
                "birthday": formatted_birthday,  # 조립한 날짜 문자열
            }
            temp_token = self.jwt_service.create_temp_token(token_payload)

            return {
                "is_new_user": True,
                "temp_token": str(temp_token),
                "kakao_info": {
                    "email": email,
                    "gender": gender,
                    "birthyear": birthyear,  # 프론트엔드 와이어프레임 노출용
                    "birthday": birthday,  # 프론트엔드 와이어프레임 노출용
                },
            }

    async def complete_kakao_signup(
        self, request: KakaoSignUpRequest, temp_token: str
    ) -> dict:
        """
        [보안 강화 및 객체지향 리팩토링 버전]
        클라이언트의 입력을 최소화하고, 신뢰할 수 있는 임시 토큰 객체에서 카카오 데이터를 추출하여 회원가입을 완료합니다.
        """

        # 1. 임시 토큰 해독 및 카카오 보증 데이터 추출 (리팩토링 반영)
        temp_token_obj = self.jwt_service.verify_jwt(
            token=temp_token, token_type="temp"
        )
        payload = temp_token_obj.payload  # TempToken 객체에서 딕셔너리 추출

        kakao_id = payload.get("kakao_id")
        raw_email = payload.get("email")
        raw_gender = payload.get("gender")  # 예: "male" 또는 "female"
        raw_birthday = payload.get("birthday")  # 예: "1999-01-02"

        if not kakao_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="비정상적인 접근입니다. 토큰에 식별자가 없습니다.",
            )

        # 2. 필수 약관 동의 검증
        agreements = request.agreements
        if not agreements.get("terms_of_service") or not agreements.get(
            "privacy_policy"
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="필수 서비스 이용 약관 및 개인정보 수집에 동의해야 합니다.",
            )

        # 3. 전화번호 인증 토큰 검증
        await self.phone_auth_service.validate_verified_token(
            phone_number=request.phone_number,
            verification_token=request.phone_verification_token,
        )

        # 4. 방어 로직: 카카오 ID 중복 가입 확인
        existing_kakao_user = await self.user_repo.get_user_by_kakao_id(
            kakao_id
        )
        if existing_kakao_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 가입된 카카오 계정입니다.",
            )

        # 5. 방어 로직: 전화번호 중복 가입 확인
        existing_phone_user = await User.get_or_none(
            phone_number=request.phone_number
        )
        if existing_phone_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 해당 전화번호로 가입된 계정이 존재합니다.",
            )

        # 6. 데이터 타입 변환 (Type Casting)
        # 6-1. 성별(Gender) Enum 매핑
        try:
            user_gender = (
                Gender(raw_gender.upper()) if raw_gender else Gender.UNKNOWN
            )
        except ValueError:
            user_gender = Gender.UNKNOWN

        # 6-2. 생년월일(Date) 매핑
        user_birthday = None
        if raw_birthday:
            try:
                user_birthday = datetime.strptime(
                    raw_birthday, "%Y-%m-%d"
                ).date()
            except ValueError:
                pass

        # 7. 방어 로직: 필수 약관 동의 검증
        agreements = request.agreements
        if (
            not agreements.get("terms_of_service")
            or not agreements.get("privacy_policy")
            or not agreements.get("sensitive_policy")
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="필수 서비스 이용 약관, 개인정보 수집 및 민감정보 처리에 모두 동의해야 합니다.",
            )

        # 8. 검증된 데이터만 모아서 User 엔티티 생성 준비
        user_data = {
            "kakao_id": kakao_id,
            "email": raw_email,
            "nickname": request.nickname,
            "name": None,
            "gender": user_gender,
            "birthday": user_birthday,
            "phone_number": request.phone_number,
            "terms_agreed": agreements.get("terms_of_service", False),
            "privacy_agreed": agreements.get("privacy_policy", False),
            "sensitive_agreed": agreements.get("sensitive_policy", False),
            "marketing_agreed": agreements.get("terms_of_marketing", False),
        }

        # 9. DB INSERT 및 로그인 토큰 발급
        new_user = await self.user_repo.create_kakao_user(user_data)
        tokens = await self.login(new_user)

        return tokens
