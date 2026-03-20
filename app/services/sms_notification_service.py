"""SMS 복약 알림 서비스.

APScheduler에서 1분마다 호출되어 복용 예정 사용자에게 SMS 발송.
Solapi API + Redis 중복 발송 방지.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import uuid
from datetime import UTC, datetime, time, timedelta

import httpx
from redis.asyncio import Redis

from app.core import config
from app.models.medicine import Medicine
from app.models.user_medication import UserMedication
from app.models.user_settings import UserSettings
from app.models.users import User

logger = logging.getLogger("dodaktalk.sms_notification")

# SMS 메시지 템플릿
SMS_TEMPLATE = "[도닥톡] {nickname}님, {time_label} 약 드실 시간이에요! {medicine_names}"
DEFAULT_SLOT_TIMES = {
    "MORNING": "06:00",
    "LUNCH": "11:00",
    "EVENING": "17:00",
    "BEDTIME": "21:00",
}


class SMSNotificationService:
    """복약 알림 SMS 서비스."""

    def __init__(self, redis_client: Redis) -> None:
        self.redis = redis_client
        self.dedup_ttl = 660  # 중복 방지 TTL (11분) - 시간 윈도우(±5분=10분)보다 길게

    def _get_solapi_headers(self) -> dict:
        """Solapi HMAC-SHA256 인증 헤더 생성."""
        api_key = config.SOLAPI_API_KEY
        api_secret = config.SOLAPI_API_SECRET

        date = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        salt = uuid.uuid4().hex
        data = date + salt

        signature = hmac.new(
            api_secret.encode("utf-8"),
            data.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return {
            "Authorization": f"HMAC-SHA256 apiKey={api_key}, date={date}, salt={salt}, signature={signature}",
            "Content-Type": "application/json",
        }

    async def _is_already_sent(self, user_id: int, time_slot: str) -> bool:
        """중복 발송 여부 확인.

        Redis key: med_sms_sent:{user_id}:{날짜}:{시간슬롯}
        """
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        key = f"med_sms_sent:{user_id}:{today}:{time_slot}"
        return await self.redis.exists(key) > 0

    async def _mark_as_sent(self, user_id: int, time_slot: str) -> None:
        """발송 완료 마킹 (TTL 2분)."""
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        key = f"med_sms_sent:{user_id}:{today}:{time_slot}"
        await self.redis.setex(key, self.dedup_ttl, "1")

    async def send_medication_reminder(
        self,
        user_id: int,
        phone_number: str,
        nickname: str,
        medicine_names: list[str],
        time_slot: str,
        time_label: str,
    ) -> bool:
        """SMS 복약 알림 발송.

        Args:
            user_id: 사용자 ID
            phone_number: 수신 전화번호
            nickname: 사용자 닉네임
            medicine_names: 복용 약물 목록
            time_slot: 복용 시간 (HH:MM)
            time_label: 시간대 라벨 (아침, 점심 등)

        Returns:
            발송 성공 여부
        """
        # 중복 발송 체크
        if await self._is_already_sent(user_id, time_slot):
            logger.debug("이미 발송됨: user_id=%d, time_slot=%s", user_id, time_slot)
            return False

        # 발송 시도 전에 먼저 마킹 (실패해도 재시도 방지)
        await self._mark_as_sent(user_id, time_slot)

        # 약물 목록 포맷팅 (최대 3개까지만 표시)
        if len(medicine_names) > 3:
            meds_text = ", ".join(medicine_names[:3]) + f" 외 {len(medicine_names) - 3}개"
        else:
            meds_text = ", ".join(medicine_names)

        message = SMS_TEMPLATE.format(
            nickname=nickname or "회원",
            time_label=time_label,
            medicine_names=meds_text,
        )

        # Solapi SMS 발송
        solapi_url = "https://api.solapi.com/messages/v4/send"
        headers = self._get_solapi_headers()
        payload = {
            "message": {
                "to": phone_number,
                "from": config.SOLAPI_SENDER_NUMBER,
                "text": message,
            }
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    solapi_url,
                    json=payload,
                    headers=headers,
                    timeout=5.0,
                )
                response.raise_for_status()

            logger.info(
                "SMS 발송 성공: user_id=%d, time_slot=%s, medicines=%s",
                user_id,
                time_slot,
                meds_text,
            )
            return True

        except httpx.HTTPStatusError as e:
            logger.error(
                "SMS 발송 실패 (HTTP %d): user_id=%d, detail=%s",
                e.response.status_code,
                user_id,
                e.response.text,
            )
            return False

        except httpx.RequestError as e:
            logger.error("SMS 발송 네트워크 오류: user_id=%d, error=%s", user_id, e)
            return False


def _is_within_time_range(slot_time: str, current_hour: int, current_minute: int) -> bool:
    """현재 시간 ±5분 범위 내인지 확인."""
    try:
        parts = slot_time.strip().split(":")
        slot_total = int(parts[0]) * 60 + int(parts[1])
        current_total = current_hour * 60 + current_minute
        return abs(slot_total - current_total) <= 5
    except (ValueError, IndexError):
        return False


def _normalize_slot_name(slot: str) -> str | None:
    normalized = slot.strip().upper()
    if normalized in DEFAULT_SLOT_TIMES:
        return normalized
    if normalized == "DINNER":
        return "EVENING"
    if normalized == "NIGHT":
        return "BEDTIME"
    return None


def _format_time_value(value: object) -> str | None:
    if isinstance(value, time):
        return value.strftime("%H:%M")
    if isinstance(value, timedelta):
        total_seconds = int(value.total_seconds()) % (24 * 60 * 60)
        hour = total_seconds // 3600
        minute = (total_seconds % 3600) // 60
        return f"{hour:02d}:{minute:02d}"
    if isinstance(value, str):
        parts = value.split(":")
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            hour = int(parts[0])
            minute = int(parts[1])
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return f"{hour:02d}:{minute:02d}"
    return None


def _read_settings_time(slot_name: str, settings: UserSettings) -> object | None:
    field_map = {
        "MORNING": settings.morning_time,
        "LUNCH": settings.lunch_time,
        "EVENING": settings.evening_time,
        "BEDTIME": settings.bedtime_time,
    }
    return field_map.get(slot_name)


def _resolve_slot_time(slot: str, settings: UserSettings | None) -> str | None:
    if ":" in slot:
        return _format_time_value(slot)

    slot_name = _normalize_slot_name(slot)
    if slot_name is None:
        return None

    if settings:
        formatted = _format_time_value(_read_settings_time(slot_name, settings))
        if formatted:
            return formatted

    return DEFAULT_SLOT_TIMES[slot_name]


def _get_time_label_for_sms(hour: int) -> str:
    """시간대 라벨 반환."""
    if 5 <= hour < 10:
        return "아침"
    if 10 <= hour < 14:
        return "점심"
    if 14 <= hour < 18:
        return "오후"
    if 18 <= hour < 22:
        return "저녁"
    return "밤"


async def _build_user_slots(current_hour: int, current_minute: int) -> dict[int, dict]:
    """복용 예정 약물을 사용자별로 그룹화."""
    all_meds = await UserMedication.filter(status="ACTIVE")
    user_ids = list({med.user_id for med in all_meds})
    user_settings = await UserSettings.filter(user_id__in=user_ids).all() if user_ids else []
    settings_by_user = {s.user_id: s for s in user_settings}

    user_slots: dict[int, dict] = {}

    for med in all_meds:
        if not med.time_slots:
            continue
        medicine = await Medicine.get_or_none(item_seq=med.medicine_id)
        if not medicine:
            continue

        for slot in med.time_slots:
            scheduled_time = _resolve_slot_time(str(slot), settings_by_user.get(med.user_id))
            if scheduled_time and _is_within_time_range(scheduled_time, current_hour, current_minute):
                user_id = med.user_id
                user_slots.setdefault(user_id, {}).setdefault(scheduled_time, []).append(medicine.item_name)

    return user_slots


async def get_active_medication_users(redis_client: Redis) -> list[dict]:
    """현재 시간 기준 복용 예정 사용자 조회."""
    now = datetime.now(UTC) + timedelta(hours=9)
    user_slots = await _build_user_slots(now.hour, now.minute)

    if not user_slots:
        return []

    users = await User.filter(user_id__in=list(user_slots.keys())).all()
    user_map = {u.user_id: u for u in users}

    result: list[dict] = []
    sms_service = SMSNotificationService(redis_client)

    for user_id, slots in user_slots.items():
        user = user_map.get(user_id)
        if not user or not user.phone_number:
            continue

        for time_slot, medicines in slots.items():
            if await sms_service._is_already_sent(user_id, time_slot):
                continue

            hour = int(time_slot.split(":")[0])
            result.append(
                {
                    "user_id": user_id,
                    "phone_number": user.phone_number,
                    "nickname": user.nickname,
                    "medicine_names": medicines,
                    "time_slot": time_slot,
                    "time_label": _get_time_label_for_sms(hour),
                }
            )

    return result


async def send_scheduled_reminders(redis_client: Redis) -> int:
    """스케줄된 복약 알림 일괄 발송.

    APScheduler에서 1분마다 호출.

    Returns:
        발송된 SMS 수
    """
    users = await get_active_medication_users(redis_client)
    if not users:
        logger.debug("현재 복용 예정 사용자 없음")
        return 0

    sms_service = SMSNotificationService(redis_client)
    sent_count = 0

    for user_data in users:
        success = await sms_service.send_medication_reminder(
            user_id=user_data["user_id"],
            phone_number=user_data["phone_number"],
            nickname=user_data["nickname"],
            medicine_names=user_data["medicine_names"],
            time_slot=user_data["time_slot"],
            time_label=user_data["time_label"],
        )
        if success:
            sent_count += 1

    if sent_count > 0:
        logger.info("복약 알림 발송 완료: %d건", sent_count)

    return sent_count
