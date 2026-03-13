from datetime import date, datetime, time, timedelta

from pydantic import BaseModel, field_validator

from app.dtos.base import BaseSerializerModel


class AppointmentCreateRequest(BaseModel):
    appointment_date: date | None = None
    appointment_time: time | None = None
    hospital_name: str | None = None


class AppointmentUpdateRequest(BaseModel):
    appointment_date: date | None = None
    appointment_time: time | None = None
    hospital_name: str | None = None


class AppointmentResponse(BaseSerializerModel):
    appointment_id: int
    appointment_date: date | None
    appointment_time: time | None
    hospital_name: str | None
    created_at: datetime

    @field_validator("appointment_time", mode="before")
    @classmethod
    def normalize_appointment_time(cls, value: object) -> object:
        if isinstance(value, timedelta):
            seconds = int(value.total_seconds()) % (24 * 60 * 60)
            hour = seconds // 3600
            minute = (seconds % 3600) // 60
            second = seconds % 60
            return time(hour=hour, minute=minute, second=second)
        return value


class AppointmentNextResponse(BaseModel):
    appointment_id: int
    hospital_name: str | None
    appointment_date: date
    appointment_time: time | None

    @field_validator("appointment_time", mode="before")
    @classmethod
    def normalize_appointment_time(cls, value: object) -> object:
        if isinstance(value, timedelta):
            seconds = int(value.total_seconds()) % (24 * 60 * 60)
            hour = seconds // 3600
            minute = (seconds % 3600) // 60
            second = seconds % 60
            return time(hour=hour, minute=minute, second=second)
        return value


class AppointmentListResponse(BaseModel):
    appointments: list[AppointmentResponse]
