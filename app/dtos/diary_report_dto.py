from datetime import date, datetime

from pydantic import BaseModel, Field


class MoodSticker(BaseModel):
    score: int
    color: str
    label: str


class CalendarDay(BaseModel):
    date: date
    hasDiary: bool
    moodStickers: list[MoodSticker]


class DiaryCalendarResponse(BaseModel):
    year: int
    month: int
    days: list[CalendarDay]


class DiaryEntry(BaseModel):
    entryId: int
    source: str
    title: str
    content: str
    createdAt: datetime


class DiaryByDateResponse(BaseModel):
    date: date
    entries: list[DiaryEntry]


class DiaryTextSaveRequest(BaseModel):
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)


class DiarySaveResponse(BaseModel):
    entryId: int
    message: str


class OcrUploadResponse(BaseModel):
    entryId: int
    extractedText: str


class OcrConfirmRequest(BaseModel):
    entryId: int
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)


class ChatbotSummaryResponse(BaseModel):
    hasChatHistory: bool
    entryId: int | None
    summary: str | None
    redirectToChatbot: bool


class ChatbotSummarySaveRequest(BaseModel):
    entryId: int
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)


class DiaryUpdateRequest(BaseModel):
    title: str | None = None
    content: str | None = None


class DeleteDiaryResponse(BaseModel):
    message: str


class ReportListItem(BaseModel):
    reportId: int
    startDate: date
    endDate: date
    createdAt: date


class ReportListResponse(BaseModel):
    reports: list[ReportListItem]


class ReportCreateRequest(BaseModel):
    startDate: date
    endDate: date


class ReportDetailResponse(BaseModel):
    reportId: int
    startDate: date
    endDate: date
    createdAt: date
    summary: str


class ReportUpdateRequest(BaseModel):
    summary: str = Field(min_length=1)


class ReportUpdateResponse(BaseModel):
    reportId: int
    message: str
