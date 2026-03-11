from __future__ import annotations

import json
import uuid

import httpx

from app.core import config


class OcrService:
    async def extract_text(self, file_bytes: bytes, file_type: str) -> str:
        provider = (config.OCR_PROVIDER or "stub").lower()

        if provider == "stub":
            return "손글씨 인식 결과입니다."
        if provider == "http":
            return await self._extract_text_via_http(file_bytes=file_bytes, file_type=file_type)
        if provider == "clova":
            return await self._extract_text_via_clova(file_bytes=file_bytes, file_type=file_type)
        raise ValueError("OCR_PROVIDER_NOT_SUPPORTED")

    async def _extract_text_via_http(self, file_bytes: bytes, file_type: str) -> str:
        if not config.OCR_API_URL:
            raise ValueError("OCR_NOT_CONFIGURED")

        headers: dict[str, str] = {}
        if config.OCR_API_KEY:
            headers["Authorization"] = f"Bearer {config.OCR_API_KEY}"

        async with httpx.AsyncClient(timeout=config.OCR_TIMEOUT_SECONDS) as client:
            response = await client.post(
                config.OCR_API_URL,
                files={"image": ("upload", file_bytes, file_type)},
                headers=headers,
            )
            response.raise_for_status()
            payload = response.json()

        extracted = self._find_text(payload)
        if not extracted:
            raise ValueError("OCR_EMPTY_RESULT")
        return extracted

    async def _extract_text_via_clova(self, file_bytes: bytes, file_type: str) -> str:
        """Clova OCR (X-OCR-SECRET 헤더 방식) 호출."""
        if not config.OCR_API_URL or not config.OCR_API_KEY:
            raise ValueError("OCR_NOT_CONFIGURED")

        message = json.dumps({
            "version": "V2",
            "requestId": str(uuid.uuid4()),
            "timestamp": 0,
            "images": [{"format": file_type.split("/")[-1], "name": "prescription"}],
        })
        headers = {"X-OCR-SECRET": config.OCR_API_KEY}
        async with httpx.AsyncClient(timeout=config.OCR_TIMEOUT_SECONDS) as client:
            response = await client.post(
                config.OCR_API_URL,
                headers=headers,
                data={"message": message},
                files={"file": ("prescription", file_bytes, file_type)},
            )
            response.raise_for_status()
            payload = response.json()

        fields = payload.get("images", [{}])[0].get("fields", [])
        if not fields:
            raise ValueError("OCR_EMPTY_RESULT")
        lines = sorted(fields, key=lambda f: f.get("boundingPoly", {}).get("vertices", [{}])[0].get("y", 0))
        return "\n".join(f.get("inferText", "") for f in lines)

    def _find_text(self, payload: dict | list | str) -> str:
        if isinstance(payload, str):
            return payload.strip()
        if isinstance(payload, dict):
            direct_keys = ("text", "extractedText", "extracted_text", "result")
            for key in direct_keys:
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            for value in payload.values():
                found = self._find_text(value)
                if found:
                    return found
            return ""
        if isinstance(payload, list):
            parts = [self._find_text(item) for item in payload]
            return " ".join(part for part in parts if part).strip()
        return ""
