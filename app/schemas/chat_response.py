"""LLM Structured Output을 위한 Pydantic 스키마.

GPT 호출 시 response_format={"type": "json_object"}로 사용하여
LLM이 직접 위기/위험 여부를 판단하도록 한다.
"""

from pydantic import BaseModel, Field


class LLMChatResponse(BaseModel):
    """LLM이 반환하는 구조화된 응답 스키마.

    GPT system prompt에 이 스키마를 명시하고,
    response_format={"type": "json_object"}로 호출하여 파싱한다.
    """

    answer: str = Field(
        ...,
        description="사용자에게 전달할 친절한 답변",
    )
    is_flagged: bool = Field(
        default=False,
        description="위기 감지 여부 (자살/자해/죽고싶 등 감지 시 True) - CrisisOverlay 표시용",
    )
    red_alert: bool = Field(
        default=False,
        description="위험 약물 조합 감지 여부 (병용금기 등) - InfoCard border #FF0000 표시용",
    )
    reasoning: str = Field(
        default="",
        description="LLM의 판단 근거 (감사 추적용, DB 저장용)",
    )

    @classmethod
    def safe_default(cls, answer: str = "죄송합니다. 응답을 생성하는 중에 문제가 발생했습니다.") -> "LLMChatResponse":
        """파싱 실패 시 안전한 기본값 반환."""
        return cls(
            answer=answer,
            is_flagged=False,
            red_alert=False,
            reasoning="파싱 실패로 기본값 반환",
        )

    @classmethod
    def crisis_response(cls, answer: str, alert_type: str) -> "LLMChatResponse":
        """위기 감지 시 반환할 응답."""
        return cls(
            answer=answer,
            is_flagged=True,
            red_alert=True,
            reasoning=f"위기 키워드 감지 (유형: {alert_type})",
        )
