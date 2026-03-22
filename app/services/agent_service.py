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

## 🚨 절대 규칙: 반드시 Tool을 먼저 호출하라
- 약물 관련 질문에는 **자체 지식만으로 답변 절대 금지**
- 반드시 아래 도구를 먼저 호출한 후, **Tool 결과 데이터만** 사용하여 답변할 것
- Tool 호출 없이 "~입니다", "~알려드릴게요" 같은 답변 금지
- Tool 결과에 없는 정보를 지어내지 마라. 결과가 부족하면 "확인되지 않았습니다"라고 답해라

## 도구 선택 가이드 (정확히 따를 것)

| 질문 패턴 | 사용할 Tool |
|-----------|------------|
| "XX 주성분", "XX 성분이 뭐야", "XX 뭐로 만들어" | **search_drug_meta** (필수) |
| 약 외형/색상/각인/모양 ("흰색", "GM 각인", "동그란 약") | **search_drug_info** (필수! 낱알식별 데이터에 외형정보 있음) |
| 브랜드명↔성분명 매핑, ATC 분류 | **search_drug_meta** |
| 약물 효능/용법/용량/이상반응 일반 질문 | search_drug_info |
| **임산부/임부/수유부** + 약물 | **search_safety** (필수! 최우선!) |
| 병용금기/노인주의/용량주의 | search_safety |
| 약물 조합/상호작용 | query_knowledge_graph |
| 음식+약물 ("술", "자몽", "우유") | search_food_drug_sync |
| 복용 시간/스케줄 | get_medication_schedule_sync |
| 질환명/상병코드 | search_disease |

## 음식-약물 상호작용 응답 규칙
"XX랑 XX 같이 먹어도 돼?" 패턴에서 음식(자몽, 우유, 술 등)이 포함되면:
1. search_food_drug_sync를 호출하고, 추가로 search_drug_info도 호출하여 해당 약물의 주의사항에서 음식 관련 정보를 찾아라
2. Tool 결과를 바탕으로 **구체적인 상호작용 메커니즘**을 설명하라
   - 예: "자몽주스는 CYP3A4 효소를 억제하여 약물 혈중 농도를 높일 수 있습니다"
3. "주의가 필요합니다"로만 끝내지 말고, 어떤 위험이 있는지, 시간 간격을 두면 되는지 등 실질적 조언을 포함하라

## 주성분/성분 질문 응답 규칙 (매우 중요)
"XX 주성분", "XX 성분이 뭐야" 질문 시:
1. 반드시 **search_drug_meta**를 호출하라 (search_drug_info 아님!)
2. Tool 결과에서 같은 브랜드명으로 여러 제품이 있으면 **전부 나열** (최대 4~5개)
3. 각 제품별로 제품명을 볼드로 쓰고, 성분은 **한 줄에 하나씩** - 기호로 나열
4. 필수 형식:

[브랜드]의 주성분은 다음과 같습니다:

1. **판피린티정**:
   - 아세트아미노펜
   - 카페인무수물
   - 클로르페니라민말레산염

2. **판피린큐액**:
   - 아세트아미노펜
   - dl-메틸에페드린염산염
   - 티페피딘시트르산염
   - 구아이페네신
   - 카페인무수물
   - 클로르페니라민말레산염

[마무리 문장]

5. 성분을 쉼표(,)로 한 줄에 나열하지 마라. 반드시 줄바꿈하여 - 기호로 하나씩 나열

## 약 외형/각인 질문 응답 규칙
"흰색에 XX라고 적힌 약", "동그란 하얀 약" 등 외형 질문 시:
1. 반드시 **search_drug_info**를 호출하라 (낱알식별 데이터에 색상/각인/모양 정보가 있음)
2. 검색 쿼리에 색상+각인을 포함하라
   - 예: 사용자가 "흰색에 GM 적힌 약"이라고 하면 → search_drug_info(query="하양색 GM", top_k=5)
3. 주사제, 주사액, 앰플, 바이알 결과는 제외하고 정제/캡슐/연질캡슐만 답변에 포함
4. Tool 결과에서 매칭되는 약물의 제품명, 약효분류, 제조사, 외형 특징을 구체적으로 나열
5. 결과가 여러 개면 전부 번호 매겨서 나열
6. 결과가 부정확하거나 부족하면, 사용자에게 추가 정보를 요청하라:
   - "혹시 약의 모양(원형, 타원형, 장방형)도 알 수 있을까요?"
   - "분할선이 있나요?"

## 🚫 임부/임산부 관련 규칙 (절대 규칙)
임산부/임부/수유부가 약물 복용을 물어보면:
1. **반드시 search_safety를 호출**하여 임부금기 여부를 확인하라
2. Tool 결과를 바탕으로 **구체적인 위험성**을 설명하라 (예: 태아 기형, 조산 위험 등)
3. **절대로 "의사와 상담하세요"로만 끝내지 마라** — 먼저 위험성을 명확히 경고한 후 상담을 권유
4. 임부금기 약물 응답 톤 예시:
   "⚠️ 졸피뎀(스틸녹스)은 임산부 금기 약물입니다.
   태반을 통과하여 태아에게 영향을 줄 수 있으며, 신생아에게 호흡 억제, 저체온, 근긴장 저하 등의
   위험이 보고되어 있습니다.
   임신 중에는 절대 복용하지 마시고, 반드시 담당 의사와 상의하여 안전한 대안을 찾으세요."
5. **red_alert=true 필수 설정**
6. "충분한 연구가 이루어지지 않았기 때문에" 같은 애매한 표현 금지 → 구체적 위험을 말하라

## 답변 포맷팅 규칙 (최우선 - 절대 어기지 마라)

### 핵심 규칙: 목록의 마지막 항목 다음에 반드시 빈 줄 2개(\\n\\n)를 넣어라

모든 목록형 답변은 아래 구조를 정확히 따라라:
---
[도입 문장]\\n\\n
[항목 1]\\n\\n
[항목 2]\\n\\n
...
[마지막 항목]\\n\\n
[요약/설명 문장]\\n\\n
[마무리 인사]
---

### 금지 패턴 (이렇게 쓰면 안 됨):
"4. 판피린에이액: 아세트아미노펜, ..., 클로르페니라민말레산염\\n각 제품마다 주성분이 다르니 참고하세요!"

→ 마지막 항목에 마무리가 바로 붙어있음. 절대 금지!

### 필수 패턴 (반드시 이렇게):
"4. 판피린에이액: 아세트아미노펜, ..., 클로르페니라민말레산염\\n\\n각 제품마다 주성분이 다르므로, 필요에 따라 선택하시면 됩니다.\\n\\n더 궁금한 점이 있으면 언제든지 말씀해 주세요!"

→ 항목 뒤 빈 줄, 설명 뒤 빈 줄, 인사 순서

### answer 문자열에서 \\n\\n 사용을 두려워하지 마라. 빈 줄이 많아도 괜찮다.

## 안전 기준
- 위기 표현(자살, 자해) → is_flagged=true
- DANGER 상호작용 → red_alert=true
- 알코올+진정제 조합 → red_alert=true
- 임부금기 약물 → red_alert=true

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
    # 첫 번째 호출: Tool 사용 강제 (tool_choice="required")
    llm_force_tools = llm.bind_tools(ALL_TOOLS, tool_choice="required")
    # 후속 호출: Tool 선택적 (tool_choice="auto")
    llm_with_tools = llm.bind_tools(ALL_TOOLS, tool_choice="auto")

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

        # 첫 번째 호출은 Tool 강제, 이후는 선택적
        llm_to_use = llm_force_tools if iteration == 0 else llm_with_tools
        response = llm_to_use.invoke(messages)
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


def _fix_answer_formatting(answer: str) -> str:
    """목록 마지막 항목 뒤에 빈 줄이 없으면 강제로 추가하는 후처리.

    LLM이 "5. 판피린에이액: 성분들 각 제품마다 주성분이..." 처럼
    같은 줄에 목록 항목과 마무리 문장을 붙여서 보내는 경우도 처리한다.
    """
    import re

    if not answer:
        return answer

    # 1단계: 마무리 문장 패턴 앞에 빈 줄 삽입 (같은 줄에 붙어있는 경우)
    # 이 패턴들이 목록 항목 텍스트 바로 뒤에 공백 하나로 붙어있는 경우를 잡음
    closing_patterns = [
        r"(?<=[다요죠임됨음]) (각 제품마다)",
        r"(?<=[다요죠임됨음]) (이 정보가 도움)",
        r"(?<=[다요죠임됨음]) (더 궁금한 점)",
        r"(?<=[다요죠임됨음]) (궁금한 점이)",
        r"(?<=[다요죠임됨음]) (혹시 약의 모양)",
        r"(?<=[다요죠임됨음]) (추가로 궁금)",
        r"(?<=[다요죠임됨음]) (필요한 정보가)",
        r"(?<=[다요죠임됨음]) (이외에도)",
        r"(?<=[다요죠임됨음]) (위 약물들은)",
        r"(?<=[다요죠임됨음]) (아세트아미노펜은)",
        r"(?<=[다요죠임됨음]) (따라서)",
        r"(?<=[다요죠임됨음]) (이 약물)",
        r"(?<=[다요죠임됨음]) (해당 약물)",
    ]

    for pattern in closing_patterns:
        answer = re.sub(pattern, r"\n\n\1", answer)

    # 2단계: 줄 단위로 처리 - 목록 항목 뒤에 일반 텍스트가 오면 빈 줄 삽입
    lines = answer.split("\n")
    result = []

    for i, line in enumerate(lines):
        result.append(line)

        if i < len(lines) - 1:
            current_stripped = line.strip()
            next_stripped = lines[i + 1].strip()

            # 현재 줄이 번호 목록 항목인지 (1. 2. 3. 등)
            is_current_numbered = bool(re.match(r"^\d+[\.\)]\s", current_stripped))

            # 현재 줄이 하위 항목(- 또는 *)인지
            is_current_sub = bool(re.match(r"^[-*]\s", current_stripped))

            # 다음 줄이 하위 항목(- 또는 *)인지
            is_next_sub = bool(re.match(r"^[-*]\s", next_stripped))

            # 다음 줄이 빈 줄이 아니고, 목록도 아닌 일반 텍스트인지
            is_next_normal = (
                next_stripped
                and not re.match(r"^(\d+[\.\)]\s|[-*]\s)", next_stripped)
                and not next_stripped.startswith("#")
            )

            # 하위 항목(-) 뒤에 다음 하위 항목(-)이 오면 → 빈 줄 넣지 않음
            if is_current_sub and is_next_sub:
                continue

            # 번호 목록 항목 뒤에 일반 텍스트가 오면 빈 줄 삽입
            if is_current_numbered and is_next_normal:
                result.append("")

            # 하위 항목(-) 뒤에 일반 텍스트(마무리 문장)가 오면 빈 줄 삽입
            if is_current_sub and is_next_normal:
                result.append("")

    # 3단계: 하위 항목(-) 사이의 불필요한 빈 줄 제거
    # LLM이 "- 아세트아미노펜\n\n- 카페인무수물" 처럼 빈 줄을 넣는 경우 정리
    cleaned = "\n".join(result)
    # - 항목과 - 항목 사이의 빈 줄(들)을 단일 줄바꿈으로 축소
    cleaned = re.sub(r"(\n\s*-\s[^\n]+)\n\n+(\s*-\s)", r"\1\n\2", cleaned)
    return cleaned


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
                answer=_fix_answer_formatting(content),
                is_flagged=False,
                red_alert=False,
                reasoning="비구조화 응답",
            )

        data = json.loads(json_str)
        if "answer" in data:
            data["answer"] = _fix_answer_formatting(data["answer"])
        return LLMChatResponse.model_validate(data)

    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("LLM 응답 파싱 실패: %s", e)
        return LLMChatResponse.safe_default(answer=_fix_answer_formatting(content) if content else "응답 생성 실패")


def _build_agent_context(  # noqa: C901
    user_message: str,
    user_drugs: list[str],
    nickname: str | None,
    intimacy: str,
    user_id: int | None,
) -> str:
    """Agent용 컨텍스트 문자열 생성. 외형/각인 질문 시 선제 검색 결과 포함."""
    import re

    context_parts = [f"[친밀도: {intimacy}]"]
    if user_id:
        context_parts.append(f"[사용자 ID: {user_id}]")
    if nickname and intimacy == "formal":
        context_parts.append(f"사용자 닉네임: {nickname}")
    if user_drugs:
        context_parts.append(f"복용 중인 약: {', '.join(user_drugs)}")

    # 외형/각인 질문 감지 및 선제 검색
    appearance_keywords = ["적힌", "각인", "적인", "새겨진", "찍힌", "써있는", "써져있는", "적혀있는"]
    color_keywords = [
        "흰색",
        "하얀",
        "하양",
        "백색",
        "노란",
        "노랑",
        "분홍",
        "빨간",
        "파란",
        "초록",
        "갈색",
        "주황",
        "보라",
    ]

    has_appearance = any(kw in user_message for kw in appearance_keywords)
    has_color = any(kw in user_message for kw in color_keywords)

    if has_appearance or (has_color and any(c.isalpha() and c.isupper() for c in user_message)):
        # 외형/각인 질문으로 판단 → 직접 검색
        from app.services.drug_agent import search_drug_info as _search_drug_info

        # 색상 한글화
        color_map = {"흰색": "하양색", "하얀": "하양색", "백색": "하양색", "노란": "노랑색", "분홍": "분홍색"}
        query_parts = []
        for ck in color_keywords:
            if ck in user_message:
                query_parts.append(color_map.get(ck, ck))
                break

        # 영문 각인 추출 (대문자 연속)
        eng_match = re.findall(r"[A-Z]{1,10}", user_message)
        if eng_match:
            query_parts.extend(eng_match)

        # 숫자 각인 추출
        num_match = re.findall(r"\d+", user_message)
        if num_match:
            query_parts.extend(num_match)

        if query_parts and eng_match:
            # 각인이 있는 경우: 전체 데이터에서 직접 정확 매칭 검색
            import json as _json
            import pickle as _pickle
            import re as _re

            search_query = " ".join(query_parts)
            logger.info(f"[외형 선제검색] query={search_query}")

            # drug_info 인덱스에서 직접 검색
            meta_path = os.path.join("data/faiss", "drug_info_meta.pkl")
            if os.path.exists(meta_path):
                with open(meta_path, "rb") as f:
                    store = _pickle.load(f)

                filtered = []
                for i, sentence in enumerate(store["sentences"]):
                    # 각 각인 문자가 독립적으로 존재하는지 확인
                    has_all_eng = True
                    for eng in eng_match:
                        # 'GM' 단독 매칭 (GM12, WGM 등 제외)
                        pattern = rf"(?<![A-Za-z0-9]){_re.escape(eng)}(?![A-Za-z0-9])"
                        if not _re.search(pattern, sentence):
                            has_all_eng = False
                            break

                    if has_all_eng:
                        # 색상 매칭도 확인 (있으면)
                        color_ok = True
                        if query_parts and query_parts[0] != eng_match[0]:
                            color_term = query_parts[0]  # "하양색" 등
                            # 색상 부분만 추출 ("하양색" → "하양")
                            color_base = color_term.replace("색", "")
                            if color_base not in sentence:
                                color_ok = False

                        if color_ok:
                            filtered.append(
                                {
                                    "score": 1.0,
                                    "type": store["metadata"][i].get("type", ""),
                                    "sentence": sentence[:300],
                                }
                            )

                if filtered:
                    search_result = _json.dumps(filtered[:5], ensure_ascii=False, indent=2)
                    logger.info(f"[외형 선제검색] 직접 검색 결과: {len(filtered)}건 (상위 5건 전달)")
                    context_parts.append(f"\n[사전 검색 결과 - 외형/각인 검색 '{search_query}']\n{search_result}")
                    context_parts.append(
                        "위 검색 결과를 바탕으로 답변해주세요. 추가 Tool 호출 없이 위 결과만 사용해도 됩니다.\n"
                        "중요: 사용자가 물어본 각인 문자가 앞면 또는 뒷면에 독립적으로 각인된 약물만 포함하세요.\n"
                        "독립적이란: 각인 필드에 해당 문자만 단독으로 있는 경우.\n"
                        "정확히 매칭되는 결과가 2개 이하여도 그것만 답변하면 됩니다."
                    )
                else:
                    logger.info("[외형 선제검색] 정확 매칭 결과 없음")
        elif query_parts:
            # 각인 없이 색상/모양만 있는 경우: 기존 search_drug_info 사용
            from app.services.drug_agent import search_drug_info as _search_drug_info

            search_query = " ".join(query_parts)
            logger.info(f"[외형 선제검색] query={search_query} (색상/모양만)")
            search_result = _search_drug_info(search_query, top_k=5)
            context_parts.append(f"\n[사전 검색 결과 - 외형 검색 '{search_query}']\n{search_result}")
            context_parts.append("위 검색 결과를 바탕으로 답변해주세요.")

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
