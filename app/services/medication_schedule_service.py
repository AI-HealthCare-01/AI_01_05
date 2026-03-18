"""사용자 복용 스케줄 분석 서비스.

user_medications 테이블의 time_slots JSON 컬럼을 활용하여
현재 시간 기준 복용 현황을 분석하고 맥락 있는 정보를 제공.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

logger = logging.getLogger("dodaktalk.schedule")


@dataclass
class MedicationSlot:
    """개별 약물 복용 시간 정보."""

    medicine_name: str
    scheduled_time: str  # "HH:MM" 형식
    dose: str  # "1정", "0.5정" 등
    status: str  # "upcoming", "due", "overdue", "completed"
    minutes_diff: int  # 현재 시간과의 차이 (분)


@dataclass
class ScheduleSummary:
    """복용 스케줄 요약."""

    current_time: str  # "오전 8:25" 형식
    due_medications: list[MedicationSlot]  # 복용 예정 (30분 이내)
    overdue_medications: list[MedicationSlot]  # 복용 시간 지남
    next_medication: MedicationSlot | None  # 다음 복용
    all_slots: list[MedicationSlot]  # 전체 스케줄


def _parse_time(time_str: str) -> tuple[int, int]:
    """시간 문자열을 (hour, minute) 튜플로 파싱."""
    try:
        parts = time_str.strip().split(":")
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return 0, 0


def _format_korean_time(dt: datetime) -> str:
    """datetime을 한국어 시간 형식으로 변환."""
    hour = dt.hour
    minute = dt.minute
    period = "오전" if hour < 12 else "오후"
    display_hour = hour if hour <= 12 else hour - 12
    if display_hour == 0:
        display_hour = 12
    return f"{period} {display_hour}:{minute:02d}"


def _get_time_label(time_str: str) -> str:
    """시간대 라벨 반환."""
    hour, _ = _parse_time(time_str)
    if 5 <= hour < 10:
        return "아침"
    if 10 <= hour < 14:
        return "점심"
    if 14 <= hour < 18:
        return "오후"
    if 18 <= hour < 22:
        return "저녁"
    return "밤"


def _minutes_until(target_time: str, now: datetime) -> int:
    """현재 시간부터 목표 시간까지 분 차이 계산.

    음수: 목표 시간이 이미 지남
    양수: 목표 시간까지 남은 분
    """
    hour, minute = _parse_time(target_time)
    target_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    diff = (target_dt - now).total_seconds() / 60
    return int(diff)


async def get_user_schedule(user_id: int) -> ScheduleSummary:
    """사용자의 오늘 복용 스케줄 분석.

    Args:
        user_id: 사용자 ID

    Returns:
        ScheduleSummary: 복용 스케줄 요약
    """
    from app.models.medicine import Medicine
    from app.models.user_medication import UserMedication

    # KST 기준 현재 시간 (UTC+9)
    now = datetime.now(UTC) + timedelta(hours=9)
    now = now.replace(tzinfo=None)  # naive datetime으로 변환

    meds = await UserMedication.filter(user_id=user_id, status="ACTIVE")

    all_slots: list[MedicationSlot] = []
    due_meds: list[MedicationSlot] = []
    overdue_meds: list[MedicationSlot] = []

    for med in meds:
        # 직접 Medicine 조회 (prefetch_related 대신)
        medicine = await Medicine.get_or_none(item_seq=med.medicine_id)
        if not medicine:
            continue

        time_slots = med.time_slots or []
        dose = f"{med.dose_per_intake}정"
        medicine_name = medicine.item_name

        for slot_time in time_slots:
            minutes_diff = _minutes_until(slot_time, now)

            # 상태 판단
            if -30 <= minutes_diff < 0:
                status = "overdue"  # 30분 이내 지남
            elif 0 <= minutes_diff <= 30:
                status = "due"  # 30분 이내 예정
            elif minutes_diff > 30:
                status = "upcoming"  # 아직 여유 있음
            else:
                status = "completed"  # 30분 넘게 지남 (이미 복용 가정)

            slot = MedicationSlot(
                medicine_name=medicine_name,
                scheduled_time=slot_time,
                dose=dose,
                status=status,
                minutes_diff=minutes_diff,
            )
            all_slots.append(slot)

            if status == "due":
                due_meds.append(slot)
            elif status == "overdue":
                overdue_meds.append(slot)

    # 시간순 정렬
    all_slots.sort(key=lambda x: _parse_time(x.scheduled_time))
    due_meds.sort(key=lambda x: x.minutes_diff)
    overdue_meds.sort(key=lambda x: x.minutes_diff, reverse=True)

    # 다음 복용 찾기 (30분 이후 가장 가까운 것)
    next_med = None
    upcoming = [s for s in all_slots if s.status == "upcoming"]
    if upcoming:
        next_med = upcoming[0]

    return ScheduleSummary(
        current_time=_format_korean_time(now),
        due_medications=due_meds,
        overdue_medications=overdue_meds,
        next_medication=next_med,
        all_slots=all_slots,
    )


async def format_schedule_text(user_id: int) -> str:
    """사용자 복용 스케줄을 텍스트로 포맷팅.

    챗봇 프롬프트에 주입할 형식.
    """
    summary = await get_user_schedule(user_id)

    if not summary.all_slots:
        return ""

    lines = [f"[복용 스케줄 현황]\n현재 시간: {summary.current_time}"]

    # 복용 예정 (30분 이내)
    if summary.due_medications:
        for slot in summary.due_medications:
            if slot.minutes_diff == 0:
                time_info = "지금"
            else:
                time_info = f"{slot.minutes_diff}분 후"
            lines.append(f"- {slot.medicine_name} ({slot.dose}): {slot.scheduled_time} 복용 예정 ({time_info})")

    # 복용 시간 지남 (30분 이내)
    if summary.overdue_medications:
        for slot in summary.overdue_medications:
            lines.append(
                f"- {slot.medicine_name} ({slot.dose}): {slot.scheduled_time} 복용 시간 지남 ({-slot.minutes_diff}분 전)"
            )

    # 다음 복용
    if summary.next_medication:
        next_slot = summary.next_medication
        time_label = _get_time_label(next_slot.scheduled_time)
        lines.append(f"- 다음 복용: {time_label} {next_slot.scheduled_time} ({next_slot.medicine_name})")

    return "\n".join(lines)


def _group_slots_by_time(all_slots: list[MedicationSlot]) -> dict[str, list[MedicationSlot]]:
    """복용 슬롯을 시간대별로 그룹화."""
    time_groups: dict[str, list[MedicationSlot]] = {}
    for slot in all_slots:
        label = _get_time_label(slot.scheduled_time)
        if label not in time_groups:
            time_groups[label] = []
        time_groups[label].append(slot)
    return time_groups


def _format_time_groups(time_groups: dict[str, list[MedicationSlot]]) -> list[str]:
    """시간대별 그룹을 텍스트 라인으로 포맷팅."""
    lines = []
    for label in ["아침", "점심", "오후", "저녁", "밤"]:
        if label not in time_groups:
            continue
        lines.append(f"[{label}]")
        for slot in time_groups[label]:
            emoji = "⏰" if slot.status == "due" else ("⚠️" if slot.status == "overdue" else "📋")
            lines.append(f"  {emoji} {slot.scheduled_time} - {slot.medicine_name} ({slot.dose})")
        lines.append("")
    return lines


async def get_full_schedule_text(user_id: int) -> str:
    """전체 복용 스케줄을 텍스트로 반환 (Tool용)."""
    summary = await get_user_schedule(user_id)

    if not summary.all_slots:
        return "등록된 복용 스케줄이 없습니다."

    lines = [f"[오늘 복용 스케줄]\n현재 시간: {summary.current_time}\n"]

    time_groups = _group_slots_by_time(summary.all_slots)
    lines.extend(_format_time_groups(time_groups))

    if summary.due_medications:
        lines.append("⏰ 지금 복용할 약:")
        lines.extend(f"  - {slot.medicine_name}" for slot in summary.due_medications)

    if summary.overdue_medications:
        lines.append("⚠️ 복용 시간이 지난 약:")
        lines.extend(f"  - {slot.medicine_name} ({-slot.minutes_diff}분 전)" for slot in summary.overdue_medications)

    return "\n".join(lines)
