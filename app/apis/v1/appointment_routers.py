from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import ORJSONResponse as Response

from app.dependencies.security import get_request_user
from app.dtos.appointment_dto import (
    AppointmentCreateRequest,
    AppointmentListResponse,
    AppointmentResponse,
    AppointmentUpdateRequest,
)
from app.models.users import User
from app.services.appointment_service import AppointmentService

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    body: AppointmentCreateRequest,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[AppointmentService, Depends(AppointmentService)],
) -> Response:
    appt = await service.create_appointment(user, body.appointment_date, body.hospital_name, body.notes)
    return Response(AppointmentResponse.model_validate(appt).model_dump(), status_code=status.HTTP_201_CREATED)


@router.get("", response_model=AppointmentListResponse, status_code=status.HTTP_200_OK)
async def get_appointments(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[AppointmentService, Depends(AppointmentService)],
) -> Response:
    appts = await service.get_appointments(user)
    return Response({"appointments": [AppointmentResponse.model_validate(a).model_dump() for a in appts]})


@router.patch("/{appointment_id}", response_model=AppointmentResponse, status_code=status.HTTP_200_OK)
async def update_appointment(
    appointment_id: int,
    body: AppointmentUpdateRequest,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[AppointmentService, Depends(AppointmentService)],
) -> Response:
    appt = await service.update_appointment(user, appointment_id, body.appointment_date, body.hospital_name, body.notes)
    return Response(AppointmentResponse.model_validate(appt).model_dump())


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_appointment(
    appointment_id: int,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[AppointmentService, Depends(AppointmentService)],
) -> None:
    await service.delete_appointment(user, appointment_id)
