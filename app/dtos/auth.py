from datetime import date
from typing import Annotated, Optional, Dict

from pydantic import AfterValidator, BaseModel, EmailStr, Field

from app.models.users import Gender
from app.validators.user_validators import (
    validate_birthday,
    validate_password,
    validate_phone_number,
)


class LoginResponse(BaseModel):
    access_token: str


class TokenRefreshResponse(LoginResponse):
    pass


class KakaoLoginRequest(BaseModel):
    code: str


class KakaoLoginResponse(BaseModel):
    is_new_user: bool
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    temp_token: Optional[str] = None
    kakao_info: Optional[Dict] = None


class KakaoSignUpRequest(BaseModel):
    nickname: Annotated[str, Field(max_length=10)]
    phone_number: Annotated[str, AfterValidator(validate_phone_number)]
    phone_verification_token: str
    agreements: Dict[str, bool]
