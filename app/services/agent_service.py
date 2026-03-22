"""LangGraph ReAct Agent 서비스.

기존 직접 함수 호출 방식을 LangGraph ToolNode 패턴으로 교체.
LLM이 Pydantic Structured Output으로 위험도를 직접 판단.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Annotated

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from app.schemas.chat_response import LLMChatResponse
from app.services.persona_service import get_persona_prompt

logger = logging.getLogger("dodaktalk.agent")

# ── 설정 ────────────────────────────────────────────────────
MAX_ITERATIONS = 10
TIMEOUT_SECONDS = 60
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


# ── Tool 정의 (기존 함수 래핑) ─────────────────────────────────
@tool
def search_drug_info(query: str, top_k: int = 3) -> str:
    """약물의 효능, 용법용량, 주의사항, 이상반응, 외형 정보를 검색합니다.

    Args:
        query: 검색할 약물명, 증상, 또는 질문 내용
        top_k: 반환할 결과 수 (기본 3)
    """
    from app.services.drug_agent import search_drug_info as _search

    return _search(query, top_k)


@tool
def search_safety(query: str, top_k: int = 3) -> str:
    """DUR 안전 정보를 검색합니다 (병용금기, 임부금기, 노인주의, 용량주의 등).

    Args:
        query: 성분명, 약물 계열, 또는 안전 관련 질문
        top_k: 반환할 결과 수 (기본 3)
    """
    from app.services.drug_agent import search_safety as _search

    return _search(query, top_k)


@tool
def search_disease(query: str, top_k: int = 3) -> str:
    """질환명으로 ICD 상병분류기호(상병코드)를 검색합니다.

    Args:
        query: 질환명 또는 증상명
        top_k: 반환할 결과 수 (기본 3)
    """
    from app.services.drug_agent import search_disease as _search

    return _search(query, top_k)


@tool
def search_drug_meta(query: str, top_k: int = 5) -> str:
    """의약품허가정보에서 브랜드명↔성분명 매핑, ATC 약효군 분류, 마약류/희귀의약품 여부를 검색합니다.

    "타이레놀 성분", "판피린 주성분", "졸피뎀 분류" 같은 질문에 사용하세요.

    Args:
        query: 브랜드명, 성분명, 약효군, 또는 분류 관련 질문
        top_k: 반환할 결과 수 (기본 5)
    """
    from app.services.drug_agent import search_drug_meta as _search

    return _search(query, top_k)


@tool
def lookup_adverse(ingredient: str) -> str:
    """이상사례보고 데이터에서 성분명으로 부작용 코드를 조회합니다.

    Args:
        ingredient: 한글 성분명 (예: 아세트아미노펜, 이부프로펜)
    """
    from app.services.drug_agent import lookup_adverse as _lookup

    return _lookup(ingredient)


_main_loop: asyncio.AbstractEventLoop | None = None


def set_main_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _main_loop
    _main_loop = loop


def _run_async(coro):
    """동기 컨텍스트에서 비동기 코루틴 실행 (Tortoise ORM 호환)."""
    if _main_loop is not None and _main_loop.is_running():
        future = asyncio.run_coroutine_threadsafe(coro, _main_loop)
        return future.result(timeout=60)
    return asyncio.run(coro)


@tool
def search_food_drug_sync(query: str, user_drugs_json: str) -> str:
    """음식-약물 상호작용을 검색합니다.

    Args:
        query: 사용자 질문 (음식 관련 키워드 포함)
        user_drugs_json: 사용자가 복용 중인 약물 목록 (JSON 문자열)
    """
    from app.services.food_drug_service import search_food_drug as _search

    user_drugs = json.loads(user_drugs_json) if user_drugs_json else []
    return _run_async(_search(query, user_drugs))


@tool
def search_rag_sync(query: str, n_results: int = 3) -> str:
    """의학 가이드라인을 벡터 검색합니다.

    Args:
        query: 검색 쿼리
        n_results: 반환할 결과 수
    """
    from app.services.rag_service import RAGService

    async def _search():
        rag = RAGService()
        results = await rag.search(query, n_results)
        return "\n".join(results) if results else "관련 가이드라인 없음"

    return _run_async(_search())


@tool
def get_drug_interactions_sync(drug_names_json: str) -> str:
    """Neo4j에서 약물 상호작용 정보를 조회합니다.

    Args:
        drug_names_json: 조회할 약물명 목록 (JSON 문자열)
    """
    from app.services.graph_service import get_graph_service

    drug_names = json.loads(drug_names_json) if drug_names_json else []

    async def _get():
        graph = await get_graph_service()
        return await graph.get_drug_interactions(drug_names)

    return _run_async(_get())


@tool
def query_knowledge_graph(query_drug: str, user_drugs_json: str) -> str:
    """Neo4j 지식그래프에서 약물 상호작용을 검색합니다.

    질문에 언급된 약물과 사용자 복용약 간 DANGER/CAUTION 상호작용을 찾습니다.
    DANGER 발견 시 red_alert=True로 설정해야 합니다.

    Args:
        query_drug: 질문에 언급된 약물 (예: "졸피뎀", "술", "알코올", "리튬")
        user_drugs_json: 사용자 복용 중인 약물 목록 (JSON 문자열, 예: '["리스페리돈", "올란자핀"]')

    Returns:
        상호작용 검색 결과. DANGER 발견 시 명시적 경고 포함.
    """
    from app.services.graph_service import get_graph_service

    user_drugs = json.loads(user_drugs_json) if user_drugs_json else []

    # "술" → "알코올"로 정규화
    query_normalized = query_drug
    alcohol_aliases = ["술", "음주", "맥주", "소주", "와인", "알콜"]
    if any(alias in query_drug for alias in alcohol_aliases):
        query_normalized = "알코올"

    async def _search():
        graph = await get_graph_service()
        result = await graph.search_interaction(query_normalized, user_drugs)
        return await graph.format_interaction_result(result), result

    formatted, result = _run_async(_search())

    # DANGER 발견 시 명시적 경고 추가
    if result["has_danger"]:
        return (
            f"🚨 [DANGER 상호작용 발견] red_alert=True 필수!\n\n"
            f"{formatted}\n\n"
            f"⚠️ 이 조합은 생명을 위협할 수 있습니다. "
            f"반드시 answer에 구체적인 위험 내용을 포함하고 red_alert=True로 설정하세요."
        )
    elif result["has_caution"]:
        return f"⚠️ [CAUTION 상호작용 발견]\n\n{formatted}"
    elif not formatted:
        return f"'{query_drug}'와 사용자 복용약 간 알려진 상호작용 없음. 의사/약사 상담 권장."
    return formatted


@tool
def check_all_drug_combinations(drugs_json: str) -> str:
    """사용자 복용약 전체 목록의 상호작용을 교차 검사합니다.

    모든 약물 쌍에 대해 DANGER/CAUTION 상호작용을 검색합니다.

    Args:
        drugs_json: 검사할 약물 목록 (JSON 문자열, 예: '["리스페리돈", "졸피뎀", "알코올"]')

    Returns:
        발견된 모든 상호작용 목록. DANGER 발견 시 명시적 경고 포함.
    """
    from app.services.graph_service import get_graph_service

    drugs = json.loads(drugs_json) if drugs_json else []

    async def _check():
        graph = await get_graph_service()
        result = await graph.check_drug_combination(drugs)
        return await graph.format_interaction_result(result), result

    formatted, result = _run_async(_check())

    if result["has_danger"]:
        return (
            f"🚨 [DANGER 상호작용 발견] red_alert=True 필수!\n\n"
            f"{formatted}\n\n"
            f"⚠️ 위험한 약물 조합이 발견되었습니다. "
            f"반드시 answer에 구체적인 위험 내용을 포함하고 red_alert=True로 설정하세요."
        )
    elif result["has_caution"]:
        return f"⚠️ [CAUTION 상호작용 발견]\n\n{formatted}"
    elif not formatted:
        return "복용 중인 약물 간 알려진 상호작용 없음."
    return formatted


@tool
def get_user_medicines_sync(user_id: int) -> str:
    """DB에서 사용자의 복용약 목록과 복용 스케줄을 조회합니다.

    Args:
        user_id: 사용자 ID

    Returns:
        복용약 목록 + 복용 시간대 정보
    """
    from app.models.medicine import Medicine
    from app.models.user_medication import UserMedication
    from app.services.medication_schedule_service import format_schedule_text

    async def _get():
        meds = await UserMedication.filter(user_id=user_id, status="ACTIVE")
        if not meds:
            return "복용 중인 약 없음"

        # 기본 복용약 목록
        med_list = ["[복용 중인 약물]"]
        for um in meds:
            # 직접 Medicine 조회 (prefetch_related 대신)
            medicine = await Medicine.get_or_none(item_seq=um.medicine_id)
            if not medicine:
                continue
            time_slots = um.time_slots or []
            time_info = ", ".join(time_slots) if time_slots else "시간 미지정"
            med_list.append(
                f"- {medicine.item_name}: {um.dose_per_intake}정, 하루 {um.daily_frequency}회 ({time_info})"
            )

        # 복용 스케줄 현황 추가
        schedule_text = await format_schedule_text(user_id)
        if schedule_text:
            med_list.append("")
            med_list.append(schedule_text)

        return "\n".join(med_list)

    return _run_async(_get())


@tool
def get_medication_schedule_sync(user_id: int) -> str:
    """사용자의 오늘 복용 스케줄을 조회합니다.

    현재 시간 기준으로 복용 예정, 복용 시간 지남, 다음 복용 시간 정보를 반환합니다.
    "약 먹을 시간", "언제 먹어", "복용 시간" 등의 질문에 사용하세요.

    Args:
        user_id: 사용자 ID

    Returns:
        오늘 전체 복용 스케줄 (시간대별 정리)
    """
    from app.services.medication_schedule_service import get_full_schedule_text

    return _run_async(get_full_schedule_text(user_id))


# ── Agent State 정의 ─────────────────────────────────────────
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    iteration_count: int
    user_drugs: list[str]


# ── System Prompt ─────────────────────────────────────────────
AGENT_SYSTEM_PROMPT = """AI 약사 어시스턴트입니다. 안전 판단이 최우선입니다.

## 도구 사용 (필요한 경우만)
- 약물 조합/상호작용 질문 → query_knowledge_graph
- 복용 시간 질문 → get_medication_schedule_sync
- 약 효능/부작용/용법 질문 → search_drug_info
- 브랜드명↔성분명, "XX 주성분", ATC분류 → search_drug_meta
- 병용금기/임부금기/노인주의 → search_safety
- 질환명/상병코드 질문 → search_disease
- 음식-약물 질문 → search_food_drug_sync
- 성분 부작용 통계 → lookup_adverse

⚡ 도구 없이 답변 가능하면 바로 답변하세요. 도구는 최대 1-2개만 호출.

## 주성분/성분 질문 응답 규칙
"XX 주성분", "XX 성분이 뭐야" 질문 시 search_drug_meta 결과에서:
- 같은 브랜드명으로 여러 제품이 있으면 최대 4개까지 각각 정리
- 제품명과 주성분 목록을 번호로 나열
- 예시:
  1. 판피린티정: 아세트아미노펜, 카페인무수물, 클로르페니라민말레산염
  2. 판피린큐액: 아세트아미노펜, dl-메틸에페드린염산염, ...
  3. 판피린에이액: ...

## 안전 기준
- 위기 표현(자살, 자해) → is_flagged=true
- DANGER 상호작용 → red_alert=true
- 알코올+진정제 조합 → red_alert=true

{persona_prompt}

## 응답 형식 (JSON만)
```json
{{"answer": "답변", "is_flagged": false, "red_alert": false, "reasoning": "근거"}}
```"""


# ── LangGraph Agent 구성 ─────────────────────────────────────
ALL_TOOLS = [
    search_drug_info,
    search_safety,
    search_disease,
    search_drug_meta,
    lookup_adverse,
    search_food_drug_sync,
    search_rag_sync,
    get_drug_interactions_sync,
    get_user_medicines_sync,
    get_medication_schedule_sync,
    query_knowledge_graph,
    check_all_drug_combinations,
]


def create_agent(character_id: int | None = None) -> StateGraph:
    """LangGraph ReAct Agent 생성."""
    persona_prompt = get_persona_prompt(character_id)
    system_prompt = AGENT_SYSTEM_PROMPT.format(persona_prompt=persona_prompt)

    llm = ChatOpenAI(
        model=MODEL_NAME,
        temperature=0.7,
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    tool_node = ToolNode(ALL_TOOLS)

    def agent_node(state: AgentState) -> dict:
        """Agent 노드: LLM 호출."""
        messages = state["messages"]
        iteration = state.get("iteration_count", 0)

        if iteration >= MAX_ITERATIONS:
            return {
                "messages": [
                    AIMessage(
                        content=json.dumps(
                            {
                                "answer": "처리 시간이 초과되었습니다. 다시 시도해 주세요.",
                                "is_flagged": False,
                                "red_alert": False,
                                "reasoning": "max_iterations 초과",
                            },
                            ensure_ascii=False,
                        )
                    )
                ],
                "iteration_count": iteration + 1,
            }

        # System prompt가 없으면 추가
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=system_prompt)] + list(messages)

        response = llm_with_tools.invoke(messages)
        return {
            "messages": [response],
            "iteration_count": iteration + 1,
        }

    def should_continue(state: AgentState) -> str:
        """도구 호출 여부 판단."""
        messages = state["messages"]
        last_message = messages[-1]

        if state.get("iteration_count", 0) >= MAX_ITERATIONS:
            return END

        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"

        return END

    # Graph 구성
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)

    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile()


def parse_llm_response(content: str) -> LLMChatResponse:
    """LLM 응답에서 JSON 파싱하여 LLMChatResponse 반환."""
    try:
        # JSON 블록 추출 시도
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            json_str = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            json_str = content[start:end].strip()
        elif content.strip().startswith("{"):
            json_str = content.strip()
        else:
            # JSON 형식이 아니면 answer로 사용
            return LLMChatResponse(
                answer=content,
                is_flagged=False,
                red_alert=False,
                reasoning="비구조화 응답",
            )

        data = json.loads(json_str)
        return LLMChatResponse.model_validate(data)

    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("LLM 응답 파싱 실패: %s", e)
        return LLMChatResponse.safe_default(answer=content if content else "응답 생성 실패")


def _build_agent_context(
    user_message: str,
    user_drugs: list[str],
    nickname: str | None,
    intimacy: str,
    user_id: int | None,
) -> str:
    """Agent용 컨텍스트 문자열 생성."""
    context_parts = [f"[친밀도: {intimacy}]"]
    if user_id:
        context_parts.append(f"[사용자 ID: {user_id}]")
    if nickname and intimacy == "formal":
        context_parts.append(f"사용자 닉네임: {nickname}")
    if user_drugs:
        context_parts.append(f"복용 중인 약: {', '.join(user_drugs)}")
    context_parts.append(f"\n질문: {user_message}")
    return "\n".join(context_parts)


def _convert_chat_history(chat_history: list[dict] | None) -> list:
    """대화 히스토리를 LangChain 메시지로 변환."""
    messages = []
    if chat_history:
        for entry in chat_history[-10:]:
            role = entry.get("role", "user")
            content = entry.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
    return messages


async def run_agent(
    user_message: str,
    user_drugs: list[str],
    character_id: int | None = None,
    nickname: str | None = None,
    chat_history: list[dict] | None = None,
    message_count: int = 0,
    intimacy: str = "formal",
    user_id: int | None = None,
) -> LLMChatResponse:
    """Agent 실행 및 LLMChatResponse 반환."""
    agent = create_agent(character_id)

    user_content = _build_agent_context(user_message, user_drugs, nickname, intimacy, user_id)
    messages = _convert_chat_history(chat_history)
    messages.append(HumanMessage(content=user_content))

    initial_state: AgentState = {
        "messages": messages,
        "iteration_count": 0,
        "user_drugs": user_drugs,
    }

    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(agent.invoke, initial_state),
            timeout=TIMEOUT_SECONDS,
        )

        final_messages = result.get("messages", [])
        for msg in reversed(final_messages):
            if isinstance(msg, AIMessage) and msg.content:
                return parse_llm_response(msg.content)

        return LLMChatResponse.safe_default()

    except TimeoutError:
        logger.error("Agent 실행 타임아웃 (%ds)", TIMEOUT_SECONDS)
        return LLMChatResponse.safe_default(answer="응답 시간이 초과되었습니다. 다시 시도해 주세요.")
    except Exception as e:
        logger.error("Agent 실행 실패: %s", e)
        return LLMChatResponse.safe_default()


def _get_tool_status_message(tool_name: str) -> str:
    """도구 이름에 따른 상태 메시지 반환."""
    status_map = {
        "search_drug_info": "약 정보 검색 중...",
        "search_safety": "안전성 정보 확인 중...",
        "search_disease": "질환 정보 검색 중...",
        "search_drug_meta": "의약품 허가정보 검색 중...",
        "lookup_adverse": "이상사례 정보 조회 중...",
        "search_food_drug_sync": "음식-약물 상호작용 확인 중...",
        "search_rag_sync": "의학 가이드라인 검색 중...",
        "get_drug_interactions_sync": "약물 상호작용 확인 중...",
        "query_knowledge_graph": "지식그래프 검색 중...",
        "check_all_drug_combinations": "약물 조합 검사 중...",
        "get_user_medicines_sync": "복용약 정보 조회 중...",
        "get_medication_schedule_sync": "복용 스케줄 조회 중...",
    }
    return status_map.get(tool_name, "정보 검색 중...")


async def run_agent_stream(
    user_message: str,
    user_drugs: list[str],
    character_id: int | None = None,
    nickname: str | None = None,
    chat_history: list[dict] | None = None,
    message_count: int = 0,
    intimacy: str = "formal",
    user_id: int | None = None,
):
    """Agent 스트리밍 실행 - SSE용 async generator.

    도구 호출 시 상태 메시지 전송 후 응답 스트리밍.
    """
    # 상태 메시지 먼저 전송 (도구 호출 예상)
    yield json.dumps({"status": "정보 검색 중..."}, ensure_ascii=False)

    # Agent 실행 (기존 안정적인 방식 사용)
    response = await run_agent(
        user_message=user_message,
        user_drugs=user_drugs,
        character_id=character_id,
        nickname=nickname,
        chat_history=chat_history,
        message_count=message_count,
        user_id=user_id,
        intimacy=intimacy,
    )

    # 답변을 청크로 분할하여 스트리밍
    answer = response.answer
    chunk_size = 5  # 더 작은 청크로 자연스러운 타이핑

    for i in range(0, len(answer), chunk_size):
        chunk = answer[i : i + chunk_size]
        yield json.dumps({"token": chunk}, ensure_ascii=False)

        # 진행률에 따른 타이핑 속도 조절 (천천히)
        progress = i / len(answer) if answer else 0
        if progress < 0.1:
            delay = 0.02  # 시작 (처음 10%)
        elif progress < 0.4:
            delay = 0.05  # 천천히 타이핑 (10~40%)
        elif progress < 0.7:
            delay = 0.03  # 중간 속도 (40~70%)
        else:
            delay = 0.05  # 마무리 천천히 (70~100%)

        await asyncio.sleep(delay)

    # 최종 메타데이터 전송
    yield json.dumps(
        {
            "warning_level": "Critical" if response.is_flagged else ("Caution" if response.red_alert else "Normal"),
            "red_alert": response.red_alert,
            "is_flagged": response.is_flagged,
            "alert_type": "Direct" if response.is_flagged else None,
            "reasoning": response.reasoning,
        },
        ensure_ascii=False,
    )


# ── 레거시 호환 ─────────────────────────────────────────────
class AgentService:
    """레거시 호환용 클래스. 새 코드는 run_agent() 사용 권장."""

    async def get_response(
        self,
        user_message: str,
        meds: list[str],
        med_dosages: list[str],
        system_prompt: str,
        character_id: int | None = None,
        nickname: str | None = None,
    ) -> str:
        response = await run_agent(
            user_message=user_message,
            user_drugs=meds,
            character_id=character_id,
            nickname=nickname,
        )
        return response.answer


_agent_service: AgentService | None = None


def get_agent_service() -> AgentService:
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
    return _agent_service
