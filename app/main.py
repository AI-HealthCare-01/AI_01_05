import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from redis.asyncio import Redis

from app.apis.v1 import v1_routers
from app.core import config
from app.db.databases import initialize_tortoise
from app.services.agent_service import set_main_loop
from app.services.graph_service import get_graph_service
from app.services.scheduler_service import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app):
    # Redis 클라이언트 (스케줄러용)
    redis_client = Redis(host="redis", port=6379, db=0)

    # 앱 시작 시 Neo4j 미리 초기화
    await get_graph_service()

    # APScheduler 시작 (복약 알림 등)
    await start_scheduler(redis_client)

    set_main_loop(asyncio.get_event_loop())

    yield

    # 앱 종료 시 정리
    await stop_scheduler()
    await redis_client.aclose()


# FastAPI 앱 단일 인스턴스.
# docs/redoc/openapi 경로를 API prefix 하위로 통일해 배포 시 라우팅 충돌을 줄인다.
app = FastAPI(
    lifespan=lifespan,
    default_response_class=ORJSONResponse,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
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

# P95 Latency 측정 미들웨어 (스트리밍 API 제외)
latency_logger = logging.getLogger("dodaktalk.latency")


@app.middleware("http")
async def latency_middleware(request: Request, call_next):
    if "/stream" in request.url.path:
        return await call_next(request)

    start = time.perf_counter()
    response = await call_next(request)
    latency = time.perf_counter() - start

    latency_logger.info(f"LATENCY: {request.method} {request.url.path} {latency:.3f}s")
    return response


# 앱 시작/종료 이벤트에 맞춰 Tortoise ORM 연결을 등록한다.
initialize_tortoise(app)
# /api/v1 하위 라우터를 최종적으로 애플리케이션에 장착한다.
app.include_router(v1_routers)
