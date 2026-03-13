"""낱알식별 API 서비스."""
import logging
import os
import httpx

logger = logging.getLogger("dodaktalk.pill")
PILL_API_URL = "https://apis.data.go.kr/1471000/MdcinGrnIdntfcInfoService03/getMdcinGrnIdntfcInfoList03"

class PillIdentifier:
    def __init__(self) -> None:
        self.api_key = os.getenv("KFDA_API_KEY") or os.getenv("MFDS_API_KEY")
        if not self.api_key:
            logger.warning("API 키가 설정되지 않았습니다.")

    async def search(self, item_name: str | None = None, entp_name: str | None = None, color: str | None = None, shape: str | None = None) -> list[dict]:
        if not self.api_key:
            return []
        params = {
            "serviceKey": self.api_key,
            "type": "json",
            "numOfRows": "5",
            "pageNo": "1",
        }
        if item_name:
            params["item_name"] = item_name
        if entp_name:
            params["entp_name"] = entp_name
        if color:
            params["COLOR_CLASS1"] = color
        if shape:
            params["DRUG_SHAPE"] = shape

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(PILL_API_URL, params=params)
                r.raise_for_status()
                data = r.json()
            body = data.get("body", {})
            items = body.get("items", [])
            if not items:
                return []
            results = []
            for item in items:
                results.append({
                    "name": item.get("ITEM_NAME", ""),
                    "company": item.get("ENTP_NAME", ""),
                    "shape": item.get("DRUG_SHAPE", ""),
                    "color": item.get("COLOR_CLASS1", ""),
                    "imprint": item.get("PRINT_FRONT", ""),
                    "image_url": item.get("ITEM_IMAGE", ""),
                })
            return results
        except Exception as e:
            logger.warning("낱알식별 API 호출 실패: %s", e)
            return []

    def format_results(self, results: list[dict]) -> str:
        if not results:
            return "해당 조건의 약을 찾을 수 없습니다."
        lines = []
        for r in results:
            line = f"- {r['name']} ({r['company']})"
            if r["shape"]:
                line += f" | 모양: {r['shape']}"
            if r["color"]:
                line += f" | 색깔: {r['color']}"
            if r["imprint"]:
                line += f" | 각인: {r['imprint']}"
            lines.append(line)
        return "\n".join(lines)
