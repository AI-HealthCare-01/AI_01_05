import re

import httpx

from app.core import config
from app.models.medicine import Medicine


class MfdsClient:
    async def search(self, keyword: str, num_of_rows: int = 20) -> list[dict]:
        if not config.MFDS_API_KEY:
            return []
        url = "http://apis.data.go.kr/1471000/DrbEasyDrugInfoService/getDrbEasyDrugList"
        params = {
            "serviceKey": config.MFDS_API_KEY,
            "itemName": keyword,
            "numOfRows": num_of_rows,
            "pageNo": 1,
            "type": "json",
        }
        try:
            async with httpx.AsyncClient(timeout=config.MFDS_API_TIMEOUT) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                body = response.json()
            items = body.get("body", {}).get("items", []) or []
            return items if isinstance(items, list) else []
        except Exception:
            return []


class MedicineService:
    def __init__(self) -> None:
        self._client = MfdsClient()

    async def search(self, keyword: str, limit: int = 20) -> list[dict]:
        results = await Medicine.filter(
            search_keyword__startswith=keyword, is_active=True
        ).limit(limit).values("item_seq", "item_name", "entp_name")

        if results:
            return list(results)

        api_items = await self._client.search(keyword, num_of_rows=limit)
        if api_items:
            await self._cache_from_api(api_items)
            results = await Medicine.filter(
                search_keyword__startswith=keyword, is_active=True
            ).limit(limit).values("item_seq", "item_name", "entp_name")

        return list(results)

    async def get_detail(self, item_seq: str) -> Medicine | None:
        return await Medicine.get_or_none(item_seq=item_seq, is_active=True)

    async def _cache_from_api(self, items: list[dict]) -> None:
        for item in items:
            item_seq = item.get("ITEM_SEQ") or item.get("item_seq")
            item_name = item.get("ITEM_NAME") or item.get("item_name", "")
            if not item_seq:
                continue
            await Medicine.get_or_create(
                item_seq=item_seq,
                defaults={
                    "item_name": item_name,
                    "search_keyword": self._normalize_keyword(item_name),
                    "entp_name": item.get("ENTP_NAME") or item.get("entp_name"),
                    "efcy_qesitm": item.get("EFCY_QESITM"),
                    "use_method_qesitm": item.get("USE_METHOD_QESITM"),
                    "item_image": item.get("ITEM_IMAGE"),
                },
            )

    @staticmethod
    def _normalize_keyword(item_name: str) -> str:
        return re.sub(
            r"\d+(\.\d+)?(mg|밀리그램|mcg|g|ml|밀리리터|iu|μg|%)",
            "",
            item_name,
            flags=re.IGNORECASE,
        ).strip()
