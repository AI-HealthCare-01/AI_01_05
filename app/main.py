import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

# 1. 로컬 모듈 임포트 (환경 변수 로드 후에 가져와야 안전한 경우)
from app.apis.v1 import v1_routers

# 2. 환경 변수 로드 (가장 먼저 실행)
load_dotenv("envs/.local.env")


# 3. FastAPI 앱 초기화
app = FastAPI(title="AI Healthcare Chatbot Server")

# 4. CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 5. v1 라우터 등록
app.include_router(v1_routers)


# 6. 서버 작동 확인을 위한 루트 경로
@app.get("/")
async def root():
    return {"status": "running", "message": "HealthCare AI Server is alive!"}


# 7. 실행부
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
