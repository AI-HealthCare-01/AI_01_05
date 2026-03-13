import logging

from fastapi import APIRouter, HTTPException, status

from app.dtos.chat import ChatRequest, ChatResponse
from app.models.chat import ChatLog
from app.models.user_medication import UserMedication
from app.services.chatbot_service import MedicationChatbot

logger = logging.getLogger("dodaktalk.chatbot")

chatbot_router = APIRouter(prefix="/chat", tags=["chatbot"])

# 앱 시작 시 한 번만 초기화 (모듈 레벨 싱글턴)
_chatbot: MedicationChatbot | None = None


def _get_chatbot() -> MedicationChatbot:
    global _chatbot
    if _chatbot is None:
        _chatbot = MedicationChatbot()
    return _chatbot


@chatbot_router.post("/ask", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def ask_question(request: ChatRequest) -> ChatResponse:
    """사용자의 질문을 받아 AI 답변을 반환합니다."""
    try:
        chatbot = _get_chatbot()

        # DB에서 사용자 활성 복약 정보 자동 조회
        db_meds = await UserMedication.filter(
            user_id=request.user_id, status="ACTIVE"
        ).prefetch_related("medicine")

        # 약물명(API 검색용)과 복용량 정보 분리
        import re
        med_names = []      # API 검색용 (정제된 이름)
        med_dosages = []    # 복용량 포함 전체 정보
        for um in db_meds:
            if um.medicine:
                clean_name = re.sub(r'\s*\(.*', '', um.medicine.item_name).strip()
                med_names.append(clean_name)
                med_dosages.append(
                    f"{um.medicine.item_name} {um.dose_per_intake}정, 하루 {um.daily_frequency}회"
                )
        meds = med_names if med_names else request.medication_list

        result = await chatbot.get_response(
            user_message=request.message,
            meds=meds,
            med_dosages=med_dosages,
            user_note=request.user_note,
            character_id=request.character_id,
        )
    except ValueError as e:
        logger.error("Chatbot 초기화 실패: %s", e)
        raise HTTPException(status_code=500, detail="AI 서비스를 사용할 수 없습니다.") from e
    except Exception as e:
        logger.error("AI 응답 생성 실패: %s", e)
        raise HTTPException(status_code=502, detail="AI 응답 생성 중 오류가 발생했습니다.") from e

    await ChatLog.create(
        user_id=request.user_id,
        message_content=request.message,
        response_content=result["answer"],
        is_flagged=result["red_alert"],
    )

    return ChatResponse(**result)


@chatbot_router.get("/history", status_code=status.HTTP_200_OK)
async def get_chat_history(user_id: int) -> list[dict]:
    logs = await ChatLog.filter(user_id=user_id).order_by("-created_at").limit(20)
    return [
        {
            "id": log.id,
            "title": log.message_content[:30],
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]


@chatbot_router.get("/history/{log_id}", status_code=status.HTTP_200_OK)
async def get_chat_log(log_id: int) -> dict:
    log = await ChatLog.get_or_none(id=log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Not found")

    # 앞뒤 10개씩 가져오기
    before = await ChatLog.filter(user_id=log.user_id, id__lte=log_id).order_by("-id").limit(10)
    after = await ChatLog.filter(user_id=log.user_id, id__gt=log_id).order_by("id").limit(10)

    all_logs = list(reversed(before)) + list(after)
    return {
        "target_id": log_id,
        "messages": [
            {
                "id": l.id,
                "message_content": l.message_content,
                "response_content": l.response_content,
            }
            for l in all_logs
        ]
    }
