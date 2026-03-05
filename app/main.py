from dotenv import load_dotenv
import os

# 1. 다른 모듈을 불러오기 전에 반드시 환경 변수를 가장 먼저 로드해야 합니다.
# 이 순서가 틀리면 chatbot_engine이 OPENAI_API_KEY를 찾지 못해 에러가 발생합니다.
load_dotenv("envs/.local.env")

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

# 2. 환경 변수가 로드된 후, v1_routers를 가져옵니다.
# (이 안에 chatbot, auth, user 라우터가 포함되어 있습니다.)
from app.apis.v1 import v1_routers

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