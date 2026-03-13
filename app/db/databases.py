from fastapi import FastAPI
from tortoise import Tortoise
from tortoise.contrib.fastapi import register_tortoise

from app.core import config

# Tortoise가 스캔할 모델 모듈 목록.
# aerich.models는 마이그레이션 이력 테이블 관리를 위해 반드시 포함한다.
TORTOISE_APP_MODELS = [
    "aerich.models",
    "app.models",
]

# FastAPI 구동 시 register_tortoise에 전달할 ORM 설정 딕셔너리.
TORTOISE_ORM = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.mysql",
            "dialect": "asyncmy",
            "credentials": {
                "host": config.DB_HOST,
                "port": config.DB_PORT,
                "user": config.DB_USER,
                "password": config.DB_PASSWORD,
                "database": config.DB_NAME,
                "connect_timeout": config.DB_CONNECT_TIMEOUT,
                "maxsize": config.DB_CONNECTION_POOL_MAXSIZE,
            },
        },
    },
    "apps": {
        "models": {
            "models": TORTOISE_APP_MODELS,
            "default_connection": "default",
        },
    },
    "timezone": "Asia/Seoul",
}


def initialize_tortoise(app: FastAPI) -> None:
    # 모델 메타데이터를 선등록해 import 타이밍 이슈를 줄인다.
    Tortoise.init_models(TORTOISE_APP_MODELS, "models")
    # app lifespan과 DB connection lifecycle을 연결한다.
    register_tortoise(app, config=TORTOISE_ORM)
