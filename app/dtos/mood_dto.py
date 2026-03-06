from datetime import datetime

from pydantic import BaseModel, Field

from app.dtos.base import BaseSerializerModel


class MoodCreateRequest(BaseModel):
    mood_score: int = Field(..., ge=1, le=5)
    note: str | None = None


class MoodUpdateRequest(BaseModel):
    mood_score: int | None = Field(None, ge=1, le=5)
    note: str | None = None


class MoodResponse(BaseSerializerModel):
    mood_id: int
    mood_score: int | None
    note: str | None
    created_at: datetime


class MoodListResponse(BaseModel):
    moods: list[MoodResponse]
