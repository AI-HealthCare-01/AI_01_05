"""식약처 e약은요 API 클라이언트.

Design spec: chat-core.design.md §5.4
공공데이터포털 DrbEasyDrugInfoService API를 통해 약물 정보를 조회한다.
"""

import logging
import os

import httpx

logger = logging.getLogger("dodaktalk.kfda")
_cache: dict[str, dict] = {}

KFDA_BASE_URL = "https://apis.data.go.kr/1471000/DrbEasyDrugInfoService/getDrbEasyDrugList"


class KFDAClient:
    """식약처 e약은요 API 클라이언트."""

    def __init__(self) -> None:
        self.api_key = os.getenv("KFDA_API_KEY")
        if not self.api_key:
            logger.warning("KFDA_API_KEY가 설정되지 않았습니다. 식약처 API를 사용할 수 없습니다.")

    async def search_drug(self, drug_name: str) -> dict | None:
        """e약은요 API로 약물 정보를 조회합니다.

        Args:
            drug_name: 약물명 (예: "아모디핀")

        Returns:
            약물 정보 딕셔너리 또는 검색 결과 없으면 None.
        """
        if not self.api_key:
            return None

        params = {
            "serviceKey": self.api_key,
            "itemName": drug_name,
            "type": "json",
            "numOfRows": "1",
        }

        if drug_name in _cache:
            return _cache[drug_name]
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(KFDA_BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()

            body = data.get("body", {})
            items = body.get("items", [])
            if not items:
                return None

            item = items[0]
            result = {
                "name": item.get("itemName", drug_name),
                "efcy": item.get("efcyQesitm", ""),
                "use_method": item.get("useMethodQesitm", ""),
                "caution": item.get("atpnQesitm", ""),
                "interaction": item.get("intrcQesitm", ""),
                "side_effect": item.get("seQesitm", ""),
                "storage": item.get("depositMethodQesitm", ""),
            }
            _cache[drug_name] = result
            return result
        except Exception as e:
            logger.warning("식약처 API 호출 실패 (약물: %s): %s", drug_name, e)
            return None

    async def get_drug_context(self, meds: list[str]) -> str:
        """약물 리스트에서 컨텍스트 문자열을 생성합니다.

        Args:
            meds: 복용 중인 약물명 리스트

        Returns:
            LLM 프롬프트에 주입할 약물 정보 텍스트. 실패 시 빈 문자열.
        """
        if not meds or not self.api_key:
            return ""

        context_parts: list[str] = []
        import re

        for med in meds:
            # "탁센연질캡슐(나프록센) (1.00정, 하루 1회)" → "탁센연질캡슐"
            med = re.sub(r"\s*\(.*", "", med).strip()
            info = await self.search_drug(med)
            if info:
                part = f"[{info['name']}]\n"
                if info["efcy"]:
                    part += f"  효능: {info['efcy'][:200]}\n"
                if info["caution"]:
                    part += f"  주의사항: {info['caution'][:300]}\n"
                if info["interaction"]:
                    part += f"  상호작용: {info['interaction'][:200]}\n"
                context_parts.append(part)

        return "\n".join(context_parts)
