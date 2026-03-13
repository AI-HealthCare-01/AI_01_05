from fastapi import APIRouter

from app.apis.v1.appointment_routers import router as appointment_router
from app.apis.v1.auth_routers import auth_router
from app.apis.v1.character_routers import router as character_router
from app.apis.v1.chatbot import chatbot_router
from app.apis.v1.diary_routers import router as diary_router
from app.apis.v1.home_routers import router as home_router
from app.apis.v1.medication_routers import router as medication_router
from app.apis.v1.medicine_routers import router as medicine_router
from app.apis.v1.mood_routers import router as mood_router
from app.apis.v1.ocr_routers import router as ocr_router
from app.apis.v1.user_medication_routers import router as user_medication_router
from app.apis.v1.user_routers import user_router

# 모든 v1 API는 `/api/v1` prefix를 공유한다.
v1_routers = APIRouter(prefix="/api/v1")
# include 순서는 문서화 태그 정렬/가독성에 영향을 준다.
# 기능별 엔드포인트를 여기에서 중앙 등록해 앱 엔트리포인트(app.main)를 단순화한다.
v1_routers.include_router(auth_router)
v1_routers.include_router(user_router)
v1_routers.include_router(character_router)
v1_routers.include_router(home_router)
v1_routers.include_router(diary_router)
v1_routers.include_router(mood_router)
v1_routers.include_router(appointment_router)
v1_routers.include_router(medication_router)
v1_routers.include_router(chatbot_router)
v1_routers.include_router(medicine_router)
v1_routers.include_router(user_medication_router)
v1_routers.include_router(ocr_router)
