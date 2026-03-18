from datetime import date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core import memory_db
from app.dependencies.security import get_request_user
from app.models.medicine import Medicine
from app.models.mood import Mood
from app.models.user_medication import UserMedication
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
    time_slot: str = Field(alias="timeSlot")


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
    today = date.today()
    active_meds = await UserMedication.filter(user_id=user.user_id, status="ACTIVE")
    today_meds = [
        med for med in active_meds if med.start_date <= today <= med.start_date + timedelta(days=med.total_days - 1)
    ]

    check_store = memory_db.home_medication_checks.get(user.user_id, {})
    today_str = today.isoformat()

    response_items = []
    for med in today_meds:
        # 직접 Medicine 조회 (prefetch_related 대신)
        medicine = await Medicine.get_or_none(item_seq=med.medicine_id)
        if not medicine:
            continue
        for slot in med.time_slots:
            check_key = f"{med.medication_id}:{slot}:{today_str}"
            check_info = check_store.get(check_key, {})
            response_items.append(
                {
                    "medicationId": med.medication_id,
                    "itemSeq": medicine.item_seq,
                    "name": medicine.item_name,
                    "timeSlot": slot,
                    "dosePerIntake": float(med.dose_per_intake),
                    "isTaken": check_info.get("isTaken", False),
                    "takenAt": check_info.get("takenAt"),
                    "itemImage": medicine.item_image,
                }
            )

    remaining_count = len([item for item in response_items if not item["isTaken"]])
    return {"date": today_str, "items": response_items, "remainingCount": remaining_count}


@router.post("/medications/today")
async def post_home_medication_today(
    request: HomeMedicationSaveRequest,
    user: Annotated[User, Depends(get_request_user)],
):
    try:
        slot = _normalize_time_slot(request.time_slot)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="INVALID_TIME_SLOT") from None
    medicine = await Medicine.get_or_none(item_name=request.name)
    if not medicine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MEDICINE_NOT_FOUND")
    med = await UserMedication.create(
        user_id=user.user_id,
        medicine_id=medicine.item_seq,
        dose_per_intake=request.dosage,
        daily_frequency=1,
        total_days=1,
        start_date=date.today(),
        time_slots=[slot],
    )
    return {"medicationId": med.medication_id, "message": "복약 항목이 추가되었습니다."}


@router.patch("/medications/today/{medication_id}/check")
async def patch_home_medication_check(
    medication_id: int,
    request: HomeMedicationCheckRequest,
    user: Annotated[User, Depends(get_request_user)],
):
    med = await UserMedication.get_or_none(medication_id=medication_id, user_id=user.user_id)
    if not med:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MEDICATION_NOT_FOUND")

    today_str = date.today().isoformat()
    check_store = memory_db.home_medication_checks.setdefault(user.user_id, {})

    try:
        slot = _normalize_time_slot(request.time_slot)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="INVALID_TIME_SLOT") from None

    check_key = f"{medication_id}:{slot}:{today_str}"
    check_store[check_key] = {
        "isTaken": request.is_taken,
        "takenAt": datetime.now().isoformat() if request.is_taken else None,
    }

    return {
        "medicationId": medication_id,
        "isTaken": request.is_taken,
        "takenAt": datetime.now().isoformat() if request.is_taken else None,
        "message": "복약 상태가 변경되었습니다.",
    }
