# ruff: noqa: E402
from dotenv import load_dotenv
load_dotenv("envs/.local.env")

# ... 나머지 코드
# 2. 환경 변수가 로드된 후, v1_routers를 가져옵니다.
# (이 안에 chatbot, auth, user 라우터가 포함되어 있습니다.)

# 아래와 같이 주석을 달면 에러가 사라집니다.
from fastapi import FastAPI  # noqa: E402
from starlette.middleware.cors import CORSMiddleware  # noqa: E402
from app.apis.v1 import v1_routers  # noqa: E402

# 3. FastAPI 앱 초기화
app = FastAPI(title="AI Healthcare Chatbot Server")

# 4. CORS 설정 (프론트엔드와 통신을 위해 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 5. v1 라우터 등록 (auth, users, chatbot 기능 통합)
# 이제 모든 API는 /api/v1/... 경로로 작동합니다.
app.include_router(v1_routers)


# 6. 서버 작동 확인을 위한 루트 경로
@app.get("/")
async def root():
    return {"status": "running", "message": "HealthCare AI Server is alive!"}


# 7. 파이썬 명령어로 직접 실행할 때 uvicorn 구동
if __name__ == "__main__":
    import uvicorn

    # 8000번 포트에서 서버 실행
    uvicorn.run(app, host="0.0.0.0", port=8001)
