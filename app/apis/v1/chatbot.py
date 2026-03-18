import logging

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.dtos.chat import ChatRequest, ChatResponse
from app.models.chat import ChatLog
from app.models.medicine import Medicine
from app.models.user_medication import UserMedication
from app.models.users import User
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

        # 사용자 닉네임 조회
        user = await User.get_or_none(user_id=request.user_id)
        nickname = user.nickname if user else None

        # DB에서 사용자 활성 복약 정보 자동 조회
        db_meds = await UserMedication.filter(user_id=request.user_id, status="ACTIVE")

        # 약물명(API 검색용)과 복용량 정보 분리
        import re

        med_names = []  # API 검색용 (정제된 이름)
        med_dosages = []  # 복용량 포함 전체 정보
        for um in db_meds:
            # 직접 Medicine 조회 (prefetch_related 대신)
            medicine = await Medicine.get_or_none(item_seq=um.medicine_id)
            if not medicine:
                continue
            clean_name = re.sub(r"\s*\(.*", "", medicine.item_name).strip()
            med_names.append(clean_name)
            med_dosages.append(f"{medicine.item_name} {um.dose_per_intake}정, 하루 {um.daily_frequency}회")
        meds = med_names if med_names else request.medication_list

        result = await chatbot.get_response(
            user_message=request.message,
            meds=meds,
            med_dosages=med_dosages,
            user_note=request.user_note,
            character_id=request.character_id,
            nickname=nickname,
            chat_history=request.chat_history,
            message_count=request.message_count,
            last_message_time=request.last_message_time,
            user_id=request.user_id,
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
        is_flagged=result.get("is_flagged", False),
        red_alert=result.get("red_alert", False),
        reasoning=result.get("reasoning", ""),
    )

    return ChatResponse(**result)


def _parse_stream_chunk(chunk: str, state: dict) -> None:
    """스트림 청크에서 메타데이터를 추출하여 state 업데이트."""
    import json as _json

    if not chunk.startswith("data: ") or "[DONE]" in chunk:
        return
    try:
        data = _json.loads(chunk[6:].strip())
        if "token" in data:
            state["full_answer"] += data["token"]
        elif "answer" in data:
            state["full_answer"] = data["answer"]
        if "is_flagged" in data:
            state["is_flagged"] = data["is_flagged"]
        if "red_alert" in data:
            state["red_alert"] = data["red_alert"]
        if "reasoning" in data:
            state["reasoning"] = data["reasoning"]
    except Exception:
        pass


@chatbot_router.post("/ask/stream", status_code=status.HTTP_200_OK)
async def ask_question_stream(request: ChatRequest):
    """SSE 스트리밍으로 AI 답변을 실시간 전송합니다."""
    import re

    chatbot = _get_chatbot()

    user = await User.get_or_none(user_id=request.user_id)
    nickname = user.nickname if user else None

    db_meds = await UserMedication.filter(user_id=request.user_id, status="ACTIVE")

    med_names = []
    med_dosages = []
    for um in db_meds:
        medicine = await Medicine.get_or_none(item_seq=um.medicine_id)
        if not medicine:
            continue
        clean_name = re.sub(r"\s*\(.*", "", medicine.item_name).strip()
        med_names.append(clean_name)
        med_dosages.append(f"{medicine.item_name} {um.dose_per_intake}정, 하루 {um.daily_frequency}회")
    meds = med_names if med_names else request.medication_list

    async def event_generator():
        state = {"full_answer": "", "is_flagged": False, "red_alert": False, "reasoning": ""}

        async for chunk in chatbot.get_response_stream(
            user_message=request.message,
            meds=meds,
            med_dosages=med_dosages,
            user_note=request.user_note,
            character_id=request.character_id,
            nickname=nickname,
            chat_history=request.chat_history,
            message_count=request.message_count,
            last_message_time=request.last_message_time,
            user_id=request.user_id,
        ):
            _parse_stream_chunk(chunk, state)
            yield chunk

        if state["full_answer"]:
            from app.models.chat import ChatLog as _ChatLog

            await _ChatLog.create(
                user_id=request.user_id,
                message_content=request.message,
                response_content=state["full_answer"],
                is_flagged=state["is_flagged"],
                red_alert=state["red_alert"],
                reasoning=state["reasoning"],
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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
                "id": log.id,
                "message_content": log.message_content,
                "response_content": log.response_content,
            }
            for log in all_logs
        ],
    }
