import asyncio
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import ORJSONResponse as Response

from app.dependencies.security import get_request_user
from app.models.appointment import Appointment
from app.models.diary import Diary
from app.models.medication import MedicationLog
from app.models.mood import Mood
from app.models.users import User
from app.services.character_service import CharacterService

router = APIRouter(prefix="/home", tags=["home"])


@router.get("/summary", status_code=status.HTTP_200_OK)
async def home_summary(
    user: Annotated[User, Depends(get_request_user)],
    character_service: Annotated[CharacterService, Depends(CharacterService)],
    date: Annotated[date, Query(...)],
) -> Response:
    mood_q = Mood.filter(user_id=user.user_id).order_by("-created_at").first()
    diary_q = Diary.filter(user_id=user.user_id, diary_date=date, deleted_at__isnull=True).first()
    appt_q = Appointment.filter(user_id=user.user_id, appointment_date__gte=date).order_by("appointment_date").first()
    logs_q = MedicationLog.filter(user_id=user.user_id, log_date=date)

    mood, diary, appointment, logs = await asyncio.gather(mood_q, diary_q, appt_q, logs_q)

    try:
        my_char = await character_service.get_my_character(user)
        char_data = {"name": my_char["name"], "image_url": None}
    except Exception:
        char_data = None

    return Response(
        {
            "user": {"nickname": user.nickname, "character": char_data},
            "today_mood": {"mood_score": mood.mood_score, "note": mood.note} if mood else None,
            "today_diary": {"diary_id": diary.diary_id, "title": diary.title, "diary_date": str(diary.diary_date)}
            if diary
            else None,
            "upcoming_appointment": {
                "appointment_date": str(appointment.appointment_date),
                "hospital_name": appointment.hospital_name,
            }
            if appointment
            else None,
            "today_medications": [{"log_id": log.log_id, "is_taken": log.is_taken} for log in logs],
        }
    )
