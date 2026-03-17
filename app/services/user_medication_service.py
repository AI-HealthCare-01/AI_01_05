from fastapi import HTTPException, status

from app.dtos.user_medication_dto import UserMedicationCreateRequest
from app.models.medicine import Medicine
from app.models.user_medication import UserMedication
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
