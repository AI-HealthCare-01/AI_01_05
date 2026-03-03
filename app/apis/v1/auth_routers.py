from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, status, Header
from fastapi.responses import JSONResponse as Response

from app.core import config
from app.core.config import Env
from app.dtos.auth import (
    LoginResponse,
    TokenRefreshResponse,
    KakaoLoginRequest,
    KakaoLoginResponse,
    KakaoSignUpRequest,
)
from app.services.auth import AuthService
from app.services.jwt import JwtService

auth_router = APIRouter(prefix="/auth", tags=["auth"])


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
        content=TokenRefreshResponse(
            access_token=str(access_token)
        ).model_dump(),
        status_code=status.HTTP_200_OK,
    )


# 2. 카카오 로그인 (인가코드 수신)
@auth_router.post(
    "/kakao", response_model=KakaoLoginResponse, status_code=status.HTTP_200_OK
)
async def kakao_login(
    request: KakaoLoginRequest,
    auth_service: Annotated[AuthService, Depends(AuthService)],
) -> Response:
    """
    1. 카카오 인가 코드를 받아 유저를 판별합니다.
    """
    result_data = await auth_service.process_kakao_login(request.code)

    resp = Response(
        content=KakaoLoginResponse(**result_data).model_dump(),
        status_code=status.HTTP_200_OK,
    )

    if not result_data.get("is_new_user") and "refresh_token" in result_data:
        refresh_max_age = 14 * 24 * 60 * 60

        resp.set_cookie(
            key="refresh_token",
            value=str(result_data["refresh_token"]),
            httponly=True,
            secure=True if config.ENV == Env.PROD else False,
            domain=config.COOKIE_DOMAIN or None,
            max_age=refresh_max_age,  # 여기에 만료 시간 적용
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
    authorization: Annotated[str, Header(description="Bearer <temp_token>")],
) -> Response:
    """
    2. 추가 정보와 임시 토큰을 결합하여 최종 회원가입을 완료합니다.
    """
    temp_token = (
        authorization.split(" ")[1] if " " in authorization else authorization
    )

    tokens = await auth_service.complete_kakao_signup(request, temp_token)

    resp = Response(
        content=LoginResponse(
            access_token=str(tokens["access_token"])
        ).model_dump(),
        status_code=status.HTTP_201_CREATED,
    )

    refresh_max_age = 14 * 24 * 60 * 60

    resp.set_cookie(
        key="refresh_token",
        value=str(tokens["refresh_token"]),
        httponly=True,
        secure=True if config.ENV == Env.PROD else False,
        domain=config.COOKIE_DOMAIN or None,
        max_age=refresh_max_age,
    )
    return resp
