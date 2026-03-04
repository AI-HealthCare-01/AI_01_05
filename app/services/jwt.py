from typing import Literal, overload

from fastapi import HTTPException, status

from app.models.users import User
from app.utils.jwt.exceptions import ExpiredTokenError, TokenError
from app.utils.jwt.tokens import AccessToken, RefreshToken, TempToken


class JwtService:
    access_token_class = AccessToken
    refresh_token_class = RefreshToken
    temp_token_class = TempToken

    def create_access_token(self, user: User) -> AccessToken:
        return self.access_token_class.for_user(user)

    def create_refresh_token(self, user: User) -> RefreshToken:
        return self.refresh_token_class.for_user(user)

    @overload
    def verify_jwt(
        self,
        token: str,
        token_type: Literal["access"],
    ) -> AccessToken: ...

    @overload
    def verify_jwt(
        self,
        token: str,
        token_type: Literal["refresh"],
    ) -> RefreshToken: ...

    @overload
    def verify_jwt(self, token: str, token_type: Literal["temp"]) -> TempToken: ...

    def verify_jwt(
        self, token: str, token_type: Literal["access", "refresh", "temp"]
    ) -> AccessToken | RefreshToken | TempToken:
        if token_type == "access":
            token_class = self.access_token_class
        elif token_type == "refresh":
            token_class = self.refresh_token_class
        elif token_type == "temp":
            token_class = self.temp_token_class
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="지원하지 않는 토큰 타입입니다.",
            )

        try:
            verified = token_class(token=token)
            return verified
        except ExpiredTokenError as err:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"{token_type} token has expired.",
            ) from err
        except TokenError as err:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Provided invalid token.",
            ) from err

    def refresh_jwt(self, refresh_token: str) -> AccessToken:
        verified_rt = self.verify_jwt(token=refresh_token, token_type="refresh")
        return verified_rt.access_token

    def issue_jwt_pair(self, user: User) -> dict[str, AccessToken | RefreshToken]:
        rt = self.create_refresh_token(user)
        at = rt.access_token
        return {"access_token": at, "refresh_token": rt}

    def create_temp_token(self, payload: dict) -> TempToken:
        return self.temp_token_class.for_registration(payload)
