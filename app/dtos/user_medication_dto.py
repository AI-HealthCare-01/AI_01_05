from datetime import date

from pydantic import BaseModel

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
