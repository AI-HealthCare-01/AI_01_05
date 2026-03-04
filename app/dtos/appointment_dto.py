from pydantic import BaseModel
from datetime import date


class AppointmentCreateDTO(BaseModel):
    date: date
    title: str
    memo: str | None = None