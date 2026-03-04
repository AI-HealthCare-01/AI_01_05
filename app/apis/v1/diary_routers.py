from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import ORJSONResponse
from starlette import status

from app.dependencies.security import get_request_user
from app.dtos.diary_report_dto import (
    ChatbotSummaryResponse,
    ChatbotSummarySaveRequest,
    DeleteDiaryResponse,
    DiaryByDateResponse,
    DiaryCalendarResponse,
    DiarySaveResponse,
    DiaryTextSaveRequest,
    DiaryUpdateRequest,
    OcrConfirmRequest,
    OcrUploadResponse,
    ReportCreateRequest,
    ReportDetailResponse,
    ReportListResponse,
    ReportUpdateRequest,
    ReportUpdateResponse,
)
from app.models.users import User
from app.services.diary_report_service import DiaryReportService

router = APIRouter(prefix="/diary", tags=["diary"])
service = DiaryReportService()


@router.get("/calendar", response_model=DiaryCalendarResponse)
async def get_diary_calendar(
    year: int,
    month: int,
    user: Annotated[User, Depends(get_request_user)],
):
    try:
        return await service.get_calendar(user_id=user.user_id, year=year, month=month)
    except ValueError as e:
        return ORJSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"error": str(e)})


@router.post("/{entry_date}/text", response_model=DiarySaveResponse, status_code=status.HTTP_201_CREATED)
async def create_diary_text(
    entry_date: date,
    request: DiaryTextSaveRequest,
    user: Annotated[User, Depends(get_request_user)],
):
    return await service.create_text_diary(
        user_id=user.user_id,
        entry_date=entry_date,
        title=request.title,
        content=request.content,
    )


@router.post("/{entry_date}/photo/ocr", response_model=OcrUploadResponse)
async def extract_ocr_text(
    entry_date: date,
    _user: Annotated[User, Depends(get_request_user)],
    image: UploadFile = File(...),
):
    file_type = (image.content_type or "").lower()
    file_bytes = await image.read()
    try:
        return service.extract_ocr_text(entry_date=entry_date, file_type=file_type, file_bytes=file_bytes)
    except ValueError as e:
        error_code = str(e)
        if error_code == "FILE_TOO_LARGE":
            status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        else:
            status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        return ORJSONResponse(status_code=status_code, content={"error": error_code})


@router.post("/{entry_date}/photo/ocr/confirm", response_model=DiarySaveResponse, status_code=status.HTTP_201_CREATED)
async def confirm_ocr_text(
    entry_date: date,
    request: OcrConfirmRequest,
    user: Annotated[User, Depends(get_request_user)],
):
    try:
        return await service.confirm_ocr_text(
            user_id=user.user_id,
            entry_date=entry_date,
            entry_id=request.entryId,
            title=request.title,
            content=request.content,
        )
    except LookupError as e:
        return ORJSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": str(e)})


@router.get("/{entry_date}/chatbot/summary", response_model=ChatbotSummaryResponse)
async def get_chatbot_summary(
    entry_date: date,
    user: Annotated[User, Depends(get_request_user)],
):
    return await service.get_chatbot_summary(user_id=user.user_id, entry_date=entry_date)


@router.post("/{entry_date}/chatbot/summary/save", response_model=DiarySaveResponse, status_code=status.HTTP_201_CREATED)
async def save_chatbot_summary(
    entry_date: date,
    request: ChatbotSummarySaveRequest,
    user: Annotated[User, Depends(get_request_user)],
):
    try:
        return await service.save_chatbot_summary(
            user_id=user.user_id,
            entry_date=entry_date,
            entry_id=request.entryId,
            title=request.title,
            content=request.content,
        )
    except LookupError as e:
        return ORJSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": str(e)})


@router.put("/{entry_date}/entry/{entry_id}", response_model=DiarySaveResponse)
async def update_diary_entry(
    entry_date: date,
    entry_id: int,
    request: DiaryUpdateRequest,
    user: Annotated[User, Depends(get_request_user)],
):
    try:
        return await service.update_diary_entry(
            user_id=user.user_id,
            entry_date=entry_date,
            entry_id=entry_id,
            title=request.title,
            content=request.content,
        )
    except LookupError as e:
        return ORJSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": str(e)})


@router.delete("/{entry_date}/entry/{entry_id}", response_model=DeleteDiaryResponse)
async def delete_diary_entry(
    entry_date: date,
    entry_id: int,
    user: Annotated[User, Depends(get_request_user)],
):
    try:
        return await service.delete_diary_entry(user_id=user.user_id, entry_date=entry_date, entry_id=entry_id)
    except LookupError as e:
        return ORJSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": str(e)})


@router.get("/report", response_model=ReportListResponse)
async def get_reports(user: Annotated[User, Depends(get_request_user)]):
    return await service.get_reports(user_id=user.user_id)


@router.post("/report", response_model=ReportDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    request: ReportCreateRequest,
    user: Annotated[User, Depends(get_request_user)],
):
    try:
        return await service.create_report(
            user_id=user.user_id,
            start_date=request.startDate,
            end_date=request.endDate,
        )
    except ValueError as e:
        return ORJSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"error": str(e)})


@router.get("/report/{report_id}", response_model=ReportDetailResponse)
async def get_report_detail(
    report_id: int,
    user: Annotated[User, Depends(get_request_user)],
):
    try:
        return await service.get_report_detail(user_id=user.user_id, report_id=report_id)
    except LookupError as e:
        return ORJSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": str(e)})


@router.put("/report/{report_id}", response_model=ReportUpdateResponse)
async def update_report(
    report_id: int,
    request: ReportUpdateRequest,
    user: Annotated[User, Depends(get_request_user)],
):
    try:
        return await service.update_report(user_id=user.user_id, report_id=report_id, summary=request.summary)
    except LookupError as e:
        return ORJSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": str(e)})


@router.get("/{entry_date}", response_model=DiaryByDateResponse)
async def get_diary_by_date(
    entry_date: date,
    user: Annotated[User, Depends(get_request_user)],
):
    try:
        return await service.get_diary_by_date(user_id=user.user_id, entry_date=entry_date)
    except LookupError as e:
        return ORJSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": str(e)})
