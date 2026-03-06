from datetime import date

from pydantic import BaseModel


class AppointmentCreateDTO(BaseModel):
    date: date
    title: str
    memo: str | None = None
