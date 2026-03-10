import os

import httpx
from fastapi import APIRouter, HTTPException, status

from app.dtos.chat import ChatRequest, ChatResponse
from app.models.chat import ChatLog

chatbot_router = APIRouter(prefix="/chat", tags=["chatbot"])

AI_WORKER_URL = os.getenv("AI_WORKER_URL", "http://ai-worker:8100")


@chatbot_router.post("/ask", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def ask_question(request: ChatRequest) -> ChatResponse:
    """사용자의 질문을 받아 AI 답변을 반환합니다. ai-worker에 HTTP 요청."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{AI_WORKER_URL}/ask",
            json={
                "message": request.message,
                "medication_list": request.medication_list,
                "user_note": request.user_note,
            },
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="AI Worker 응답 오류")

    result = resp.json()

    await ChatLog.create(
        user_id=request.user_id,
        message_content=request.message,
        response_content=result["answer"],
        is_flagged=result["red_alert"],
    )

    return ChatResponse(**result)
