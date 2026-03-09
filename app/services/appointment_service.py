from datetime import date

from fastapi import HTTPException, status

from app.models.appointment import Appointment
from app.models.users import User


class AppointmentService:
    async def create_appointment(
        self, user: User, appointment_date: date | None, hospital_name: str | None, notes: str | None
    ) -> Appointment:
        return await Appointment.create(
            user_id=user.user_id,
            appointment_date=appointment_date,
            hospital_name=hospital_name,
            notes=notes,
        )

    async def get_appointments(self, user: User) -> list[Appointment]:
        return await Appointment.filter(user_id=user.user_id).order_by("appointment_date")

    async def update_appointment(
        self,
        user: User,
        appointment_id: int,
        appointment_date: date | None,
        hospital_name: str | None,
        notes: str | None,
    ) -> Appointment:
        appt = await Appointment.get_or_none(appointment_id=appointment_id, user_id=user.user_id)
        if not appt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="일정을 찾을 수 없습니다.")
        update: dict = {}
        if appointment_date is not None:
            update["appointment_date"] = appointment_date
        if hospital_name is not None:
            update["hospital_name"] = hospital_name
        if notes is not None:
            update["notes"] = notes
        if update:
            await Appointment.filter(appointment_id=appointment_id).update(**update)
            await appt.refresh_from_db()
        return appt

    async def delete_appointment(self, user: User, appointment_id: int) -> None:
        appt = await Appointment.get_or_none(appointment_id=appointment_id, user_id=user.user_id)
        if not appt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="일정을 찾을 수 없습니다.")
        await appt.delete()
