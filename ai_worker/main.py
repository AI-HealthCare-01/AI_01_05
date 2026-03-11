"""DodakTalk AI Worker — FastAPI 서버.

MedicationChatbot을 HTTP 엔드포인트로 노출한다.
fastapi 컨테이너가 httpx로 이 서버를 호출한다.
"""

import logging

from fastapi import FastAPI
from pydantic import BaseModel, Field

from ai_worker.tasks.chatbot_engine import MedicationChatbot

logger = logging.getLogger("ai_worker")
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")

app = FastAPI(title="DodakTalk AI Worker")
chatbot = MedicationChatbot()
logger.info("MedicationChatbot 로드 완료 (model=%s)", chatbot.model)


class AskRequest(BaseModel):
    message: str = Field(..., description="사용자 질문 메시지")
    medication_list: list[str] = Field(default_factory=list)
    user_note: str | None = Field(None)


@app.post("/ask")
async def ask(request: AskRequest) -> dict:
    return await chatbot.get_response(
        user_message=request.message,
        meds=request.medication_list,
        user_note=request.user_note,
    )
