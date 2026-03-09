from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import ORJSONResponse as Response

from app.dependencies.security import get_request_user
from app.dtos.mood_dto import MoodListResponse, MoodResponse, MoodUpdateRequest
from app.models.users import User
from app.services.mood_service import MoodService

router = APIRouter(prefix="/moods", tags=["moods"])

VALID_TIME_SLOTS = {"MORNING", "LUNCH", "EVENING", "BEDTIME"}
DATE_QUERY = Query(None, alias="date")


def _normalize_time_slot(value: str) -> str:
    normalized = value.strip().upper()
    if normalized not in VALID_TIME_SLOTS:
        raise ValueError("INVALID_TIME_SLOT")
    return normalized


def _serialize_mood(mood) -> dict:
    return {
        "mood_id": mood.mood_id,
        "log_date": mood.log_date.isoformat(),
        "time_slot": mood.time_slot,
        "mood_level": mood.mood_level,
        "recorded_at": mood.updated_at.isoformat(),
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_mood(
    body: MoodCreateRequest,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[MoodService, Depends(MoodService)],
) -> Response:
    try:
        slot = _normalize_time_slot(body.time_slot)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="INVALID_TIME_SLOT") from None
    mood = await service.upsert_mood(
        user=user,
        log_date=body.log_date,
        time_slot=slot,
        mood_level=body.mood_level,
    )
    return Response(_serialize_mood(mood), status_code=status.HTTP_201_CREATED)


@router.get("", status_code=status.HTTP_200_OK)
async def get_moods(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[MoodService, Depends(MoodService)],
    date_value: date | None = DATE_QUERY,
) -> Response:
    moods = await service.get_moods(user, date_value=date_value)
    return Response({"message": "success", "data": [_serialize_mood(mood) for mood in moods]})


@router.patch("/{mood_id}", response_model=MoodResponse, status_code=status.HTTP_200_OK)
async def update_mood(
    mood_id: int,
    body: MoodUpdateRequest,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[MoodService, Depends(MoodService)],
) -> Response:
    mood = await service.update_mood(user, mood_id, body.mood_level)
    return Response(MoodResponse.model_validate(mood).model_dump())
from datetime import date
from typing import Annotated
