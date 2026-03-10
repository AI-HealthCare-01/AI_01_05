import os
import uuid
import zoneinfo
from dataclasses import field
from enum import StrEnum
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Env(StrEnum):
    LOCAL = "local"
    DEV = "dev"
    PROD = "prod"


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="allow")

    ENV: Env = Env.LOCAL
    SECRET_KEY: str = f"default-secret-key{uuid.uuid4().hex}"
    TIMEZONE: zoneinfo.ZoneInfo = field(default_factory=lambda: zoneinfo.ZoneInfo("Asia/Seoul"))
    TEMPLATE_DIR: str = os.path.join(Path(__file__).resolve().parent.parent, "templates")

    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "pw1234"
    DB_NAME: str = "ai_health"
    DB_CONNECT_TIMEOUT: int = 5
    DB_CONNECTION_POOL_MAXSIZE: int = 10

    COOKIE_DOMAIN: str = "localhost"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173"]

    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 14 * 24 * 60
    JWT_LEEWAY: int = 5

    KAKAO_REST_API_KEY: str
    KAKAO_REDIRECT_URI: str
    KAKAO_CLIENT_SECRET: str

    SOLAPI_API_KEY: str
    SOLAPI_API_SECRET: str
    SOLAPI_SENDER_NUMBER: str

    TEST_VERIFICATION_TOKEN: str = ""

    # OCR integration
    # OCR_PROVIDER: "stub" | "http"
    OCR_PROVIDER: str = "stub"
    OCR_API_URL: str | None = None
    OCR_API_KEY: str | None = None
    OCR_TIMEOUT_SECONDS: int = 20

    # LLM integration
    # LLM_PROVIDER: "stub" | "openai"
    LLM_PROVIDER: str = "stub"
    LLM_API_KEY: str | None = None
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TIMEOUT_SECONDS: int = 30

    # MFDS (식약처) e약은요 API
    # MFDS_API_KEY: "" → stub 모드 (빈 리스트 반환)
    MFDS_API_KEY: str = ""
    MFDS_API_TIMEOUT: int = 10
