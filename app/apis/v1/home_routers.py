from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core import memory_db
from app.dependencies.security import get_request_user
from app.models.mood import Mood
from app.models.users import User

router = APIRouter(prefix="/home", tags=["home"])
VALID_TIME_SLOTS = {"MORNING", "LUNCH", "EVENING", "BEDTIME"}


class HomeMoodSaveRequest(BaseModel):
    time_slot: str = Field(alias="timeSlot")
    mood_level: int = Field(alias="moodLevel", ge=1, le=7)


class HomeMedicationSaveRequest(BaseModel):
    name: str
    time_slot: str = Field(alias="timeSlot")
    dosage: int = Field(ge=1)


class HomeMedicationCheckRequest(BaseModel):
    is_taken: bool = Field(alias="isTaken")


def _normalize_time_slot(value: str) -> str:
    normalized = value.strip().upper()
    if normalized not in VALID_TIME_SLOTS:
        raise ValueError("INVALID_TIME_SLOT")
    return normalized


@router.get("/appointments/next")
async def get_home_appointment_next(_user: Annotated[User, Depends(get_request_user)]):
    return {
        "today": date.today(),
        "hasUpcoming": False,
        "dDay": None,
        "appointment": None,
    }


@router.get("/moods/today")
async def get_home_moods_today(user: Annotated[User, Depends(get_request_user)]):
    today = date.today()
    moods = await Mood.filter(user_id=user.user_id, log_date=today).order_by("time_slot")
    mood_data = [
        {
            "moodId": mood.mood_id,
            "timeSlot": mood.time_slot,
            "moodLevel": mood.mood_level,
            "recordedAt": mood.updated_at.isoformat(),
        }
        for mood in moods
    ]
    remaining_slots = [
        slot for slot in ("MORNING", "LUNCH", "EVENING", "BEDTIME") if slot not in {m.time_slot for m in moods}
    ]
    return {"date": today, "remainingSlots": remaining_slots, "moods": mood_data}


@router.post("/moods/today")
async def post_home_mood_today(
    request: HomeMoodSaveRequest,
    user: Annotated[User, Depends(get_request_user)],
):
    today = date.today()
    try:
        slot = _normalize_time_slot(request.time_slot)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="INVALID_TIME_SLOT") from None
    mood = await Mood.get_or_none(user_id=user.user_id, log_date=today, time_slot=slot)
    if mood:
        mood.mood_level = request.mood_level
        await mood.save(update_fields=["mood_level", "updated_at"])
    else:
        mood = await Mood.create(
            user_id=user.user_id,
            log_date=today,
            time_slot=slot,
            mood_level=request.mood_level,
        )
    return {"moodId": mood.mood_id, "message": "기분이 저장되었습니다."}


@router.get("/medications/today")
async def get_home_medications_today(user: Annotated[User, Depends(get_request_user)]):
    today = date.today().isoformat()
    items = memory_db.fake_home_medications.get(user.user_id, [])
    today_items = [item for item in items if item["date"] == today]
    response_items = [
        {
            "medicationId": item["medicationId"],
            "itemSeq": item["itemSeq"],
            "name": item["name"],
            "timeSlot": item["timeSlot"],
            "dosePerIntake": item["dosePerIntake"],
            "isTaken": item["isTaken"],
            "takenAt": item["takenAt"],
        }
        for item in today_items
    ]
    remaining_count = len([item for item in today_items if not item["isTaken"]])
    return {"date": today, "items": response_items, "remainingCount": remaining_count}


@router.post("/medications/today")
async def post_home_medication_today(
    request: HomeMedicationSaveRequest,
    user: Annotated[User, Depends(get_request_user)],
):
    try:
        slot = _normalize_time_slot(request.time_slot)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="INVALID_TIME_SLOT") from None
    medication_id = memory_db.home_medication_sequence
    memory_db.home_medication_sequence += 1
    new_item = {
        "date": date.today().isoformat(),
        "medicationId": medication_id,
        "itemSeq": str(medication_id),
        "name": request.name,
        "timeSlot": slot,
        "dosePerIntake": request.dosage,
        "isTaken": False,
        "takenAt": None,
    }
    user_items = memory_db.fake_home_medications.setdefault(user.user_id, [])
    user_items.append(new_item)
    return {"medicationId": medication_id, "message": "복약 항목이 추가되었습니다."}


@router.patch("/medications/today/{medication_id}/check")
async def patch_home_medication_check(
    medication_id: int,
    request: HomeMedicationCheckRequest,
    user: Annotated[User, Depends(get_request_user)],
):
    items = memory_db.fake_home_medications.get(user.user_id, [])
    target = next((item for item in items if item["medicationId"] == medication_id), None)
    if target is None:
        return {"medicationId": medication_id, "isTaken": False, "takenAt": None, "message": "복약 항목이 없습니다."}

    target["isTaken"] = request.is_taken
    target["takenAt"] = datetime.now().isoformat() if request.is_taken else None
    return {
        "medicationId": target["medicationId"],
        "isTaken": target["isTaken"],
        "takenAt": target["takenAt"],
        "message": "복약 상태가 변경되었습니다.",
    }
