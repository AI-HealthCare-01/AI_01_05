from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from fastapi.responses import JSONResponse as Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core import config
from app.core.config import Env
from app.dtos.auth import (
    KakaoLoginRequest,
    KakaoLoginResponse,
    KakaoSignUpRequest,
    LoginResponse,
    SendPhoneCodeRequest,
    SendPhoneCodeResponse,
    TokenRefreshResponse,
    VerifyPhoneCodeRequest,
    VerifyPhoneCodeResponse,
)
from app.services.auth import AuthService
from app.services.jwt import JwtService
from app.services.phone_auth import PhoneAuthService

auth_router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()


# 1. 토큰 갱신
@auth_router.get(
    "/token/refresh",
    response_model=TokenRefreshResponse,
    status_code=status.HTTP_200_OK,
)
async def token_refresh(
    jwt_service: Annotated[JwtService, Depends(JwtService)],
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> Response:
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is missing.",
        )
    access_token = jwt_service.refresh_jwt(refresh_token)
    return Response(
        content=TokenRefreshResponse(access_token=str(access_token)).model_dump(),
        status_code=status.HTTP_200_OK,
    )


# 2. 카카오 로그인 (인가코드 수신)
@auth_router.post("/kakao", response_model=KakaoLoginResponse, status_code=status.HTTP_200_OK)
async def kakao_login(
    request: KakaoLoginRequest,
    auth_service: Annotated[AuthService, Depends(AuthService)],
) -> Response:
    result_data = await auth_service.process_kakao_login(request.code)

    resp = Response(
        content=result_data.model_dump(),
        status_code=status.HTTP_200_OK,
    )

    if not result_data.is_new_user and result_data.refresh_token:
        refresh_max_age = 14 * 24 * 60 * 60
        resp.set_cookie(
            key="refresh_token",
            value=result_data.refresh_token,
            httponly=True,
            secure=True if config.ENV == Env.PROD else False,
            domain=config.COOKIE_DOMAIN or None,
            max_age=refresh_max_age,
        )
    return resp


# 3. 카카오 회원가입 (추가 정보 입력)
@auth_router.post(
    "/kakao/signup",
    response_model=LoginResponse,
    status_code=status.HTTP_201_CREATED,
)
async def kakao_signup(
    request: KakaoSignUpRequest,
    auth_service: Annotated[AuthService, Depends(AuthService)],
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    response: Response,
) -> LoginResponse:
    temp_token = credentials.credentials

    tokens = await auth_service.complete_kakao_signup(request, temp_token)

    resp = Response(
        content=tokens.model_dump(exclude={"refresh_token"}),
        status_code=status.HTTP_201_CREATED,
    )

    resp.set_cookie(
        key="refresh_token",
        value=tokens.refresh_token,
        httponly=True,
        secure=True if config.ENV == Env.PROD else False,
        domain=config.COOKIE_DOMAIN or None,
        max_age=14 * 24 * 60 * 60,
    )
    return resp


# 4. 휴대폰 인증번호 발송
@auth_router.post(
    "/phone/send-code",
    response_model=SendPhoneCodeResponse,
    status_code=status.HTTP_200_OK,
    summary="휴대폰 인증번호 발송",
)
async def send_verification_code(
    request: SendPhoneCodeRequest,
    # 팀 컨벤션에 맞게 Annotated 사용
    auth_service: Annotated[PhoneAuthService, Depends(PhoneAuthService)],
) -> Response:  # 반환 타입도 팀 룰에 맞게 일치
    """
    휴대폰 번호를 입력받아 6자리 난수 인증번호를 SMS로 발송합니다.
    (일일 최대 5회 제한)
    """
    result = await auth_service.send_verification_code(request.phone_number)

    return Response(
        content=result,
        status_code=status.HTTP_200_OK,
    )


# 5. 휴대폰 인증번호 확인
@auth_router.post(
    "/phone/verify-code",
    response_model=VerifyPhoneCodeResponse,
    status_code=status.HTTP_200_OK,
    summary="휴대폰 인증번호 검증",
)
async def verify_code(
    request: VerifyPhoneCodeRequest,
    auth_service: Annotated[PhoneAuthService, Depends(PhoneAuthService)],
) -> Response:
    """
    사용자가 입력한 인증번호를 검증하고, 성공 시 회원가입에 사용할 임시 토큰을 반환합니다.
    """
    token = await auth_service.verify_code(request.phone_number, request.code)

    response_data = VerifyPhoneCodeResponse(verification_token=token, message="인증이 완료되었습니다.")

    return Response(
        content=response_data.model_dump(),
        status_code=status.HTTP_200_OK,
    )
