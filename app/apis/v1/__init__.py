from fastapi import APIRouter

from app.apis.v1.appointment_routers import router as appointment_router
from app.apis.v1.auth_routers import auth_router
from app.apis.v1.character_routers import router as character_router
from app.apis.v1.diary_routers import router as diary_router
from app.apis.v1.home_routers import router as home_router
from app.apis.v1.medication_routers import router as medication_router
from app.apis.v1.medicine_routers import router as medicine_router
from app.apis.v1.mood_routers import router as mood_router
from app.apis.v1.chatbot import chatbot_router
from app.apis.v1.user_medication_routers import router as user_medication_router
from app.apis.v1.user_routers import user_router

v1_routers = APIRouter(prefix="/api/v1")
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
