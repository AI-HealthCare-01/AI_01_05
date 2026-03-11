from __future__ import annotations

import json
import re
import uuid
from collections import defaultdict

import httpx

from app.core import config
from app.dtos.ocr_dto import OcrParsedItem, ParsedPrescriptionResponse
from app.models.medicine import Medicine

_NOISE_KEYWORDS = [
    "조제", "복약지도", "보험", "환자명", "병원명", "전화번호",
    "약품명", "약품사진", "복약안내", "총수납금액",
]
# 줄 전체가 노이즈인 경우만 제외 (약품명이 포함된 줄은 유지)
# 약품명 접미사가 없는 줄에서만 노이즈 키워드 필터 적용
_NOISE_ONLY_KEYWORDS = ["조제", "복약지도", "환자명", "병원명", "전화번호", "총수납금액"]
# 약품명 접미사가 없고 아래 키워드만 있는 줄 제외
_NOISE_HEADER_KEYWORDS = ["약품명", "약품사진", "복약안내"]
# 투약일수 단독 헤더 줄 필터 ("연세라온치과 투약일수 3" 등) — 총투약일수는 유지
_NOISE_LINE_RE = re.compile(r"^(?!.*총투약일수).*투약일수")

# 패턴 1: 순수 인라인 "약품명 투약량 횟수 일수"
_PATTERN_INLINE = re.compile(
    r"^(?P<name>[가-힣a-zA-Z0-9%\.]+)\s+"
    r"(?P<dose>\d+\.?\d*)\s+"
    r"(?P<freq>\d+)\s+"
    r"(?P<days>\d+)$"
)
# 패턴 2: 약품명+투약정보 한 줄 레이블 인라인
# "시클러캡슐250밀리그램(세파 1회투약량 1.00 1일투여횟수3 총투약일수3 ..."
_PATTERN_LABEL_INLINE = re.compile(
    r"^(?P<name>[가-힣a-zA-Z0-9%\.]+)"
    r"(?:\([^)]*\))?"
    r".*?"
    r"1회투약량\s*(?P<dose>\d+\.?\d*)"
    r".*?"
    r"1일투여횟수\s*(?P<freq>\d+)"
    r".*?"
    r"총투약일수\s*(?P<days>\d+)",
    re.DOTALL,
)
# 줄 끝 "N N N" 패턴 — 뒤에 비숫자 문자가 있어도 허용
_PATTERN_TRAILING_NUMS = re.compile(
    r"\b(?P<dose>\d+\.?\d*)\s+(?P<freq>\d+)\s+(?P<days>\d+)\s*(?:[^\d\n].*)?$"
)
# 패턴 5: 다중 약품 한 줄 "약품명1 약품명2 약품명3 투약량1 투약량2 투약량3 횟수1 횟수2 횟수3 일수1 일수2 일수3"
_PATTERN_MULTI_DRUG = re.compile(r"^[가-힣]")

_PATTERN_DOSE = re.compile(r"1회투약량\s*(\d+\.?\d*)")
_PATTERN_FREQ = re.compile(r"1일투여횟수\s*(\d+)")
_PATTERN_DAYS = re.compile(r"총투약일수\s*(\d+)")

_UNIT_MAP = [
    (re.compile(r"\bmg\b", re.IGNORECASE), "밀리그램"),
    (re.compile(r"\bg\b", re.IGNORECASE), "그램"),
    (re.compile(r"\bml\b", re.IGNORECASE), "밀리리터"),
]
_TYPO_MAP = [
    ("밀리그림", "밀리그램"),
    ("미리그람", "밀리그램"),
    ("캅셀", "캡슐"),
]
_DOSE_STRIP = re.compile(r"\d+(\.\d+)?(밀리그램|그램|밀리리터|mg|g|ml)", re.IGNORECASE)
# 의약품 접미사 포함 여부 — 병합 조건 제한용
_DRUG_NAME_START_RE = re.compile(
    r"^[가-힣a-zA-Z0-9].*?(정|캡슐|액|크림|연고|주|산|시럽|패치|주사|주사제|주사액|제|환)"
)
# 약품명 접미사 추출용
# - 반드시 한글로 시작
# - 접미사(정/캡슐/액/크림/연고 등) 포함
# - 접미사 뒤 숫자/단위 허용 (예: 오메크라정625밀리그램)
_DRUG_SUFFIX_RE = re.compile(
    r"(?P<name>[가-힣][가-힣a-zA-Z0-9%\.]*(?:정|캡슐|액|크림|연고|산|시럽|패치|주사|주사제|주사액)[가-힣a-zA-Z0-9%\.]*)"
)


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

    async def parse_prescription(self, file_bytes: bytes, file_type: str) -> ParsedPrescriptionResponse:
        provider = (config.OCR_PROVIDER or "stub").lower()

        if provider == "stub":
            return ParsedPrescriptionResponse(items=[], raw_text="")

        processed = self._preprocess_image(file_bytes)
        try:
            raw_text = await self.extract_text(file_bytes=processed, file_type=file_type)
        except ValueError:
            return ParsedPrescriptionResponse(items=[], raw_text="")

        lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
        parsed = self._parse_prescription_text(lines)

        items: list[OcrParsedItem] = []
        for entry in parsed:
            cleaned = self._clean_drug_name(entry["drug_name"])
            candidates = await self._smart_verify_drug(cleaned)
            matched = self._verify_drug_with_mfds(candidates, entry["drug_name"])
            if matched:
                items.append(OcrParsedItem(
                    item_seq=matched.get("item_seq"),
                    item_name=matched.get("item_name", cleaned),
                    dose_per_intake=entry["dose_per_intake"],
                    daily_frequency=entry["daily_frequency"],
                    total_days=entry["total_days"],
                    confidence="HIGH",
                ))
            else:
                items.append(OcrParsedItem(
                    item_seq=None,
                    item_name=cleaned,
                    dose_per_intake=entry["dose_per_intake"],
                    daily_frequency=entry["daily_frequency"],
                    total_days=entry["total_days"],
                    confidence="LOW",
                ))

        return ParsedPrescriptionResponse(items=items, raw_text=raw_text)

    # ── 전처리 ────────────────────────────────────────────────────────────────

    def _preprocess_image(self, image_bytes: bytes) -> bytes:
        """방향 보정 → Grayscale → Gaussian Blur. opencv 미설치 시 원본 반환."""
        try:
            import io

            import cv2
            import numpy as np
            from PIL import Image, ImageOps

            with io.BytesIO(image_bytes) as buf:
                pil_img = ImageOps.exif_transpose(Image.open(buf))
            img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2GRAY)
            img = cv2.GaussianBlur(img, (3, 3), 0)
            _, encoded = cv2.imencode(".jpg", img)
            return encoded.tobytes()
        except ImportError:
            return image_bytes

    # ── 파싱 ──────────────────────────────────────────────────────────────────

    def _parse_prescription_text(self, lines: list[str]) -> list[dict]:
        results: list[dict] = []
        filtered = [
            l for l in lines
            if not any(kw in l for kw in _NOISE_ONLY_KEYWORDS)
            and not _NOISE_LINE_RE.search(l)
            and not (_DRUG_SUFFIX_RE.search(l) is None and any(kw in l for kw in _NOISE_HEADER_KEYWORDS))
        ]

        # 패턴 1: 순수 인라인 "약품명 투약량 횟수 일수"
        for line in filtered:
            m = _PATTERN_INLINE.match(line)
            if m:
                results.append({
                    "drug_name": m.group("name"),
                    "dose_per_intake": float(m.group("dose")),
                    "daily_frequency": int(m.group("freq")),
                    "total_days": int(m.group("days")),
                })
        if results:
            return results

        # 패턴 2: 약품명+투약정보 한 줄 레이블 인라인
        # 총투약일수가 다음 줄에 있는 경우 병합 후 재시도 (의약품 접미사 포함 줄만)
        i = 0
        while i < len(filtered):
            line = filtered[i]
            m = _PATTERN_LABEL_INLINE.match(line)
            if not m and i + 1 < len(filtered) and _DRUG_NAME_START_RE.match(line):
                merged = line + " " + filtered[i + 1]
                m = _PATTERN_LABEL_INLINE.match(merged)
                if m:
                    i += 1
            if m:
                results.append({
                    "drug_name": m.group("name"),
                    "dose_per_intake": float(m.group("dose")),
                    "daily_frequency": int(m.group("freq")),
                    "total_days": int(m.group("days")),
                })
            i += 1
        if results:
            return results

        # 패턴 5: 다중 약품 한 줄 "약품명1 약품명2 ... 투약량1 투약량2 ... 횟수1 ... 일수1 ..."
        for line in filtered:
            if not _PATTERN_MULTI_DRUG.match(line):
                continue
            tokens = line.split()
            names = [t for t in tokens if re.match(r"^[가-힣]", t) and _DRUG_SUFFIX_RE.search(t)]
            nums = [t for t in tokens if re.match(r"^\d+\.?\d*$", t)]
            n = len(names)
            if n >= 2 and len(nums) == n * 3:
                doses = nums[:n]
                freqs = nums[n:n * 2]
                days = nums[n * 2:]
                for name, d, f, dy in zip(names, doses, freqs, days):
                    results.append({
                        "drug_name": name,
                        "dose_per_intake": float(d),
                        "daily_frequency": int(f),
                        "total_days": int(dy),
                    })
                if results:
                    return results

        # 패턴 4: 약품명 줄 + 이후 3줄 이내 끝 "N N N" 연결
        # - 약품명이 줄 중간에 있는 경우도 탐색 (search 사용)
        # - 새 약품명이 나와도 투약정보를 찾을 때까지 이전 약품명 유지
        i = 0
        pending_name: str | None = None
        pending_since: int = 0
        while i < len(filtered):
            line = filtered[i]
            nums_m = _PATTERN_TRAILING_NUMS.search(line)
            if nums_m and pending_name and (i - pending_since) <= 3:
                results.append({
                    "drug_name": pending_name,
                    "dose_per_intake": float(nums_m.group("dose")),
                    "daily_frequency": int(nums_m.group("freq")),
                    "total_days": int(nums_m.group("days")),
                })
                pending_name = None
            name_m = _DRUG_SUFFIX_RE.search(line)
            if name_m and not nums_m:
                # 투약정보가 없는 줄에서만 약품명 갱신
                pending_name = name_m.group("name")
                pending_since = i
            elif pending_name and (i - pending_since) > 3:
                pending_name = None
            i += 1
        if results:
            return results

        # 패턴 3 (fallback): 순수 레이블 형식 (각각 별도 줄)
        full_text = "\n".join(filtered)
        dose_m = _PATTERN_DOSE.search(full_text)
        freq_m = _PATTERN_FREQ.search(full_text)
        days_m = _PATTERN_DAYS.search(full_text)
        if dose_m and freq_m and days_m:
            drug_name = filtered[0] if filtered else ""
            results.append({
                "drug_name": drug_name,
                "dose_per_intake": float(dose_m.group(1)),
                "daily_frequency": int(freq_m.group(1)),
                "total_days": int(days_m.group(1)),
            })

        return results

    def _clean_drug_name(self, raw: str) -> str:
        name = re.sub(r"[（(]?수출명[：:].*", "", raw, flags=re.IGNORECASE).strip()
        name = re.sub(r"\(.*?\)", "", name).strip()
        name = re.sub(r"[^\w가-힣\d\.%]", "", name)
        for pattern, replacement in _UNIT_MAP:
            name = pattern.sub(replacement, name)
        for typo, correct in _TYPO_MAP:
            name = name.replace(typo, correct)
        return name.strip()

    async def _smart_verify_drug(self, cleaned_name: str) -> list[dict]:
        results = await Medicine.filter(
            search_keyword__startswith=cleaned_name, is_active=True
        ).limit(10).values("item_seq", "item_name", "entp_name")
        if results:
            return list(results)

        base_name = _DOSE_STRIP.sub("", cleaned_name).strip()
        if base_name == cleaned_name:
            return []
        results = await Medicine.filter(
            search_keyword__startswith=base_name, is_active=True
        ).limit(10).values("item_seq", "item_name", "entp_name")
        return list(results)

    def _verify_drug_with_mfds(self, candidates: list[dict], original_name: str) -> dict | None:
        if not candidates:
            return None
        numbers = re.findall(r"\d+", original_name)
        if not numbers:
            return candidates[0]
        for num in numbers:
            for c in candidates:
                if num in c.get("item_name", ""):
                    return c
        return candidates[0]

    # ── HTTP / Clova ──────────────────────────────────────────────────────────

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
        """Clova OCR 호출 — x+y 좌표 기반 줄 재구성."""
        if not config.CLOVA_OCR_INVOKE_URL or not config.CLOVA_OCR_SECRET_KEY:
            raise ValueError("OCR_NOT_CONFIGURED")

        message = json.dumps({
            "version": "V2",
            "requestId": str(uuid.uuid4()),
            "timestamp": 0,
            "images": [{"format": file_type.split("/")[-1], "name": "prescription"}],
        })
        headers = {"X-OCR-SECRET": config.CLOVA_OCR_SECRET_KEY}
        async with httpx.AsyncClient(timeout=config.OCR_TIMEOUT_SECONDS) as client:
            response = await client.post(
                config.CLOVA_OCR_INVOKE_URL,
                headers=headers,
                data={"message": message},
                files={"file": ("prescription", file_bytes, file_type)},
            )
            response.raise_for_status()
            payload = response.json()

        fields = payload.get("images", [{}])[0].get("fields", [])
        if not fields:
            raise ValueError("OCR_EMPTY_RESULT")
        return self._reconstruct_lines(fields)

    @staticmethod
    def _reconstruct_lines(fields: list[dict], threshold: int = 15) -> str:
        """boundingPoly x+y 좌표 기반으로 단어를 줄 단위로 재구성."""
        groups: dict[int, list[tuple[int, str]]] = defaultdict(list)
        for field in fields:
            vertices = field.get("boundingPoly", {}).get("vertices", [{}])
            y = vertices[0].get("y", 0)
            x = vertices[0].get("x", 0)
            groups[y].append((x, field.get("inferText", "")))

        sorted_ys = sorted(groups.keys())
        merged: list[list[tuple[int, str]]] = []
        current: list[tuple[int, str]] = list(groups[sorted_ys[0]])
        current_y = sorted_ys[0]

        for y in sorted_ys[1:]:
            if abs(y - current_y) <= threshold:
                current.extend(groups[y])
            else:
                merged.append(sorted(current, key=lambda t: t[0]))
                current = list(groups[y])
            current_y = y
        if current:
            merged.append(sorted(current, key=lambda t: t[0]))

        return "\n".join(" ".join(t for _, t in line) for line in merged)

    def _find_text(self, payload: dict | list | str) -> str:
        if isinstance(payload, str):
            return payload.strip()
        if isinstance(payload, dict):
            for key in ("text", "extractedText", "extracted_text", "result"):
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
