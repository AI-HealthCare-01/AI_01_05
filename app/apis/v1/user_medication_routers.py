from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import ORJSONResponse as Response
from pydantic import BaseModel

from app.dependencies.security import get_request_user
from app.dtos.user_medication_dto import UserMedicationCreateRequest, UserMedicationResponse
from app.models.user_medication import UserMedication
from app.models.users import User
from app.services.user_medication_service import UserMedicationService

router = APIRouter(prefix="/user-medications", tags=["user-medications"])


class TimeSlotsUpdateRequest(BaseModel):
    """시간대 설정 업데이트 요청."""

    morning: str | None = None  # "HH:MM" 형식
    lunch: str | None = None
    dinner: str | None = None
    night: str | None = None


@router.post("", response_model=UserMedicationResponse, status_code=status.HTTP_201_CREATED)
async def create_user_medication(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[UserMedicationService, Depends(UserMedicationService)],
    body: UserMedicationCreateRequest,
) -> Response:
    med = await service.create(user, body)
    return Response(
        {
            "medication_id": med.medication_id,
            "item_seq": med.medicine_id,
            "item_name": (await med.medicine).item_name,
            "status": med.status,
        },
        status_code=status.HTTP_201_CREATED,
    )


@router.get("", status_code=status.HTTP_200_OK)
async def list_user_medications(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[UserMedicationService, Depends(UserMedicationService)],
) -> Response:
    meds = await service.list_all(user)
    items = []
    for m in meds:
        medicine = await m.medicine
        items.append(
            {
                "medication_id": m.medication_id,
                "item_seq": m.medicine_id,
                "item_name": medicine.item_name,
                "dose_per_intake": float(m.dose_per_intake),
                "daily_frequency": m.daily_frequency,
                "total_days": m.total_days,
                "start_date": str(m.start_date),
                "time_slots": m.time_slots,
                "status": m.status,
            }
        )
    return Response({"items": items})


@router.delete("/{medication_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_medication(
    medication_id: int,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[UserMedicationService, Depends(UserMedicationService)],
) -> None:
    deleted = await service.delete(user, medication_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="복용약을 찾을 수 없습니다.")


@router.patch("/time-slots", status_code=status.HTTP_200_OK)
async def update_time_slots(
    user: Annotated[User, Depends(get_request_user)],
    body: TimeSlotsUpdateRequest,
) -> Response:
    """사용자의 모든 활성 복용약에 시간대 설정을 일괄 업데이트합니다.

    각 시간대 슬롯(morning, lunch, dinner, night)의 시작 시간을 받아
    time_slots JSON 배열에 저장합니다.
    """
    # 시간대 슬롯 배열 생성 (값이 있는 슬롯만)
    time_slots: list[str] = []
    if body.morning:
        time_slots.append(body.morning)
    if body.lunch:
        time_slots.append(body.lunch)
    if body.dinner:
        time_slots.append(body.dinner)
    if body.night:
        time_slots.append(body.night)

    # 해당 사용자의 모든 ACTIVE 복용약 업데이트
    updated_count = await UserMedication.filter(
        user_id=user.user_id,
        status="ACTIVE",
    ).update(time_slots=time_slots)

    return Response({"updated_count": updated_count, "time_slots": time_slots})
