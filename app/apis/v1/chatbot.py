from fastapi import APIRouter, status

from ai_worker.tasks.chatbot_engine import MedicationChatbot
from app.dtos.chat import ChatRequest, ChatResponse
from app.models.chat import ChatLog

chatbot_router = APIRouter(prefix="/chat", tags=["chatbot"])

chatbot_engine = MedicationChatbot()


@chatbot_router.post("/ask", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def ask_question(request: ChatRequest) -> ChatResponse:
    """사용자의 질문을 받아 AI 답변을 반환합니다. 위기 키워드 감지 시 red_alert=True."""
    result = await chatbot_engine.get_response(
        user_message=request.message,
        meds=request.medication_list,
        user_note=request.user_note,
    )

    await ChatLog.create(
        user_id=1,
        message_content=request.message,
        response_content=result["answer"],
        is_flagged=result["red_alert"],
    )

    return ChatResponse(**result)
