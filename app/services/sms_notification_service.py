"""SMS 복약 알림 서비스.

APScheduler에서 1분마다 호출되어 복용 예정 사용자에게 SMS 발송.
Solapi API + Redis 중복 발송 방지.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import uuid
from datetime import UTC, datetime, timedelta

import httpx
from redis.asyncio import Redis

from app.core import config

logger = logging.getLogger("dodaktalk.sms_notification")

# SMS 메시지 템플릿
SMS_TEMPLATE = "[도닥톡] {nickname}님, {time_label} 약 드실 시간이에요! {medicine_names}"


class SMSNotificationService:
    """복약 알림 SMS 서비스."""

    def __init__(self, redis_client: Redis) -> None:
        self.redis = redis_client
        self.dedup_ttl = 120  # 중복 방지 TTL (2분)

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

            # 발송 성공 → 중복 방지 마킹
            await self._mark_as_sent(user_id, time_slot)
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


async def get_active_medication_users(redis_client: Redis) -> list[dict]:
    """현재 시간 기준 복용 예정 사용자 조회.

    time_slots에서 현재 시간 ±5분 이내 복용 예정인 사용자 반환.

    Returns:
        [
            {
                "user_id": int,
                "phone_number": str,
                "nickname": str,
                "medicine_names": list[str],
                "time_slot": str,  # "08:00"
                "time_label": str,  # "아침"
            },
            ...
        ]
    """
    from app.models.medicine import Medicine
    from app.models.user_medication import UserMedication
    from app.models.users import User

    # KST 현재 시간 (UTC+9)
    now = datetime.now(UTC) + timedelta(hours=9)
    current_hour = now.hour
    current_minute = now.minute

    # 현재 시간 ±5분 범위 계산
    def is_within_range(slot_time: str) -> bool:
        try:
            parts = slot_time.strip().split(":")
            slot_hour = int(parts[0])
            slot_minute = int(parts[1])
            slot_total = slot_hour * 60 + slot_minute
            current_total = current_hour * 60 + current_minute
            return abs(slot_total - current_total) <= 5
        except (ValueError, IndexError):
            return False

    # 시간대 라벨
    def get_time_label(hour: int) -> str:
        if 5 <= hour < 10:
            return "아침"
        if 10 <= hour < 14:
            return "점심"
        if 14 <= hour < 18:
            return "오후"
        if 18 <= hour < 22:
            return "저녁"
        return "밤"

    # 활성 복약 정보 조회
    all_meds = await UserMedication.filter(status="ACTIVE")

    # 사용자별 복용 예정 약물 그룹화
    user_slots: dict[int, dict] = {}  # user_id -> {time_slot: [medicines]}

    for med in all_meds:
        if not med.time_slots:
            continue

        # 직접 Medicine 조회 (prefetch_related 대신)
        medicine = await Medicine.get_or_none(item_seq=med.medicine_id)
        if not medicine:
            continue

        for slot in med.time_slots:
            if is_within_range(slot):
                user_id = med.user_id
                if user_id not in user_slots:
                    user_slots[user_id] = {}
                if slot not in user_slots[user_id]:
                    user_slots[user_id][slot] = []
                user_slots[user_id][slot].append(medicine.item_name)

    if not user_slots:
        return []

    # 사용자 정보 조회 (전화번호, 닉네임)
    user_ids = list(user_slots.keys())
    users = await User.filter(user_id__in=user_ids).all()
    user_map = {u.user_id: u for u in users}

    result: list[dict] = []
    sms_service = SMSNotificationService(redis_client)

    for user_id, slots in user_slots.items():
        user = user_map.get(user_id)
        if not user or not user.phone_number:
            continue

        for time_slot, medicines in slots.items():
            # 중복 발송 체크
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
                    "time_label": get_time_label(hour),
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
