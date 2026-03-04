import hashlib
import hmac
import logging
import secrets
import uuid
from datetime import UTC, datetime
from typing import Annotated

import httpx
from fastapi import Depends, HTTPException, status
from redis.asyncio import Redis

from app.core import config
from app.core.config import Env
from app.dependencies.redis import get_redis

logger = logging.getLogger(__name__)


class PhoneAuthService:
    def __init__(self, redis_client: Annotated[Redis, Depends(get_redis)]):
        self.redis = redis_client
        self.code_ttl = 180  # 인증번호 유효시간 (3분)
        self.token_ttl = 1800  # 인증 완료 토큰 유효시간 (30분)

    def _get_solapi_headers(self) -> dict:
        api_key = config.SOLAPI_API_KEY
        api_secret = config.SOLAPI_API_SECRET

        date = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        salt = uuid.uuid4().hex
        data = date + salt

        signature = hmac.new(api_secret.encode("utf-8"), data.encode("utf-8"), hashlib.sha256).hexdigest()

        return {
            "Authorization": f"HMAC-SHA256 apiKey={api_key}, date={date}, salt={salt}, signature={signature}",
            "Content-Type": "application/json",
        }

    async def send_verification_code(self, phone_number: str) -> dict:
        # 1. 어뷰징 방지: 1일 최대 발송 횟수 제한 (Rate Limiting)
        daily_limit_key = f"sms_limit:{phone_number}"

        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.incr(daily_limit_key)
            pipe.ttl(daily_limit_key)
            results = await pipe.execute()

        send_count = results[0]
        current_ttl = results[1]

        # 처음 요청했거나, 서버 에러로 인해 만료시간(TTL)이 세팅되지 않은 좀비 데이터(-1)인 경우
        if send_count == 1 or current_ttl == -1:
            await self.redis.expire(daily_limit_key, 86400)  # 24시간 후 만료

        if send_count > 5:
            logger.warning(f"[Rate Limit Exceeded] {phone_number} 일일 인증 횟수 5회 초과")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="일일 인증번호 발송 횟수(5회)를 초과했습니다. 내일 다시 시도해주세요.",
            )

        # 2. 6자리 난수 생성 및 Redis 저장
        code = f"{secrets.randbelow(1000000):06d}"

        redis_key = f"auth_code:{phone_number}"
        await self.redis.setex(redis_key, self.code_ttl, code)

        # 3. 비동기 솔라피 발송 로직
        solapi_url = "https://api.solapi.com/messages/v4/send"
        headers = self._get_solapi_headers()
        payload = {
            "message": {
                "to": phone_number,
                "from": config.SOLAPI_SENDER_NUMBER,
                "text": f"[도닥톡] 인증번호는 [{code}] 입니다. 타인에게 절대 공유하지 마세요.",
            }
        }

        # 동기식 requests 대신 비동기 httpx 클라이언트를 사용하여 서버 블로킹을 막습니다.
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(solapi_url, json=payload, headers=headers, timeout=5.0)
                response.raise_for_status()

            except httpx.HTTPStatusError as e:
                error_data = e.response.json()
                logger.error(
                    f"[Solapi Error] 상태코드: {e.response.status_code}, 상세: {error_data}",
                    exc_info=True,
                )

                # 에러 코드에 따른 명확한 프론트엔드 피드백
                if e.response.status_code == 402:
                    detail_msg = "시스템 오류가 발생했습니다. (관리자: SMS 잔액 부족)"
                elif e.response.status_code == 400:
                    detail_msg = "잘못된 전화번호 형식이거나 지원하지 않는 번호입니다."
                else:
                    detail_msg = "인증번호 발송 중 일시적인 오류가 발생했습니다."

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=detail_msg,
                ) from e

            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="통신사 네트워크 지연으로 발송에 실패했습니다. 잠시 후 다시 시도해주세요.",
                ) from e

        return {
            "ttl": self.code_ttl,
            "message": "인증번호가 성공적으로 발송되었습니다.",
        }

    async def verify_code(self, phone_number: str, code: str) -> str:
        redis_key = f"auth_code:{phone_number}"
        stored_code = await self.redis.get(redis_key)

        if not stored_code or stored_code.decode() != code:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="인증번호가 일치하지 않거나 유효시간이 만료되었습니다.",
            )

        # 인증 성공 시: 사용한 인증번호는 즉시 파기 (재사용 방지)
        await self.redis.delete(redis_key)

        # 회원가입 완료까지 상태를 유지할 고유 검증 토큰 발급
        verification_token = str(uuid.uuid4())
        token_key = f"verified_phone:{verification_token}"

        await self.redis.setex(token_key, self.token_ttl, phone_number)

        return verification_token

    async def validate_verified_token(self, phone_number: str, verification_token: str) -> None:
        if (
            config.ENV != Env.PROD
            and config.TEST_VERIFICATION_TOKEN
            and verification_token == config.TEST_VERIFICATION_TOKEN
        ):
            return

        token_key = f"verified_phone:{verification_token}"
        stored_phone = await self.redis.get(token_key)

        # 토큰이 없거나, 토큰에 묶인 전화번호와 현재 가입하려는 전화번호가 다르면 에러
        if not stored_phone or stored_phone.decode() != phone_number:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="전화번호 인증 정보가 유효하지 않습니다. 다시 인증해주세요.",
            )

        # 가입에 성공적으로 사용된 토큰은 즉시 파기 (중복 가입 방지)
        await self.redis.delete(token_key)
