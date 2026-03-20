"""약물 상담 챗봇 서비스.

2중 안전장치:
1. crisis_filter.check() - Regex 키워드 매칭 (LLM 호출 전)
2. LLM Structured Output - is_flagged 판단 (LLM 응답에서)

LangGraph ReAct Agent로 도구 호출 자동화.
"""

import json
import logging
import os
from datetime import UTC

from openai import AsyncOpenAI

from app.schemas.chat_response import LLMChatResponse
from app.services import crisis_filter
from app.services.agent_service import run_agent, run_agent_stream

logger = logging.getLogger("dodaktalk.chatbot")


class MedicationChatbot:
    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def _calculate_intimacy(
        self,
        message_count: int,
        last_message_time: str | None,
    ) -> str:
        """친밀도 레벨 계산."""
        from datetime import datetime

        gap_minutes = None
        if last_message_time:
            try:
                last_time = datetime.fromisoformat(last_message_time)
                now = datetime.now(UTC)
                if last_time.tzinfo is None:
                    last_time = last_time.replace(tzinfo=UTC)
                gap_minutes = (now - last_time).total_seconds() / 60
            except (ValueError, TypeError):
                pass

        # 20분 이상 공백이면 무조건 formal
        if gap_minutes is not None and gap_minutes >= 20:
            return "formal"
        if message_count == 0:
            return "formal"
        if message_count >= 6:
            return "friendly"
        return "normal"

    async def get_response(
        self,
        user_message: str,
        meds: list[str],
        med_dosages: list[str] | None = None,
        user_note: str | None = None,
        character_id: int | None = None,
        nickname: str | None = None,
        chat_history: list[dict] | None = None,
        message_count: int = 0,
        last_message_time: str | None = None,
        user_id: int | None = None,
    ) -> dict:
        """사용자 메시지를 분석하여 응답을 생성합니다.

        Returns:
            {
                "answer": str,
                "warning_level": str,
                "red_alert": bool,
                "alert_type": str | None,
                "is_flagged": bool,
                "reasoning": str,
            }
        """
        # ── 1단계: 위기 키워드 체크 (LLM 호출 전) ──
        crisis_result = crisis_filter.check(user_message)
        if crisis_result.should_skip_llm:
            logger.warning(
                "위기 키워드 감지 (1단계): keyword=%s, type=%s",
                crisis_result.matched_keyword,
                crisis_result.alert_type,
            )
            return {
                "answer": crisis_filter.CRISIS_RESPONSE_MESSAGE,
                "warning_level": "Critical",
                "red_alert": True,
                "alert_type": crisis_result.alert_type,
                "is_flagged": True,
                "reasoning": f"1단계 위기 키워드 감지: {crisis_result.matched_keyword}",
            }

        # ── 2단계: 친밀도 계산 ──
        intimacy = self._calculate_intimacy(message_count, last_message_time)
        logger.info(
            "친밀도 계산: message_count=%d, gap=%s → %s",
            message_count,
            last_message_time,
            intimacy,
        )

        # ── 3단계: LangGraph ReAct Agent 실행 ──
        try:
            llm_response: LLMChatResponse = await run_agent(
                user_message=user_message,
                user_drugs=meds,
                character_id=character_id,
                nickname=nickname,
                chat_history=chat_history,
                message_count=message_count,
                intimacy=intimacy,
                user_id=user_id,
            )

            # ── 5단계: LLM의 is_flagged 판단 확인 (2중 안전장치) ──
            if llm_response.is_flagged:
                logger.warning("위기 감지 (2단계 LLM 판단): reasoning=%s", llm_response.reasoning)
                return {
                    "answer": llm_response.answer,
                    "warning_level": "Critical",
                    "red_alert": True,
                    "alert_type": "LLM_Detected",
                    "is_flagged": True,
                    "reasoning": llm_response.reasoning,
                }

            # ── 정상 응답 ──
            warning_level = "Caution" if meds else "Normal"
            if llm_response.red_alert:
                warning_level = "Warning"

            return {
                "answer": llm_response.answer,
                "warning_level": warning_level,
                "red_alert": llm_response.red_alert,
                "alert_type": None,
                "is_flagged": False,
                "reasoning": llm_response.reasoning,
            }

        except Exception as e:
            logger.error("Agent 실행 실패: %s", e)
            return {
                "answer": "죄송합니다. 답변을 생성하는 중에 문제가 발생했습니다.",
                "warning_level": "Normal",
                "red_alert": False,
                "alert_type": None,
                "is_flagged": False,
                "reasoning": f"Agent 실행 에러: {e}",
            }

    async def get_response_stream(
        self,
        user_message: str,
        meds: list[str],
        med_dosages: list[str] | None = None,
        user_note: str | None = None,
        character_id: int | None = None,
        nickname: str | None = None,
        chat_history: list[dict] | None = None,
        message_count: int = 0,
        last_message_time: str | None = None,
        user_id: int | None = None,
    ):
        """스트리밍 버전 - SSE용 async generator. 토큰 단위로 yield."""
        # ── 1단계: 위기 키워드 체크 (LLM 호출 전) ──
        crisis_result = crisis_filter.check(user_message)
        if crisis_result.should_skip_llm:
            logger.warning(
                "위기 키워드 감지 (1단계 스트림): keyword=%s, type=%s",
                crisis_result.matched_keyword,
                crisis_result.alert_type,
            )
            result = {
                "answer": crisis_filter.CRISIS_RESPONSE_MESSAGE,
                "warning_level": "Critical",
                "red_alert": True,
                "alert_type": crisis_result.alert_type,
                "is_flagged": True,
                "reasoning": f"1단계 위기 키워드 감지: {crisis_result.matched_keyword}",
            }
            yield f"data: {json.dumps(result, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
            return

        # ── 2단계: 친밀도 계산 ──
        intimacy = self._calculate_intimacy(message_count, last_message_time)

        # ── 3단계: LangGraph ReAct Agent 스트리밍 실행 ──
        try:
            async for chunk in run_agent_stream(
                user_message=user_message,
                user_drugs=meds,
                character_id=character_id,
                nickname=nickname,
                chat_history=chat_history,
                message_count=message_count,
                intimacy=intimacy,
                user_id=user_id,
            ):
                yield f"data: {chunk}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error("Agent 스트리밍 실패: %s", e)
            yield f"data: {json.dumps({'token': '죄송합니다. 답변을 생성하는 중에 문제가 발생했습니다.'}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'warning_level': 'Normal', 'red_alert': False, 'is_flagged': False, 'alert_type': None}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
