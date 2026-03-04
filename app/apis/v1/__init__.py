from fastapi import APIRouter

from app.apis.v1.appointment_routers import router as appointment_router
from app.apis.v1.auth_routers import auth_router
from app.apis.v1.diary_routers import router as diary_router
from app.apis.v1.mood_routers import router as mood_router
from app.apis.v1.user_routers import user_router

v1_routers = APIRouter(prefix="/api/v1")
v1_routers.include_router(auth_router)
v1_routers.include_router(user_router)
v1_routers.include_router(diary_router)
v1_routers.include_router(mood_router)
v1_routers.include_router(appointment_router)
