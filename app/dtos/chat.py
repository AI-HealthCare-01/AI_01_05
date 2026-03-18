from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    user_id: int = Field(..., description="사용자 ID")
    message: str = Field(..., description="사용자 질문 메시지")
    medication_list: list[str] = Field(default_factory=list, description="복용 중인 약물 목록")
    user_note: str | None = Field(None, description="사용자 참고 사항")
    character_id: int | None = Field(None, description="선택된 강아지 캐릭터 ID (1~4)")
    chat_history: list[dict] | None = Field(None, description="최근 대화 내역 [{role, content}, ...]")
    message_count: int = Field(0, description="현재 대화에서 주고받은 메시지 횟수")
    last_message_time: str | None = Field(None, description="마지막 메시지 시각 (ISO 문자열)")


class ChatResponse(BaseModel):
    answer: str = Field(..., description="챗봇 응답 메시지")
    warning_level: str = Field(default="Normal", description="위험도 수준 (Normal, Caution, Warning, Critical)")
    red_alert: bool = Field(default=False, description="위험 약물 조합 감지 여부 (InfoCard border #FF0000)")
    alert_type: str | None = Field(None, description="위기 유형 (Direct, Indirect, Substance, LLM_Detected)")
    is_flagged: bool = Field(default=False, description="위기 감지 여부 (CrisisOverlay 표시용)")
    reasoning: str = Field(default="", description="LLM 판단 근거 (감사 추적용)")
