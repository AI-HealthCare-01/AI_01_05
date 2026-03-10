from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    user_id: int = Field(..., description="사용자 ID")
    message: str = Field(..., description="사용자 질문 메시지")
    medication_list: list[str] = Field(default_factory=list, description="복용 중인 약물 목록")
    user_note: str | None = Field(None, description="사용자 참고 사항")


class ChatResponse(BaseModel):
    answer: str = Field(..., description="챗봇 응답 메시지")
    warning_level: str = Field(default="Normal", description="위험도 수준 (Normal, Caution, Critical)")
    red_alert: bool = Field(default=False, description="위기 상황 여부")
    alert_type: str | None = Field(None, description="위기 유형 (Direct, Indirect, Substance)")
