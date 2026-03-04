from typing import Annotated

from pydantic import AfterValidator, BaseModel, EmailStr, Field

from app.validators.user_validators import (
    validate_phone_number,
)


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str


class TokenRefreshResponse(LoginResponse):
    pass


class KakaoLoginRequest(BaseModel):
    code: str


# 카카오에서 받아올 수 있는 선택 정보
class KakaoUserInfo(BaseModel):
    nickname: str | None = Field(None, description="카카오 닉네임 (동의 시 제공)")


class KakaoLoginResponse(BaseModel):
    is_new_user: bool
    access_token: str | None = None
    refresh_token: str | None = None
    temp_token: str | None = None
    kakao_info: KakaoUserInfo | None = None


# 회원가입 시 필수/선택 동의 정보
class AgreementStatus(BaseModel):
    terms_of_service: bool = Field(..., description="(필수) 이용약관 동의 여부")
    privacy_policy: bool = Field(..., description="(필수) 개인정보 수집 동의 여부")
    sensitive_policy: bool = Field(..., description="(필수) 민감정보 처리 동의 여부")
    terms_of_marketing: bool = Field(False, description="(선택) 마케팅 수신 동의 여부")


# 최종 회원가입 요청 데이터 (사용자 직접 입력 정보 포함)
class KakaoSignUpRequest(BaseModel):
    nickname: Annotated[str, Field(max_length=10, description="사용할 닉네임 (필수)")]
    phone_number: Annotated[str, AfterValidator(validate_phone_number)]
    phone_verification_token: str
    email: EmailStr = Field(..., description="이메일 주소 (필수)")
    gender: str = Field(..., description="성별 (필수)")
    birthday: str | None = Field(None, description="생년월일 (선택)")
    agreements: AgreementStatus
