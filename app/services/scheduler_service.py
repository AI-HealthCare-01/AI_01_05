"""APScheduler 기반 백그라운드 스케줄러 서비스.

복약 알림 SMS 등 주기적 작업을 관리.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger("dodaktalk.scheduler")

# 글로벌 스케줄러 인스턴스
_scheduler: AsyncIOScheduler | None = None


async def _medication_reminder_job(redis_client: Redis) -> None:
    """복약 알림 작업 (1분마다 실행).

    Redis 분산 락으로 여러 Worker 중 하나만 실행.
    """
    from app.services.sms_notification_service import send_scheduled_reminders

    lock_key = "scheduler:medication_reminder:lock"
    lock_ttl = 55  # 스케줄러 주기(60초)보다 짧게

    # 분산 락 획득 시도 (SET NX)
    acquired = await redis_client.set(lock_key, "1", nx=True, ex=lock_ttl)
    if not acquired:
        logger.debug("다른 Worker가 복약 알림 작업 실행 중 - 스킵")
        return

    try:
        sent_count = await send_scheduled_reminders(redis_client)
        if sent_count > 0:
            logger.info("복약 알림 작업 완료: %d건 발송", sent_count)
    except Exception as e:
        logger.error("복약 알림 작업 실패: %s", e, exc_info=True)


def get_scheduler() -> AsyncIOScheduler:
    """스케줄러 싱글턴 반환."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


async def start_scheduler(redis_client: Redis) -> None:
    """스케줄러 시작 및 작업 등록.

    Args:
        redis_client: Redis 클라이언트 (중복 발송 방지용)
    """
    scheduler = get_scheduler()

    # 이미 실행 중이면 스킵
    if scheduler.running:
        logger.warning("스케줄러가 이미 실행 중입니다.")
        return

    # 복약 알림 작업 등록 (60초마다)
    scheduler.add_job(
        _medication_reminder_job,
        trigger=IntervalTrigger(seconds=60),
        args=[redis_client],
        id="medication_reminder",
        name="복약 알림 SMS",
        replace_existing=True,
        max_instances=1,  # 동시 실행 방지
    )

    scheduler.start()
    logger.info("APScheduler 시작됨 (복약 알림 60초 주기)")


async def stop_scheduler() -> None:
    """스케줄러 정지."""
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler 정지됨")
