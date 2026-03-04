from datetime import date

from fastapi import APIRouter, Query

from app.dtos.appointment_dto import AppointmentCreateDTO

router = APIRouter(prefix="/appointments", tags=["appointments"])

fake_appointments = []
DATE_QUERY = Query(...)


# ✅ 치료 일정 저장
@router.post("")
def create_appointment(data: AppointmentCreateDTO):
    fake_appointments.append(data)

    return {"message": "success", "data": data}


# ✅ 전체 조회
@router.get("")
def get_appointments():
    return {"message": "success", "data": fake_appointments}


# ✅ 날짜별 조회
@router.get("/by-date")
def get_appointments_by_date(date: date = DATE_QUERY):
    result = [appointment for appointment in fake_appointments if appointment.date == date]

    return {"message": "success", "data": result}
