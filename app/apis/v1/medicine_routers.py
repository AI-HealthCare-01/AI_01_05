from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import ORJSONResponse as Response

from app.dependencies.security import get_request_user
from app.dtos.medicine_dto import MedicineDetailResponse, MedicineSearchResponse
from app.models.users import User
from app.services.medicine_service import MedicineService

router = APIRouter(prefix="/medicines", tags=["medicines"])


@router.get("/search", response_model=list[MedicineSearchResponse], status_code=status.HTTP_200_OK)
async def search_medicines(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[MedicineService, Depends(MedicineService)],
    keyword: Annotated[str, Query(min_length=1)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> Response:
    results = await service.search(keyword, limit)
    return Response([MedicineSearchResponse(**r).model_dump() for r in results])


@router.get("/{item_seq}", response_model=MedicineDetailResponse, status_code=status.HTTP_200_OK)
async def get_medicine_detail(
    item_seq: str,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[MedicineService, Depends(MedicineService)],
) -> Response:
    medicine = await service.get_detail(item_seq)
    if not medicine:
        return Response({"detail": "의약품을 찾을 수 없습니다."}, status_code=status.HTTP_404_NOT_FOUND)
    return Response(MedicineDetailResponse.model_validate(medicine).model_dump())
