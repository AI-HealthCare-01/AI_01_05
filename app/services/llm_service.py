from __future__ import annotations

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
                "다음 사용자의 하루 대화/기록을 3~4문장 한국어로 요약해줘. "
                "감정 변화와 복약 관련 단서를 포함하고, 과장 없이 간결하게 작성해.\n\n"
                f"날짜: {entry_date}\n"
                f"원문:\n{text}"
            )
            return await self._openai_chat_completion(prompt)
        return self._stub_chat_summary(text=text, entry_date=entry_date)

    async def summarize_report(self, diary_texts: Iterable[str], start_date: str, end_date: str) -> str:
        text = self._join_texts(diary_texts)
        if not text:
            return f"======= 리포트 요약 데이터 =======\n{start_date}부터 {end_date}까지 기록이 충분하지 않습니다."

        provider = (config.LLM_PROVIDER or "stub").lower()
        if provider == "stub":
            return self._stub_report_summary(text=text, start_date=start_date, end_date=end_date)
        if provider == "openai":
            prompt = (
                "다음 기간의 일기 기록을 의료 관찰용으로 간단 요약해줘. "
                "핵심 변화, 기분 흐름, 복약 관련 단서를 4~6줄로 정리해.\n\n"
                f"기간: {start_date} ~ {end_date}\n"
                f"원문:\n{text}"
            )
            summary = await self._openai_chat_completion(prompt)
            return f"======= 리포트 요약 데이터 =======\n{summary}"
        return self._stub_report_summary(text=text, start_date=start_date, end_date=end_date)

    async def summarize_chat_as_diary(self, conversation: str, entry_date: str) -> dict:
        """챗봇 대화 내역을 일기 형식(title + content)으로 요약한다."""
        provider = (config.LLM_PROVIDER or "stub").lower()
        if provider == "stub":
            return self._stub_diary_summary(conversation=conversation, entry_date=entry_date)
        if provider == "openai":
            prompt = (
                "아래는 정신건강 관리 앱을 사용하는 사용자가 오늘 강아지 챗봇 약사와 나눈 대화야.\n"
                "이 대화를 바탕으로 사용자의 오늘 하루를 일기 형식으로 따뜻하게 정리해줘.\n\n"
                "반드시 아래 항목 중 대화에서 언급된 내용을 자연스럽게 포함해:\n"
                "- 오늘의 기분 또는 감정 변화\n"
                "- 복용 중인 약물이나 복약 관련 질문/걱정\n"
                "- 부작용, 약물 상호작용 등 건강 관련 우려\n"
                "- 사용자가 궁금해했거나 알게 된 점\n"
                "- 전반적인 하루 컨디션이나 심리 상태\n\n"
                "작성 규칙:\n"
                "- 1인칭 일기체 (나는, 오늘은 등)\n"
                "- 따뜻하고 공감적인 톤\n"
                "- 3~5문장, 자연스럽고 읽기 편하게\n"
                "- 제목은 오늘 하루를 대표하는 한 문장 (20자 이내)\n\n"
                f"날짜: {entry_date}\n"
                f"대화 내용:\n{conversation}\n\n"
                '반드시 JSON 형식으로만 반환해줘 (마크다운 없이): {"title": "...", "content": "..."}'
            )
            raw = await self._openai_chat_completion(prompt)
            import json

            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {"title": "오늘의 기록", "content": raw}
        return self._stub_diary_summary(conversation=conversation, entry_date=entry_date)

    def _stub_diary_summary(self, conversation: str, entry_date: str) -> dict:
        preview = conversation.replace("\n", " ")[:200]
        return {"title": f"{entry_date} 대화 일기", "content": f"오늘 챗봇과 대화한 내용: {preview}"}

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
                {"role": "system", "content": "너는 의료기록 보조 요약 도우미다."},
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
        return f"{entry_date} 대화 요약: {preview}"

    def _stub_report_summary(self, text: str, start_date: str, end_date: str) -> str:
        preview = text.replace("\n", " ")[:200]
        return (
            f"======= 리포트 요약 데이터 =======\n{start_date}부터 {end_date}까지의 요약입니다.\n핵심 기록: {preview}"
        )

    def _stub_title(self, content: str) -> str:
        head = content.strip().split("\n", maxsplit=1)[0]
        if not head:
            return "오늘의 기록"
        return (head[:12]).strip() or "오늘의 기록"
