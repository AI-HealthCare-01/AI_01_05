from datetime import date

from pydantic import BaseModel, field_validator, model_validator

from app.dtos.base import BaseSerializerModel


class UserMedicationCreateRequest(BaseModel):
    item_seq: str
    dose_per_intake: float
    daily_frequency: int
    total_days: int
    start_date: date
    meal_time_pref: str | None = None
    time_slots: list[str]


class UserMedicationResponse(BaseSerializerModel):
    medication_id: int
    item_seq: str
    item_name: str
    status: str


class TimeSlotsUpdateRequest(BaseModel):
    morning: str | None = None
    lunch: str | None = None
    evening: str | None = None
    bedtime: str | None = None

    @field_validator("morning", "lunch", "evening", "bedtime")
    @classmethod
    def validate_hhmm_format(cls, value: str | None) -> str | None:
        if value is None:
            return value
        parts = value.split(":")
        if len(parts) != 2:
            raise ValueError("시간은 HH:MM 형식이어야 합니다.")
        hour, minute = parts
        if not (hour.isdigit() and minute.isdigit()):
            raise ValueError("시간은 HH:MM 형식이어야 합니다.")
        hh = int(hour)
        mm = int(minute)
        if hh < 0 or hh > 23 or mm < 0 or mm > 59:
            raise ValueError("유효하지 않은 시간입니다.")
        return f"{hh:02d}:{mm:02d}"

    @model_validator(mode="after")
    def require_any_field(self) -> "TimeSlotsUpdateRequest":
        if all(v is None for v in (self.morning, self.lunch, self.evening, self.bedtime)):
            raise ValueError("최소 1개 이상의 시간대를 입력해야 합니다.")
        return self


class TimeSlotsResponse(BaseModel):
    morning: str
    lunch: str
    evening: str
    bedtime: str


class TimeSlotsUpdateResponse(BaseModel):
    updated_count: int
    time_slots: list[str]
