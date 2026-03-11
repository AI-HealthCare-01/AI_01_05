from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import ORJSONResponse as Response

from app.dependencies.security import get_request_user
from app.dtos.ocr_dto import ParsedPrescriptionResponse
from app.models.users import User
from app.services.ocr_service import OcrService

router = APIRouter(prefix="/ocr", tags=["ocr"])

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/heic", "image/heif", "image/webp"}
_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("/parse-prescription", response_model=ParsedPrescriptionResponse, status_code=status.HTTP_200_OK)
async def parse_prescription(
    user: Annotated[User, Depends(get_request_user)],
    file: Annotated[UploadFile, File()],
) -> Response:
    if file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="지원하지 않는 파일 형식입니다.")

    file_bytes = await file.read()
    if len(file_bytes) > _MAX_FILE_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="파일 크기가 10MB를 초과합니다.")

    service = OcrService()
    result = await service.parse_prescription(file_bytes=file_bytes, file_type=file.content_type)
    return Response(result.model_dump())
