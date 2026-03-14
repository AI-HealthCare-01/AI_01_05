import os
import re

from openai import AsyncOpenAI

from app.services.kfda_service import KFDAClient
from app.services.persona_service import get_persona_prompt
from app.services.pill_service import PillIdentifier
from app.services.rag_service import RAGService

CRISIS_KEYWORDS: dict[str, list[str]] = {
    "Direct": [
        "자살",
        "죽고 싶",
        "죽을래",
        "죽겠",
        "목숨",
        "유서",
        "목매",
        "투신",
        "손목을 긋",
        "극단적 선택",
        "스스로 목숨",
        "자해",
    ],
    "Indirect": [
        "사라지고 싶",
        "없어지고 싶",
        "살기 싫",
        "삶이 의미 없",
        "다 끝내고 싶",
        "더 이상 못 버티",
        "포기하고 싶",
        "힘들어서 못 살",
        "세상에 나 혼자",
        "아무도 나를",
    ],
    "Substance": [
        "약 많이 먹",
        "약을 한꺼번에",
        "약물 과다",
        "수면제 많이",
        "진통제 많이",
        "약으로 죽",
        "음독",
        "과량 복용",
    ],
}

CRISIS_RESPONSE_MESSAGE = (
    "지금 많이 힘드시군요. 당신의 이야기를 들어줄 전문가가 있습니다.\n\n"
    "▶ 자살예방상담전화: 1393 (24시간)\n"
    "▶ 정신건강위기상담전화: 1577-0199\n"
    "▶ 생명의전화: 1588-9191\n\n"
    "혼자 감당하지 마시고, 지금 바로 전화해 주세요."
)


def check_safety(text: str) -> dict | None:
    """사용자 메시지에서 위기 키워드를 감지합니다.

    Returns:
        위기 감지 시 {"alert_type": str, "keyword": str} 딕셔너리,
        감지되지 않으면 None.
    """
    normalized = text.replace(" ", "")
    for alert_type, keywords in CRISIS_KEYWORDS.items():
        for keyword in keywords:
            pattern = re.escape(keyword.replace(" ", ""))
            if re.search(pattern, normalized):
                return {"alert_type": alert_type, "keyword": keyword}
    return None


class MedicationChatbot:
    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.kfda = KFDAClient()
        self.pill = PillIdentifier()
        self.rag = RAGService()

    async def get_response(
        self,
        user_message: str,
        meds: list[str],
        med_dosages: list[str] | None = None,
        user_note: str | None = None,
        character_id: int | None = None,
    ) -> dict:
        """사용자 메시지를 분석하여 응답을 생성합니다.

        Returns:
            {"answer": str, "warning_level": str, "red_alert": bool, "alert_type": str | None}
        """
        # 1) 위기 키워드 체크 — 감지 시 OpenAI 호출 생략
        safety = check_safety(user_message)
        if safety is not None:
            return {
                "answer": CRISIS_RESPONSE_MESSAGE,
                "warning_level": "Critical",
                "red_alert": True,
                "alert_type": safety["alert_type"],
            }

        # 2) 정상 흐름: OpenAI 호출
        system_prompt = get_persona_prompt(character_id)

        # 낱알식별 키워드 감지
        pill_keywords = ["모르겠어", "무슨 약", "뭔지", "어떤 약", "알약", "모양", "색깔", "흰색", "노란색", "분홍색"]
        pill_context = ""
        if any(kw in user_message for kw in pill_keywords):
            color_map = {"흰색": "하양", "하얀": "하양", "노란색": "노랑", "분홍색": "분홍", "파란색": "파랑"}
            shape_map = {"타원형": "타원형", "원형": "원형", "동그란": "원형", "장방형": "장방형"}
            color = next((v for k, v in color_map.items() if k in user_message), None)
            shape = next((v for k, v in shape_map.items() if k in user_message), None)
            if color or shape:
                pill_results = await self.pill.search(color=color, shape=shape)
                if pill_results:
                    pill_context = "\n[낱알식별 검색 결과]\n" + self.pill.format_results(pill_results)

        # RAG 검색
        rag_results = await self.rag.search(user_message)
        rag_context = "\n".join(rag_results) if rag_results else ""

        user_content = f"복용 중인 약: {', '.join(meds) if meds else '없음'}"
        if rag_context:
            user_content += f"\n\n[의학 가이드라인]\n{rag_context}"
        if pill_context:
            user_content += pill_context
        if user_note:
            user_content += f"\n참고 사항: {user_note}"
        user_content += f"\n\n질문: {user_message}"

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.7,
                max_tokens=600,
            )
            answer = response.choices[0].message.content or "응답을 생성하지 못했습니다."
            return {
                "answer": answer,
                "warning_level": "Caution" if meds else "Normal",
                "red_alert": False,
                "alert_type": None,
            }
        except Exception as e:
            print(f"AI 호출 중 에러 발생: {e}")
            return {
                "answer": "죄송합니다. 답변을 생성하는 중에 문제가 발생했습니다.",
                "warning_level": "Normal",
                "red_alert": False,
                "alert_type": None,
            }
