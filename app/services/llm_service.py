from __future__ import annotations

import json
from collections.abc import Iterable

import httpx

from app.core import config


class LlmService:
    async def summarize_chat(self, chat_texts: Iterable[str], entry_date: str) -> str:
        text = self._join_texts(chat_texts)
        if not text:
            return ""

        provider = (config.LLM_PROVIDER or "stub").lower()
        if provider == "stub":
            return self._stub_chat_summary(text=text, entry_date=entry_date)
        if provider == "openai":
            prompt = (
                "다음 사용자의 하루 기록을 3~4문장 한국어로 요약해줘. "
                "감정 변화와 복약 관련 단서를 포함하고, 과장 없이 간결하게 작성해.\n\n"
                f"날짜: {entry_date}\n"
                f"원문:\n{text}"
            )
            return await self._openai_chat_completion(prompt)
        return self._stub_chat_summary(text=text, entry_date=entry_date)

    async def summarize_report(self, diary_texts: Iterable[str], start_date: str, end_date: str) -> dict:
        text = self._join_texts(diary_texts)
        if not text:
            return {
                "summary": (
                    f"{start_date} ~ {end_date} 기간 동안의 기록이 충분하지 않아 "
                    "전체 요약을 생성하기 어렵습니다."
                ),
                "mood_summary": "기분 흐름을 파악할 수 있을 만큼의 기록이 아직 충분하지 않습니다.",
                "clinician_note": "기록 부족으로 해석에 제한이 있습니다.",
            }

        provider = (config.LLM_PROVIDER or "stub").lower()
        if provider == "stub":
            return self._stub_report_summary(text=text, start_date=start_date, end_date=end_date)
        if provider == "openai":
            prompt = (
                "다음 기간의 일기 기록을 바탕으로 감정 리포트를 작성해줘.\n"
                "사용자도 읽고, 의료진도 참고할 수 있도록 아래 3개 항목으로 나눠서 작성해.\n\n"
                "작성 원칙:\n"
                "- 기록에 없는 내용은 지어내지 말 것\n"
                "- 진단처럼 단정하지 말 것\n"
                "- 사용자용 문장은 부드럽고 자연스럽게 작성\n"
                "- 의료진 참고 문장은 짧고 관찰 중심으로 작성\n"
                "- 반드시 JSON 형식으로만 반환\n\n"
                f"기간: {start_date} ~ {end_date}\n"
                f"원문:\n{text}\n\n"
                '반환 형식:\n'
                '{'
                '"summary": "기간 전체 기록 요약 3~4문장", '
                '"mood_summary": "기분 흐름 요약 2~3문장", '
                '"clinician_note": "의료진 참고용 짧은 요약 1~2문장"'
                '}'
            )
            raw = await self._openai_chat_completion(prompt)

            try:
                parsed = json.loads(raw)
                return {
                    "summary": str(parsed.get("summary") or "").strip(),
                    "mood_summary": str(parsed.get("mood_summary") or "").strip(),
                    "clinician_note": str(parsed.get("clinician_note") or "").strip(),
                }
            except json.JSONDecodeError:
                return self._stub_report_summary(text=text, start_date=start_date, end_date=end_date)

        return self._stub_report_summary(text=text, start_date=start_date, end_date=end_date)

    async def summarize_chat_as_diary(self, conversation: str, entry_date: str) -> dict:
        """사용자가 직접 작성한 기록을 일기 형식(title + content)으로 정리한다."""
        provider = (config.LLM_PROVIDER or "stub").lower()
        if provider == "stub":
            return self._stub_diary_summary(conversation=conversation, entry_date=entry_date)
        if provider == "openai":
            prompt = (
                "아래는 정신건강 관리 앱 사용자가 오늘 직접 작성한 기록이야.\n"
                "이 내용을 바탕으로 사용자의 오늘 하루를 일기 형식으로 자연스럽게 정리해줘.\n\n"
                "반드시 아래 항목 중 기록에서 드러나는 내용을 자연스럽게 포함해:\n"
                "- 오늘의 기분 또는 감정 변화\n"
                "- 복약 관련 걱정, 메모, 부담감\n"
                "- 몸 상태나 건강 관련 우려\n"
                "- 오늘 있었던 주요 사건이나 생각\n"
                "- 전반적인 하루 컨디션이나 심리 상태\n\n"
                "작성 규칙:\n"
                "- 1인칭 일기체 (나는, 오늘은 등)\n"
                "- 따뜻하고 자연스러운 톤\n"
                "- 3~5문장, 읽기 편하게 작성\n"
                "- 제목은 오늘 하루를 대표하는 한 문장 (20자 이내)\n"
                "- 기록에 없는 내용을 지어내지 말 것\n\n"
                f"날짜: {entry_date}\n"
                f"기록 내용:\n{conversation}\n\n"
                '반드시 JSON 형식으로만 반환해줘 (마크다운 없이): {"title": "...", "content": "..."}'
            )
            raw = await self._openai_chat_completion(prompt)

            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {"title": "오늘의 기록", "content": raw}
        return self._stub_diary_summary(conversation=conversation, entry_date=entry_date)

    def _stub_diary_summary(self, conversation: str, entry_date: str) -> dict:
        preview = conversation.replace("\n", " ")[:200]
        return {"title": f"{entry_date} 기록", "content": f"오늘 작성한 기록 요약: {preview}"}

    async def generate_title(self, content: str) -> str:
        provider = (config.LLM_PROVIDER or "stub").lower()
        if provider == "stub":
            return self._stub_title(content)
        if provider == "openai":
            prompt = (
                "다음 일기 본문에 대해 한국어 제목을 12자 이내로 하나만 만들어줘. "
                "따옴표 없이 제목만 출력해.\n\n"
                f"본문:\n{content}"
            )
            return await self._openai_chat_completion(prompt)
        return self._stub_title(content)

    async def _openai_chat_completion(self, prompt: str) -> str:
        if not config.LLM_API_KEY:
            raise ValueError("LLM_NOT_CONFIGURED")

        headers = {
            "Authorization": f"Bearer {config.LLM_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": config.LLM_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "너는 정신건강 기록을 바탕으로 사용자가 읽기 쉬우면서도 "
                        "의료진이 참고할 수 있는 중립적 요약을 작성하는 도우미다."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
        }

        async with httpx.AsyncClient(timeout=config.LLM_TIMEOUT_SECONDS) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        message = (data.get("choices") or [{}])[0].get("message") or {}
        content = (message.get("content") or "").strip()
        if not content:
            raise ValueError("LLM_EMPTY_RESULT")
        return content

    def _join_texts(self, texts: Iterable[str]) -> str:
        merged = "\n".join(t.strip() for t in texts if t and t.strip()).strip()
        return merged[:4000]

    def _stub_chat_summary(self, text: str, entry_date: str) -> str:
        preview = text.replace("\n", " ")[:160]
        return f"{entry_date} 기록 요약: {preview}"

    def _stub_report_summary(self, text: str, start_date: str, end_date: str) -> dict:
        preview = text.replace("\n", " ")[:220]
        return {
            "summary": (
                f"{start_date} ~ {end_date} 기간 동안의 기록 요약입니다. "
                f"{preview}"
            ),
            "mood_summary": (
                "최근 기록에서는 감정의 오르내림이 나타났고, "
                "몸 상태나 갈등 상황이 기분 변화와 함께 언급되었습니다."
            ),
            "clinician_note": (
                "감정 변동성과 복약/신체 상태 관련 부담이 함께 기록됨."
            ),
        }

    def _stub_title(self, content: str) -> str:
        head = content.strip().split("\n", maxsplit=1)[0]
        if not head:
            return "오늘의 기록"
        return (head[:12]).strip() or "오늘의 기록"
