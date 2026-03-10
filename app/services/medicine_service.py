import asyncio
import re

import httpx

from app.core import config
from app.models.medicine import Medicine


class MfdsClient:
    _EASY_DRUG_URL = "http://apis.data.go.kr/1471000/DrbEasyDrugInfoService/getDrbEasyDrugList"
    _PILL_URL = "https://apis.data.go.kr/1471000/MdcinGrnIdntfcInfoService03/getMdcinGrnIdntfcInfoList03"

    async def search_easy_drug(self, keyword: str, num_of_rows: int) -> list[dict]:
        if not config.MFDS_API_KEY:
            return []
        params: dict[str, str | int] = {
            "serviceKey": config.MFDS_API_KEY,
            "itemName": keyword,
            "numOfRows": num_of_rows,
            "pageNo": 1,
            "type": "json",
        }
        return await self._get(self._EASY_DRUG_URL, params)

    async def search_pill(self, keyword: str, num_of_rows: int) -> list[dict]:
        if not config.MFDS_PILL_API_KEY:
            return []
        params: dict[str, str | int] = {
            "serviceKey": config.MFDS_PILL_API_KEY,
            "item_name": keyword,
            "numOfRows": num_of_rows,
            "pageNo": 1,
            "type": "json",
        }
        return await self._get(self._PILL_URL, params)

    async def _get(self, url: str, params: dict[str, str | int]) -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=config.MFDS_API_TIMEOUT) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                body = response.json().get("body", {})
            items = body.get("items") or []
            return items if isinstance(items, list) else []
        except Exception:
            return []


class MedicineService:
    def __init__(self) -> None:
        self._client = MfdsClient()

    async def search(self, keyword: str, limit: int = 20) -> list[dict]:
        results = (
            await Medicine.filter(search_keyword__startswith=keyword, is_active=True)
            .limit(limit)
            .values("item_seq", "item_name", "entp_name")
        )

        if results:
            return list(results)

        easy, pill = await asyncio.gather(
            self._client.search_easy_drug(keyword, limit),
            self._client.search_pill(keyword, limit),
        )
        merged = self._merge(easy, pill)
        if merged:
            await self._cache_from_api(merged)
            results = (
                await Medicine.filter(search_keyword__startswith=keyword, is_active=True)
                .limit(limit)
                .values("item_seq", "item_name", "entp_name")
            )

        return list(results)

    async def get_detail(self, item_seq: str) -> Medicine | None:
        return await Medicine.get_or_none(item_seq=item_seq, is_active=True)

    async def _cache_from_api(self, items: list[dict]) -> None:
        for item in items:
            item_seq = item.get("itemSeq") or item.get("ITEM_SEQ")
            item_name = item.get("itemName") or item.get("ITEM_NAME", "")
            if not item_seq:
                continue
            await Medicine.get_or_create(
                item_seq=item_seq,
                defaults={
                    "item_name": item_name,
                    "search_keyword": self._normalize_keyword(item_name),
                    "entp_name": item.get("entpName") or item.get("ENTP_NAME"),
                    "efcy_qesitm": item.get("efcyQesitm"),
                    "use_method_qesitm": item.get("useMethodQesitm"),
                    "item_image": item.get("itemImage") or item.get("ITEM_IMAGE"),
                    "print_front": item.get("printFront") or item.get("PRINT_FRONT"),
                    "print_back": item.get("printBack") or item.get("PRINT_BACK"),
                    "drug_shape": item.get("drugShape") or item.get("DRUG_SHAPE"),
                    "color_class": item.get("colorClass1") or item.get("COLOR_CLASS1"),
                },
            )

    @staticmethod
    def _merge(easy: list[dict], pill: list[dict]) -> list[dict]:
        seen: set[str] = set()
        merged = []
        for item in easy + pill:
            seq = item.get("itemSeq") or item.get("ITEM_SEQ")
            if seq and seq not in seen:
                seen.add(seq)
                merged.append(item)
        return merged

    @staticmethod
    def _normalize_keyword(item_name: str) -> str:
        return re.sub(
            r"\d+(\.\d+)?(mg|밀리그램|mcg|g|ml|밀리리터|iu|μg|%)",
            "",
            item_name,
            flags=re.IGNORECASE,
        ).strip()
