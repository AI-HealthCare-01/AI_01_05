from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.dependencies.security import get_request_user
from app.models.mood import Mood
from app.models.users import User

router = APIRouter(prefix="/moods", tags=["moods"])
VALID_TIME_SLOTS = {"MORNING", "LUNCH", "EVENING", "BEDTIME"}
DATE_QUERY = Query(None, alias="date")


class MoodUpsertRequest(BaseModel):
    log_date: date = Field(alias="log_date")
    time_slot: str = Field(alias="time_slot")
    mood_level: int = Field(alias="mood_level", ge=1, le=7)


def _normalize_time_slot(value: str) -> str:
    normalized = value.strip().upper()
    if normalized not in VALID_TIME_SLOTS:
        raise ValueError("INVALID_TIME_SLOT")
    return normalized


def _serialize_mood(mood: Mood) -> dict:
    return {
        "mood_id": mood.mood_id,
        "log_date": mood.log_date.isoformat(),
        "time_slot": mood.time_slot,
        "mood_level": mood.mood_level,
        "recorded_at": mood.updated_at.isoformat(),
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_mood(
    body: MoodUpsertRequest,
    user: Annotated[User, Depends(get_request_user)],
):
    try:
        slot = _normalize_time_slot(body.time_slot)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="INVALID_TIME_SLOT") from None

    mood = await Mood.get_or_none(user_id=user.user_id, log_date=body.log_date, time_slot=slot)
    if mood:
        mood.mood_level = body.mood_level
        await mood.save(update_fields=["mood_level", "updated_at"])
    else:
        mood = await Mood.create(
            user_id=user.user_id,
            log_date=body.log_date,
            time_slot=slot,
            mood_level=body.mood_level,
        )

    return {"message": "success", "data": _serialize_mood(mood)}


@router.get("", status_code=status.HTTP_200_OK)
async def get_moods(
    user: Annotated[User, Depends(get_request_user)],
    date_value: date | None = DATE_QUERY,
):
    query = Mood.filter(user_id=user.user_id)
    if date_value is not None:
        query = query.filter(log_date=date_value)
    moods = await query.order_by("-log_date", "time_slot")
    return {"message": "success", "data": [_serialize_mood(mood) for mood in moods]}
