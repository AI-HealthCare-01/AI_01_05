from datetime import date, datetime

from pydantic import BaseModel

from app.dtos.base import BaseSerializerModel


class PrescriptionCreateRequest(BaseModel):
    drug_name: str
    dosage: str
    frequency: str
    start_date: date
    end_date: date | None = None
    hospital_name: str | None = None
    notes: str | None = None


class PrescriptionUpdateRequest(BaseModel):
    drug_name: str | None = None
    dosage: str | None = None
    frequency: str | None = None
    end_date: date | None = None
    hospital_name: str | None = None
    notes: str | None = None
    is_active: bool | None = None


class PrescriptionResponse(BaseSerializerModel):
    prescription_id: int
    drug_name: str
    dosage: str
    frequency: str
    start_date: date
    end_date: date | None
    hospital_name: str | None
    is_active: bool


class PrescriptionListResponse(BaseModel):
    prescriptions: list[PrescriptionResponse]


class MedicationLogCreateRequest(BaseModel):
    log_date: date
    is_taken: bool = False


class MedicationLogResponse(BaseSerializerModel):
    log_id: int
    prescription_id: int
    log_date: date
    is_taken: bool
    taken_at: datetime | None
