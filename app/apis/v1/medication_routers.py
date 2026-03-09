from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import ORJSONResponse as Response

from app.dependencies.security import get_request_user
from app.dtos.medication_dto import (
    MedicationLogCreateRequest,
    MedicationLogResponse,
    PrescriptionCreateRequest,
    PrescriptionListResponse,
    PrescriptionResponse,
    PrescriptionUpdateRequest,
)
from app.models.users import User
from app.services.medication_service import MedicationService

router = APIRouter(prefix="/medications", tags=["medications"])


@router.post("", response_model=PrescriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_prescription(
    body: PrescriptionCreateRequest,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[MedicationService, Depends(MedicationService)],
) -> Response:
    p = await service.create_prescription(
        user,
        body.drug_name,
        body.dosage,
        body.frequency,
        body.start_date,
        body.end_date,
        body.hospital_name,
        body.notes,
    )
    return Response(PrescriptionResponse.model_validate(p).model_dump(), status_code=status.HTTP_201_CREATED)


@router.get("", response_model=PrescriptionListResponse, status_code=status.HTTP_200_OK)
async def get_prescriptions(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[MedicationService, Depends(MedicationService)],
) -> Response:
    prescriptions = await service.get_prescriptions(user)
    return Response({"prescriptions": [PrescriptionResponse.model_validate(p).model_dump() for p in prescriptions]})


@router.patch("/{prescription_id}", response_model=PrescriptionResponse, status_code=status.HTTP_200_OK)
async def update_prescription(
    prescription_id: int,
    body: PrescriptionUpdateRequest,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[MedicationService, Depends(MedicationService)],
) -> Response:
    p = await service.update_prescription(user, prescription_id, body.model_dump(exclude_none=True))
    return Response(PrescriptionResponse.model_validate(p).model_dump())


@router.delete("/{prescription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_prescription(
    prescription_id: int,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[MedicationService, Depends(MedicationService)],
) -> None:
    await service.deactivate_prescription(user, prescription_id)


@router.post("/{prescription_id}/logs", response_model=MedicationLogResponse, status_code=status.HTTP_201_CREATED)
async def create_medication_log(
    prescription_id: int,
    body: MedicationLogCreateRequest,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[MedicationService, Depends(MedicationService)],
) -> Response:
    log = await service.create_log(user, prescription_id, body.log_date, body.is_taken)
    return Response(MedicationLogResponse.model_validate(log).model_dump(), status_code=status.HTTP_201_CREATED)


@router.get("/logs", response_model=list[MedicationLogResponse], status_code=status.HTTP_200_OK)
async def get_logs_by_date(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[MedicationService, Depends(MedicationService)],
    log_date: Annotated[date, Query(...)],
) -> Response:
    logs = await service.get_logs_by_date(user, log_date)
    return Response([MedicationLogResponse.model_validate(log).model_dump() for log in logs])
