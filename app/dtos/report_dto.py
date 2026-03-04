from datetime import date
from pydantic import BaseModel


class ReportCreateRequest(BaseModel):
    user_id: int
    start_date: date
    end_date: date


class ReportResponse(BaseModel):
    report_id: int
    user_id: int
    start_date: date
    end_date: date
    summary: str