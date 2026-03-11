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
    r"(?:\([^)]*\?)?"
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
# - 접미사(정/캡슐/액/크림/연고/시럽/패치/주사) 포함
# - 접미사 뒤 숫자/영문/밀리그램/그램/밀리리터 허용 (예: 오메크라정625밀리그램)
# - 산/제 제외: 클라불란산칼륨 같은 성분명 오매칭 방지
_DRUG_SUFFIX_RE = re.compile(
    r"(?P<name>[가-힣][가-힣a-zA-Z0-9%\.]*"
    r"(?:정|캡슐|액|크림|연고|시럽|패치|주사|주사제|주사액)"
    r"(?:[0-9a-zA-Z%\.]*(?:밀리그램|그램|밀리리터)?[0-9a-zA-Z%\.]*)?)"
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
        """방향 보정 → Grayscale → Gaussian Blur. 실패 시 원본 반환."""
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
        except (ImportError, Exception):
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
        # 총투약일수가 다음 줄에 있는 경우 최대 3줄 병합 후 재시도
        i = 0
        while i < len(filtered):
            line = filtered[i]
            m = _PATTERN_LABEL_INLINE.match(line)
            if not m and _DRUG_NAME_START_RE.match(line):
                for extra in range(1, 4):
                    if i + extra < len(filtered):
                        merged = " ".join(filtered[i:i + extra + 1])
                        m = _PATTERN_LABEL_INLINE.match(merged)
                        if m:
                            i += extra
                            break
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

        # 패턴 6: 컬럼 분리형 — 약품명 줄들 + "투약량" 헤더 + 숫자들 + "횟수" 헤더 + 숫자들 + "일수" 헤더 + 숫자들
        col_result = self._parse_column_layout(filtered)
        if col_result:
            return col_result

        # 패턴 7: 인터리브형 — 헤더(일수/횟수/투약량/약품명) 이후 약품명 직전 숫자들로 매핑
        interleaved = self._parse_interleaved_layout(filtered)
        if interleaved:
            return interleaved

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

    @staticmethod
    def _parse_column_layout(lines: list[str]) -> list[dict]:
        """컬럼 분리형 처방전 파싱.

        약품명들이 별도 줄에 있고, 이후 '투약량' / '횟수' / '일수' 헤더 줄 뒤에
        각 약품의 숫자값이 나열되는 구조를 처리한다.
        헤더와 숫자가 같은 줄에 인라인으로 있는 경우(예: '투약량 1 1 1')도 처리한다.
        약품명이 헤더 이후에 있는 경우도 처리한다.
        """
        _NUM_RE = re.compile(r"^\d+\.?\d*$")
        _NOISE_NUM_RE = re.compile(r"^\d+\.?\d*[\uAC00-\uD7A3a-zA-Z]")
        _NOISE_DRUG_RE = re.compile(r"약제비|연간액|수납금액|총액")

        def expand_digits(tokens: list[str]) -> list[str]:
            """두 자리 이상 숫자(각 자리 1-9)를 개별 자리로 분리 (예: '22' → ['2','2'])."""
            result = []
            for t in tokens:
                if _NUM_RE.match(t) and len(t) > 1 and "." not in t and all(c != "0" for c in t):
                    result.extend(list(t))
                else:
                    result.append(t)
            return result

        def extract_nums(line: str, expand: bool = False) -> list[float]:
            tokens = line.split()
            if expand:
                tokens = expand_digits(tokens)
            result = []
            for i, t in enumerate(tokens):
                if not _NUM_RE.match(t) or _NOISE_NUM_RE.match(t):
                    continue
                if i + 1 < len(tokens) and re.match(r"^[\uAC00-\uD7A3]", tokens[i + 1]):
                    continue
                result.append(float(t))
            return result

        dose_idx = freq_idx = days_idx = -1
        for i, line in enumerate(lines):
            if "투약량" in line and dose_idx == -1:
                dose_idx = i
            elif "횟수" in line and freq_idx == -1:
                freq_idx = i
            elif "일수" in line and days_idx == -1:
                days_idx = i

        if dose_idx == -1 or freq_idx == -1 or days_idx == -1:
            return []

        ordered_idxs = sorted([dose_idx, freq_idx, days_idx])

        def collect_nums(header_idx: int, expand: bool = False) -> list[float]:
            inline = extract_nums(lines[header_idx], expand)
            if inline:
                return inline
            next_idx = next((j for j in ordered_idxs if j > header_idx), len(lines))
            # 다음 헤더까지 모든 숫자 수집
            result: list[float] = []
            for line in lines[header_idx + 1:next_idx]:
                result.extend(extract_nums(line, expand))
            return result

        doses = collect_nums(dose_idx)
        freqs = collect_nums(freq_idx, expand=True)
        days_list = collect_nums(days_idx, expand=True)

        if not doses or not freqs or not days_list:
            return []

        # 약품명 수집: 전체 라인에서 토큰별로 접미사 포함 약품명 추출
        # (헤더 이전/이후 모두 포함, 한 줄에 여러 약품명도 처리)
        drug_names: list[str] = []
        for line in lines:
            tokens = line.split()
            for t in tokens:
                m = _DRUG_SUFFIX_RE.match(t)
                if m and not _NOISE_DRUG_RE.search(t):
                    drug_names.append(m.group("name"))

        n = len(drug_names)
        if n == 0:
            return []

        def pad(lst: list[float]) -> list[float]:
            return (lst + [lst[-1]] * (n - len(lst)))[:n] if lst else lst

        doses, freqs, days_list = pad(doses), pad(freqs), pad(days_list)

        return [
            {
                "drug_name": name,
                "dose_per_intake": d,
                "daily_frequency": int(f),
                "total_days": int(dy),
            }
            for name, d, f, dy in zip(drug_names, doses, freqs, days_list)
        ]

    @staticmethod
    def _parse_interleaved_layout(lines: list[str]) -> list[dict]:
        """인터리브형 처방전 파싱.

        헤더(일수/횟수/투약량/약품명)가 연속으로 나열된 후,
        약품명 직전에 해당 약품의 숫자값들이 나열되는 구조를 처리한다.
        """
        _NUM_RE = re.compile(r"^\d+\.?\d*$")
        _HEADER_KEYWORDS = {"일수", "횟수", "투약량", "약품명"}

        # 헤더 블록 끝 위치 탐색
        header_end = 0
        in_header = False
        for i, line in enumerate(lines):
            if line.strip() in _HEADER_KEYWORDS:
                in_header = True
                header_end = i + 1
            elif in_header:
                break

        if header_end == 0:
            return []

        def assign_freq_days(ints: list[int]) -> tuple[int, int]:
            """정수 2개를 횟수/일수로 매핑. 5 이상이면 일수, 미만이면 횟수."""
            a, b = sorted(ints)
            return (int(b), int(a)) if a >= 5 else (int(b), int(a)) if b >= 5 else (int(b), int(a))

        def _assign(ints: list[int]) -> tuple[int, int]:
            a, b = sorted(ints)
            if b >= 5:
                return int(a), int(b)  # 횟수=a, 일수=b
            return int(b), int(a)  # 횟수=b, 일수=a

        results: list[dict] = []
        pending_nums: list[float] = []

        for line in lines[header_end:]:
            stripped = line.strip()
            drug_m = _DRUG_SUFFIX_RE.match(stripped)
            if drug_m:
                if len(pending_nums) >= 3:
                    nums = pending_nums[-3:]
                    float_vals = [n for n in nums if n != int(n)]
                    int_vals = [int(n) for n in nums if n == int(n)]
                    if float_vals:
                        dose = float_vals[0]
                        remaining = [int(n) for n in nums if n != dose]
                        freq, days = _assign(remaining) if len(remaining) == 2 else (remaining[0], remaining[1] if len(remaining) > 1 else 0)
                    else:
                        sorted_nums = sorted(int_vals)
                        dose = float(sorted_nums[0])
                        freq, days = _assign(sorted_nums[1:])
                    results.append({
                        "drug_name": drug_m.group("name"),
                        "dose_per_intake": dose,
                        "daily_frequency": freq,
                        "total_days": days,
                    })
                pending_nums = []
            else:
                for t in stripped.split():
                    if _NUM_RE.match(t):
                        pending_nums.append(float(t))

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
        """boundingPoly 좌표 기반으로 단어를 줄 단위로 재구성.

        세로 촬영 이미지(x 범위 >> y 범위)는 x/y를 교환해 처리한다.
        """
        if not fields:
            return ""

        all_x = [int(f.get("boundingPoly", {}).get("vertices", [{}])[0].get("x", 0)) for f in fields]
        all_y = [int(f.get("boundingPoly", {}).get("vertices", [{}])[0].get("y", 0)) for f in fields]
        rotated = (max(all_x) - min(all_x)) > (max(all_y) - min(all_y)) * 1.5

        groups: dict[int, list[tuple[int, str]]] = defaultdict(list)
        for field in fields:
            vertices = field.get("boundingPoly", {}).get("vertices", [{}])
            raw_x = int(vertices[0].get("x", 0))
            raw_y = int(vertices[0].get("y", 0))
            row_key, col_key = (raw_x, raw_y) if rotated else (raw_y, raw_x)
            groups[row_key].append((col_key, field.get("inferText", "")))

        row_keys = sorted(groups.keys())
        gaps = [row_keys[i + 1] - row_keys[i] for i in range(len(row_keys) - 1) if row_keys[i + 1] > row_keys[i]]
        dynamic_threshold = int(min(gaps) * 0.8) if gaps else threshold

        merged: list[list[tuple[int, str]]] = []
        current: list[tuple[int, str]] = list(groups[row_keys[0]])
        current_key = row_keys[0]

        for key in row_keys[1:]:
            if abs(key - current_key) <= dynamic_threshold:
                current.extend(groups[key])
            else:
                merged.append(sorted(current, key=lambda t: t[0]))
                current = list(groups[key])
            current_key = key
        if current:
            merged.append(sorted(current, key=lambda t: t[0]))

        if rotated:
            merged = merged[::-1]

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
