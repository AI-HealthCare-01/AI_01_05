from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import ORJSONResponse as Response

from app.dependencies.security import get_request_user
from app.dtos.user_medication_dto import UserMedicationCreateRequest, UserMedicationResponse
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
        {"medication_id": med.medication_id, "item_seq": med.medicine_id, "status": med.status},
        status_code=status.HTTP_201_CREATED,
    )


@router.get("", status_code=status.HTTP_200_OK)
async def list_user_medications(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[UserMedicationService, Depends(UserMedicationService)],
) -> Response:
    meds = await service.list_active(user)
    return Response(
        [{"medication_id": m.medication_id, "item_seq": m.medicine_id, "status": m.status} for m in meds]
    )
