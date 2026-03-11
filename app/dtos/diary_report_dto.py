from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class MoodSticker(BaseModel):
    score: int
    color: str
    label: str


class MoodLog(BaseModel):
    mood_level: int
    time_slot: str


class CalendarDay(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    date: date
    has_diary: bool = Field(alias="hasDiary")
    moods: list[MoodLog] = Field(default_factory=list)


class DiaryCalendarResponse(BaseModel):
    year: int
    month: int
    days: list[CalendarDay]


class DiaryEntry(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    entry_id: int = Field(alias="entryId")
    source: str
    title: str
    content: str
    created_at: datetime = Field(alias="createdAt")


class DiaryByDateResponse(BaseModel):
    date: date
    entries: list[DiaryEntry]
    moods: list[MoodLog] = Field(default_factory=list)


class DiaryTextSaveRequest(BaseModel):
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)


class DiarySaveResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    entry_id: int = Field(alias="entryId")
    message: str


class OcrUploadResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    entry_id: int = Field(alias="entryId")
    extracted_text: str = Field(alias="extractedText")


class OcrConfirmRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    entry_id: int = Field(alias="entryId")
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)


class ChatbotSummaryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    has_chat_history: bool = Field(alias="hasChatHistory")
    entry_id: int | None = Field(alias="entryId")
    title: str | None = None
    summary: str | None
    redirect_to_chatbot: bool = Field(alias="redirectToChatbot")


class ChatbotSummarySaveRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    entry_id: int = Field(alias="entryId")
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)


class DiaryUpdateRequest(BaseModel):
    title: str | None = None
    content: str | None = None


class DeleteDiaryResponse(BaseModel):
    message: str


class ReportListItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    report_id: int = Field(alias="reportId")
    start_date: date = Field(alias="startDate")
    end_date: date = Field(alias="endDate")
    created_at: date = Field(alias="createdAt")


class ReportListResponse(BaseModel):
    reports: list[ReportListItem]


class ReportCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    start_date: date = Field(alias="startDate")
    end_date: date = Field(alias="endDate")


class ReportDetailResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    report_id: int = Field(alias="reportId")
    start_date: date = Field(alias="startDate")
    end_date: date = Field(alias="endDate")
    created_at: date = Field(alias="createdAt")
    summary: str
