from fastapi import HTTPException, status

from app.dtos.user_medication_dto import TimeSlotsUpdateRequest, TimeSlotsUpdateResponse, UserMedicationCreateRequest
from app.models.medicine import Medicine
from app.models.user_medication import UserMedication
from app.models.user_settings import UserSettings
from app.models.users import User


class UserMedicationService:
    async def create(self, user: User, data: UserMedicationCreateRequest) -> UserMedication:
        medicine = await Medicine.get_or_none(item_seq=data.item_seq, is_active=True)
        if not medicine:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="의약품을 찾을 수 없습니다.")
        return await UserMedication.create(
            user_id=user.user_id,
            medicine_id=data.item_seq,
            dose_per_intake=data.dose_per_intake,
            daily_frequency=data.daily_frequency,
            total_days=data.total_days,
            start_date=data.start_date,
            meal_time_pref=data.meal_time_pref,
            time_slots=data.time_slots,
        )

    async def list_active(self, user: User) -> list[UserMedication]:
        return await UserMedication.filter(user_id=user.user_id, status="ACTIVE").order_by("-created_at")

    async def list_all(self, user: User) -> list[UserMedication]:
        """ACTIVE 먼저, 나머지는 생성일 역순 정렬"""
        return await UserMedication.filter(user_id=user.user_id).order_by("-status", "-created_at")

    async def delete(self, user: User, medication_id: int) -> bool:
        """Returns False if not found or not owned by user."""
        med = await UserMedication.get_or_none(medication_id=medication_id, user_id=user.user_id)
        if not med:
            return False
        await med.delete()
        return True

    async def get_or_create_settings(self, user: User) -> UserSettings:
        settings = await UserSettings.get_or_none(user_id=user.user_id)
        if settings:
            return settings
        return await UserSettings.create(user_id=user.user_id)

    async def get_time_slots(self, user: User) -> dict[str, str]:
        settings = await self.get_or_create_settings(user)
        return {
            "morning": settings.morning_time.strftime("%H:%M"),
            "lunch": settings.lunch_time.strftime("%H:%M"),
            "evening": settings.evening_time.strftime("%H:%M"),
            "bedtime": settings.bedtime_time.strftime("%H:%M"),
        }

    async def update_time_slots(self, user: User, body: TimeSlotsUpdateRequest) -> TimeSlotsUpdateResponse:
        settings = await self.get_or_create_settings(user)

        update_fields: list[str] = []
        if body.morning is not None:
            hour, minute = map(int, body.morning.split(":"))
            settings.morning_time = settings.morning_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            update_fields.append("morning_time")
        if body.lunch is not None:
            hour, minute = map(int, body.lunch.split(":"))
            settings.lunch_time = settings.lunch_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            update_fields.append("lunch_time")
        if body.evening is not None:
            hour, minute = map(int, body.evening.split(":"))
            settings.evening_time = settings.evening_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            update_fields.append("evening_time")
        if body.bedtime is not None:
            hour, minute = map(int, body.bedtime.split(":"))
            settings.bedtime_time = settings.bedtime_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            update_fields.append("bedtime_time")

        if update_fields:
            update_fields.append("updated_at")
            await settings.save(update_fields=update_fields)

        changed_slots = [
            slot
            for slot, value in (
                ("MORNING", body.morning),
                ("LUNCH", body.lunch),
                ("EVENING", body.evening),
                ("BEDTIME", body.bedtime),
            )
            if value is not None
        ]

        return TimeSlotsUpdateResponse(
            updated_count=len(changed_slots),
            time_slots=changed_slots,
        )
