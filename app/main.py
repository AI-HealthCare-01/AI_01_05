from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.apis.v1 import v1_routers
from app.core import config
from app.db.databases import initialize_tortoise

# FastAPI 앱 단일 인스턴스.
# docs/redoc/openapi 경로를 API prefix 하위로 통일해 배포 시 라우팅 충돌을 줄인다.
app = FastAPI(
    default_response_class=ORJSONResponse, docs_url="/api/docs", redoc_url="/api/redoc", openapi_url="/api/openapi.json"
)

# 프론트엔드(브라우저)에서 API 호출이 가능하도록 CORS를 구성한다.
# allow_origins는 환경변수 기반(config.ALLOWED_ORIGINS)으로 관리한다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 앱 시작/종료 이벤트에 맞춰 Tortoise ORM 연결을 등록한다.
initialize_tortoise(app)
# /api/v1 하위 라우터를 최종적으로 애플리케이션에 장착한다.
app.include_router(v1_routers)
