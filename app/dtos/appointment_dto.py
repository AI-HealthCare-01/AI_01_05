from datetime import date, datetime

from pydantic import BaseModel

from app.dtos.base import BaseSerializerModel


class AppointmentCreateRequest(BaseModel):
    appointment_date: date | None = None
    hospital_name: str | None = None
    notes: str | None = None


class AppointmentUpdateRequest(BaseModel):
    appointment_date: date | None = None
    hospital_name: str | None = None
    notes: str | None = None


class AppointmentResponse(BaseSerializerModel):
    appointment_id: int
    appointment_date: date | None
    hospital_name: str | None
    notes: str | None
    created_at: datetime


class AppointmentListResponse(BaseModel):
    appointments: list[AppointmentResponse]
