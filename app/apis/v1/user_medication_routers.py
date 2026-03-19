from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import ORJSONResponse as Response

from app.dependencies.security import get_request_user
from app.dtos.user_medication_dto import (
    TimeSlotsResponse,
    TimeSlotsUpdateRequest,
    TimeSlotsUpdateResponse,
    UserMedicationCreateRequest,
    UserMedicationResponse,
)
from app.models.users import User
from app.services.user_medication_service import UserMedicationService

router = APIRouter(prefix="/user-medications", tags=["user-medications"])


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


@router.get("/time-slots", response_model=TimeSlotsResponse, status_code=status.HTTP_200_OK)
async def get_user_time_slots(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[UserMedicationService, Depends(UserMedicationService)],
) -> TimeSlotsResponse:
    result = await service.get_time_slots(user)
    return TimeSlotsResponse(**result)


@router.patch("/time-slots", response_model=TimeSlotsUpdateResponse, status_code=status.HTTP_200_OK)
async def update_user_time_slots(
    body: TimeSlotsUpdateRequest,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[UserMedicationService, Depends(UserMedicationService)],
) -> TimeSlotsUpdateResponse:
    return await service.update_time_slots(user, body)


@router.delete("/{medication_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_medication(
    medication_id: int,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[UserMedicationService, Depends(UserMedicationService)],
) -> None:
    deleted = await service.delete(user, medication_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="복용약을 찾을 수 없습니다.")
