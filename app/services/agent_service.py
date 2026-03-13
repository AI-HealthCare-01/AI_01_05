from __future__ import annotations
import logging
import os
import re
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from app.services.kfda_service import KFDAClient

logger = logging.getLogger("dodaktalk.agent")
kfda_client = KFDAClient()

@tool
async def search_medicine_info(medicine_name: str) -> str:
    """식약처 e약은요 API에서 약물의 효능, 주의사항, 상호작용, 부작용 정보를 검색합니다."""
    clean_name = re.sub(r"\s*\(.*", "", medicine_name).strip()
    info = await kfda_client.search_drug(clean_name)
    if not info:
        return f"{medicine_name}에 대한 식약처 정보를 찾을 수 없습니다."
    result = f"[{info['name']}]\n"
    if info["efcy"]:
        result += f"효능: {info['efcy'][:300]}\n"
    if info["caution"]:
        result += f"주의사항: {info['caution'][:300]}\n"
    if info["interaction"]:
        result += f"상호작용: {info['interaction'][:300]}\n"
    if info["side_effect"]:
        result += f"부작용: {info['side_effect'][:200]}\n"
    return result

@tool
def check_drug_interaction(drug_a: str, drug_b: str) -> str:
    """두 약물을 함께 복용해도 되는지 기본 규칙을 반환합니다."""
    nsaids = ["나프록센", "이부프로펜", "아스피린", "디클로페낙", "탁센", "애드빌", "부루펜"]
    acetaminophen = ["아세트아미노펜", "타이레놀", "타세놀"]
    a_is_nsaid = any(n in drug_a for n in nsaids)
    b_is_nsaid = any(n in drug_b for n in nsaids)
    a_is_acet = any(n in drug_a for n in acetaminophen)
    b_is_acet = any(n in drug_b for n in acetaminophen)
    if a_is_nsaid and b_is_nsaid:
        return f"위험: {drug_a}와 {drug_b}는 모두 NSAID 계열입니다. 동시 복용 시 위장출혈, 신장 손상 위험이 높아집니다."
    if (a_is_nsaid and b_is_acet) or (a_is_acet and b_is_nsaid):
        return f"주의: {drug_a}와 {drug_b}는 함께 복용 가능하지만 용량을 엄격히 지켜야 합니다."
    return f"{drug_a}와 {drug_b}의 상호작용은 search_medicine_info로 각각 확인하세요."

class AgentService:
    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.7,
            api_key=api_key,
            max_tokens=1000,
        )
        self.tools = [search_medicine_info, check_drug_interaction]
        self.agent = create_react_agent(self.llm, self.tools)

    async def get_response(self, user_message: str, meds: list[str], med_dosages: list[str], system_prompt: str) -> str:
        dosage_info = "\n".join(f"- {d}" for d in med_dosages) if med_dosages else "없음"
        full_system = (
            system_prompt
            + f"\n\n[사용자 복용 중인 약물]\n{dosage_info}"
            + "\n\n필요한 경우 search_medicine_info, check_drug_interaction 툴을 사용해서 정확한 정보를 찾아 답변해줘."
            + "\n\n답변 규칙: 빈 줄을 최소화하고, 내용은 간결하게 작성해. 단락 사이 빈 줄은 1줄만 사용해."
        )
        result = await self.agent.ainvoke({
            "messages": [
                SystemMessage(content=full_system),
                HumanMessage(content=user_message),
            ]
        })
        return result["messages"][-1].content

_agent_service: AgentService | None = None

def get_agent_service() -> AgentService:
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
    return _agent_service
