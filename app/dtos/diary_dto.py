from datetime import date

from pydantic import BaseModel


class DiaryCreateDTO(BaseModel):
    title: str
    content: str
    date: date
