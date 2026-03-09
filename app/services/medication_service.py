import zoneinfo
from datetime import date, datetime

from fastapi import HTTPException, status

from app.models.medication import MedicationLog, MedicationPrescription
from app.models.users import User

KST = zoneinfo.ZoneInfo("Asia/Seoul")


class MedicationService:
    async def create_prescription(
        self,
        user: User,
        drug_name: str,
        dosage: str,
        frequency: str,
        start_date: date,
        end_date: date | None = None,
        hospital_name: str | None = None,
        notes: str | None = None,
    ) -> MedicationPrescription:
        return await MedicationPrescription.create(
            user_id=user.user_id,
            drug_name=drug_name,
            dosage=dosage,
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
            hospital_name=hospital_name,
            notes=notes,
        )

    async def get_prescriptions(self, user: User) -> list[MedicationPrescription]:
        return await MedicationPrescription.filter(user_id=user.user_id, is_active=True).order_by("-created_at")

    async def update_prescription(self, user: User, prescription_id: int, data: dict) -> MedicationPrescription:
        p = await MedicationPrescription.get_or_none(prescription_id=prescription_id, user_id=user.user_id)
        if not p:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="처방을 찾을 수 없습니다.")
        update = {k: v for k, v in data.items() if v is not None}
        if update:
            await MedicationPrescription.filter(prescription_id=prescription_id).update(**update)
            await p.refresh_from_db()
        return p

    async def deactivate_prescription(self, user: User, prescription_id: int) -> None:
        p = await MedicationPrescription.get_or_none(prescription_id=prescription_id, user_id=user.user_id)
        if not p:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="처방을 찾을 수 없습니다.")
        await MedicationPrescription.filter(prescription_id=prescription_id).update(is_active=False)

    async def create_log(self, user: User, prescription_id: int, log_date: date, is_taken: bool) -> MedicationLog:
        p = await MedicationPrescription.get_or_none(prescription_id=prescription_id, user_id=user.user_id)
        if not p:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="처방을 찾을 수 없습니다.")
        existing = await MedicationLog.get_or_none(prescription_id=prescription_id, log_date=log_date)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 기록된 복약 정보입니다.")
        taken_at = datetime.now(tz=KST) if is_taken else None
        return await MedicationLog.create(
            prescription_id=prescription_id,
            user_id=user.user_id,
            log_date=log_date,
            is_taken=is_taken,
            taken_at=taken_at,
        )

    async def get_logs_by_date(self, user: User, log_date: date) -> list[MedicationLog]:
        return await MedicationLog.filter(user_id=user.user_id, log_date=log_date)
