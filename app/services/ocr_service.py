from __future__ import annotations

import json
import re
import uuid
from collections import defaultdict
from collections.abc import Callable

import httpx

from app.core import config
from app.dtos.ocr_dto import OcrParsedItem, ParsedPrescriptionResponse
from app.models.medicine import Medicine

_NOISE_KEYWORDS = [
    "조제",
    "복약지도",
    "보험",
    "환자명",
    "병원명",
    "전화번호",
    "약품명",
    "약품사진",
    "복약안내",
    "총수납금액",
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
_PATTERN_TRAILING_NUMS = re.compile(r"\b(?P<dose>\d+\.?\d*)\s+(?P<freq>\d+)\s+(?P<days>\d+)\s*(?:[^\d\n].*)?$")
# 패턴: "1일 N회 N일분" 형식
_PATTERN_DAILY_DOSE = re.compile(r"1일\s*(?P<freq>\d+)회.*?(?P<days>\d+)일분")
# 패턴 5: 다중 약품 한 줄
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
    ("밀양디세텔", "일양디세텔"),
    ("사이돕신", "사이톱신"),
    ("사이옵신", "사이톱신"),
    ("베이제", "베아제"),
]
# 레이블 패턴에서 노이즈 약품명 필터
_LABEL_NOISE_RE = re.compile(r"약제비|수납금액|총액|본인부담|보험자")
_DOSE_STRIP = re.compile(r"\d+(\.\d+)?(밀리그램|그램|밀리리터|mg|g|ml)", re.IGNORECASE)
# 의약품 접미사 포함 여부 — 병합 조건 제한용
_DRUG_NAME_START_RE = re.compile(r"^[가-힣a-zA-Z0-9].*?(정|캡슐|액|크림|연고|주|산|시럽|패치|주사|주사제|주사액|제|환)")
# 약품명 접미사 추출용
# - 반드시 한글로 시작
# - 접미사(정/캡슐/액/크림/연고/시럽/패치/주사) 포함
# - 접미사 뒤 숫자/영문/밀리그램/그램/밀리리터 허용 (예: 오메크라정625밀리그램)
# - 산/제 제외: 클라불란산칼륨 같은 성분명 오매칭 방지
_DRUG_SUFFIX_RE = re.compile(
    r"(?P<name>[가-힣][가-힣a-zA-Z0-9%\.]*"
    r"(?:정|캡슐|액|크림|연고|시럽|패치|주사|주사제|주사액|서방)"
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
                items.append(
                    OcrParsedItem(
                        item_seq=matched.get("item_seq"),
                        item_name=matched.get("item_name", cleaned),
                        dose_per_intake=entry["dose_per_intake"],
                        daily_frequency=entry["daily_frequency"],
                        total_days=entry["total_days"],
                        confidence="HIGH",
                    )
                )

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

    @staticmethod
    def _filter_lines(lines: list[str]) -> list[str]:
        return [
            line
            for line in lines
            if not any(kw in line for kw in _NOISE_ONLY_KEYWORDS)
            and not _NOISE_LINE_RE.search(line)
            and not (_DRUG_SUFFIX_RE.search(line) is None and any(kw in line for kw in _NOISE_HEADER_KEYWORDS))
        ]

    def _detect_layout(self, filtered: list[str]) -> list[dict]:
        """패턴 6/7 레이아웃 감지 후 파싱 결과 반환. 미감지 시 빈 리스트."""
        col_result = self._parse_column_layout(filtered)
        if col_result:
            return col_result
        return self._parse_interleaved_layout(filtered)

    @staticmethod
    def _parse_inline_pattern(filtered: list[str]) -> list[dict]:
        return [
            {
                "drug_name": m.group("name"),
                "dose_per_intake": float(m.group("dose")),
                "daily_frequency": int(m.group("freq")),
                "total_days": int(m.group("days")),
            }
            for line in filtered
            if (m := _PATTERN_INLINE.match(line))
        ]

    @staticmethod
    def _try_label_match(filtered: list[str], i: int) -> tuple[re.Match | None, int]:
        """인덱스 i에서 레이블 인라인 패턴 매칭 시도. (match, 소비한 줄 수) 반환."""
        line = filtered[i]
        m = _PATTERN_LABEL_INLINE.match(line)
        if m:
            return m, 0
        if not _DRUG_NAME_START_RE.match(line):
            return None, 0
        for extra in range(1, 7):
            if i + extra < len(filtered):
                merged = " ".join(filtered[i : i + extra + 1])
                m = _PATTERN_LABEL_INLINE.match(merged)
                if m:
                    return m, extra
        return None, 0

    @staticmethod
    def _parse_label_pattern(filtered: list[str]) -> list[dict]:
        results: list[dict] = []
        i = 0
        while i < len(filtered):
            m, consumed = OcrService._try_label_match(filtered, i)
            if m:
                name = m.group("name")
                if not _LABEL_NOISE_RE.search(name):
                    results.append(
                        {
                            "drug_name": name,
                            "dose_per_intake": float(m.group("dose")),
                            "daily_frequency": int(m.group("freq")),
                            "total_days": int(m.group("days")),
                        }
                    )
                    i += consumed + 1
                else:
                    i += 1
            else:
                i += 1
        return results

    @staticmethod
    def _parse_multi_drug_line(line: str) -> list[dict]:
        if not _PATTERN_MULTI_DRUG.match(line):
            return []
        tokens = line.split()
        names = [t for t in tokens if re.match(r"^[가-힣]", t) and _DRUG_SUFFIX_RE.search(t)]
        nums = [t for t in tokens if re.match(r"^\d+\.?\d*$", t)]
        n = len(names)
        if n < 2 or len(nums) != n * 3:
            return []
        return [
            {
                "drug_name": name,
                "dose_per_intake": float(d),
                "daily_frequency": int(f),
                "total_days": int(dy),
            }
            for name, d, f, dy in zip(names, nums[:n], nums[n : n * 2], nums[n * 2 :], strict=True)
        ]

    @staticmethod
    def _parse_trailing_nums_pattern(filtered: list[str]) -> list[dict]:
        results: list[dict] = []
        pending_name: str | None = None
        pending_since: int = 0
        for i, line in enumerate(filtered):
            nums_m = _PATTERN_TRAILING_NUMS.search(line)
            if nums_m and pending_name and (i - pending_since) <= 3:
                results.append(
                    {
                        "drug_name": pending_name,
                        "dose_per_intake": float(nums_m.group("dose")),
                        "daily_frequency": int(nums_m.group("freq")),
                        "total_days": int(nums_m.group("days")),
                    }
                )
                pending_name = None
                continue
            name_m = _DRUG_SUFFIX_RE.search(line)
            if name_m and not nums_m:
                pending_name = name_m.group("name")
                pending_since = i
            elif pending_name and (i - pending_since) > 3:
                pending_name = None
        return results

    @staticmethod
    def _parse_fallback_label(filtered: list[str]) -> list[dict]:
        full_text = "\n".join(filtered)
        dose_m = _PATTERN_DOSE.search(full_text)
        freq_m = _PATTERN_FREQ.search(full_text)
        days_m = _PATTERN_DAYS.search(full_text)
        if not (dose_m and freq_m and days_m):
            return []
        return [
            {
                "drug_name": filtered[0] if filtered else "",
                "dose_per_intake": float(dose_m.group(1)),
                "daily_frequency": int(freq_m.group(1)),
                "total_days": int(days_m.group(1)),
            }
        ]

    def _parse_prescription_text(self, lines: list[str]) -> list[dict]:
        expanded = self._expand_multi_drug_lines(lines)
        normalized = [self._normalize_drug_line(line) for line in expanded]
        filtered = self._filter_lines(normalized)

        result = self._parse_inline_pattern(filtered)
        if result:
            return result

        result = self._parse_label_pattern(filtered)
        if result:
            return result

        result = self._detect_layout(filtered)
        if result:
            return result

        for line in filtered:
            result = self._parse_multi_drug_line(line)
            if result:
                return result

        result = self._parse_trailing_nums_pattern(filtered)
        if result:
            return result

        result = self._parse_split_nums_pattern(filtered)
        if result:
            return result

        result = self._parse_daily_dose_pattern(filtered)
        if result:
            return result

        return self._parse_fallback_label(filtered)

    @staticmethod
    def _parse_daily_dose_pattern(filtered: list[str]) -> list[dict]:
        """'1일 N회 N일분' 패턴에서 약품명 + 투약정보 추출.

        8.jpeg: 약품명 목록 + '1일 2회 2일분' 형식.
        """
        full_text = "\n".join(filtered)
        m = _PATTERN_DAILY_DOSE.search(full_text)
        if not m:
            return []
        freq = int(m.group("freq"))
        days = int(m.group("days"))

        # 일수 콜럼에서 수집된 숫자로 일수 보완 (더 신뢰할 수 있는 경우)
        days_idx = next((i for i, line in enumerate(filtered) if line.strip() in ("일수", "밀수")), -1)
        if days_idx >= 0:
            num_re = re.compile(r"^\d+\.?\d*$")
            noise_num_re = re.compile(r"^([1-9]\d+|\d{3,}|\d+\.?\d*[\uAC00-\uD7A3a-zA-Z])")
            ordered_idxs: list[int] = []
            dose_idx, freq_idx, _ = OcrService._find_header_indices(filtered)
            if dose_idx >= 0:
                ordered_idxs.append(dose_idx)
            if freq_idx >= 0:
                ordered_idxs.append(freq_idx)
            ordered_idxs.append(days_idx)
            ordered_idxs = sorted(ordered_idxs)
            days_nums = OcrService._collect_header_nums(filtered, days_idx, ordered_idxs, num_re, noise_num_re, True)
            if days_nums:
                days = int(days_nums[0])

        noise_drug_re = re.compile(r"약제비|연간액|수납금액|총액|병원|환자|본인|전액|규정|연정|용액")
        drug_names = OcrService._filter_noise_tokens(OcrService._tokenize_lines(filtered), noise_drug_re)
        if not drug_names:
            return []
        return [
            {
                "drug_name": name,
                "dose_per_intake": 1.0,
                "daily_frequency": freq,
                "total_days": days,
            }
            for name in drug_names
        ]

    @staticmethod
    def _parse_split_nums_pattern(filtered: list[str]) -> list[dict]:
        """약품명 다음 줄에 숫자 3개가 각각 분리된 패턴 처리.

        7.jpg 하단 테이블: 약품명 / 숫자1 / 숫자2 / 숫자3 순서.
        숫자 순서는 (일수, 투약량, 횟수) 또는 (투약량, 횟수, 일수)를 휴리스틱으로 판별.
        """
        num_re = re.compile(r"^\d+\.?\d*$")
        expand_re = re.compile(r"^\d+$")
        results: list[dict] = []
        i = 0
        while i < len(filtered):
            line = filtered[i]
            drug_m = _DRUG_SUFFIX_RE.match(line)
            if not drug_m:
                i += 1
                continue
            # 다음 줄들에서 숫자 3개 수집 (최대 5줄 내)
            nums: list[float] = []
            j = i + 1
            while j < len(filtered) and len(nums) < 3 and (j - i) <= 5:
                tokens = filtered[j].split()
                # 두 자리 숫자 분리 (15 → 1, 5 / 35 → 3, 5)
                expanded: list[str] = []
                for t in tokens:
                    if expand_re.match(t) and len(t) == 2 and all(c != "0" for c in t):
                        expanded.extend(list(t))
                    else:
                        expanded.append(t)
                line_nums = [float(t) for t in expanded if num_re.match(t)]
                if line_nums and not _DRUG_SUFFIX_RE.match(filtered[j]):
                    nums.extend(line_nums)
                elif _DRUG_SUFFIX_RE.match(filtered[j]):
                    break
                j += 1
            if len(nums) >= 3:
                nums = nums[:3]
                float_vals = [n for n in nums if n != int(n)]
                int_vals = [int(n) for n in nums if n == int(n)]
                if float_vals:
                    dose = float_vals[0]
                    remaining = [int(n) for n in nums if n != dose]
                    freq, days = (
                        OcrService._assign_freq_days(remaining)
                        if len(remaining) == 2
                        else (remaining[0], remaining[1] if len(remaining) > 1 else 0)
                    )
                else:
                    sorted_nums = sorted(int_vals)
                    dose = float(sorted_nums[0])
                    freq, days = OcrService._assign_freq_days(sorted_nums[1:])
                results.append(
                    {
                        "drug_name": drug_m.group("name"),
                        "dose_per_intake": dose,
                        "daily_frequency": freq,
                        "total_days": days,
                    }
                )
                i = j
            else:
                i += 1
        return results

    @staticmethod
    def _expand_multi_drug_lines(lines: list[str]) -> list[str]:
        """한 줄에 여러 약품명이 있는 경우 분리.

        예: '휴니즈레바미피드정_(0.1g/1정) 글로덱시정300mg(덱시부프로펜)'
        → ['휴니즈레바미피드정_(0.1g/1정)', '글로덱시정300mg(덱시부프로펜)']
        """
        result: list[str] = []
        for line in lines:
            # 약품명 접미사가 줄 안에 2개 이상 있는지 확인
            matches = list(_DRUG_SUFFIX_RE.finditer(line))
            if len(matches) >= 2:
                # 두 번째 약품명 시작 위치에서 분리
                split_pos = matches[1].start()
                result.append(line[:split_pos].rstrip())
                result.append(line[split_pos:])
            else:
                result.append(line)
        return result

    @staticmethod
    def _normalize_drug_line(line: str) -> str:
        """줄 단위 전처리: 접두 노이즈 제거, 괄호 이후 성분명 절단, 오타 교정."""
        # "비)복합파자임이중정" → "복합파자임이중정": 약품명 접미사 앞에 짧은 접두 노이즈 제거
        m = _DRUG_SUFFIX_RE.search(line)
        if m and m.start() > 0 and m.start() <= 4 and not _DRUG_SUFFIX_RE.search(line[: m.start()]):
            line = line[m.start() :]
        # 약품명 접미사 뒤 괄호 성분명 절단: "잘레톤정(잘토프로팬)_(80" → "잘레톤정"
        m = _DRUG_SUFFIX_RE.match(line)
        if m and "(" in line:
            paren_pos = line.find("(", m.start())
            if paren_pos != -1:
                line = line[:paren_pos].rstrip("_( ")
        # "1.0035" → "1.00 35": 소수점 숫자에 정수가 붙어있는 경우 분리
        line = re.sub(r"(\d+\.\d+)(\d{2,})", r"\1 \2", line)
        # 단독 토큰 "3회" → "3", "5일분" → "5" (레이블 패턴 내 키워드는 유지)
        if re.match(r"^\d+회$", line.strip()):
            line = re.sub(r"(\d+)회", r"\1", line)
        if re.match(r"^\d+일분$", line.strip()):
            line = re.sub(r"(\d+)일분", r"\1", line)
        # 오타 교정
        for typo, correct in _TYPO_MAP:
            line = line.replace(typo, correct)
        return line

    @staticmethod
    def _tokenize_lines(lines: list[str]) -> list[list[str]]:
        return [line.split() for line in lines]

    @staticmethod
    def _filter_noise_tokens(token_rows: list[list[str]], noise_drug_re: re.Pattern) -> list[str]:
        """전체 토큰 중 약품명 접미사 포함 + 노이즈 아닌 것만 반환. 최소 3자 이상, 중복 제거."""
        seen: set[str] = set()
        result: list[str] = []
        for tokens in token_rows:
            for t in tokens:
                m = _DRUG_SUFFIX_RE.match(t)
                if m and not noise_drug_re.search(t) and len(m.group("name")) >= 3:
                    name = m.group("name")
                    if name not in seen:
                        seen.add(name)
                        result.append(name)
        return result

    @staticmethod
    def _expand_numeric_tokens(tokens: list[str], num_re: re.Pattern) -> list[str]:
        """두 자리 숫자(각 자리 1-9)를 개별 자리로 분리. 3자리 이상(금액 등)는 noise_num_re로 이미 필터됨."""
        result: list[str] = []
        for t in tokens:
            if num_re.match(t) and len(t) > 1 and "." not in t and all(c != "0" for c in t):
                result.extend(list(t))
            else:
                result.append(t)
        return result

    @staticmethod
    def _extract_line_nums(
        tokens: list[str],
        num_re: re.Pattern,
        noise_num_re: re.Pattern,
    ) -> list[float]:
        result: list[float] = []
        for i, t in enumerate(tokens):
            if not num_re.match(t) or noise_num_re.match(t):
                continue
            if i + 1 < len(tokens) and re.match(r"^[\uAC00-\uD7A3]", tokens[i + 1]):
                continue
            result.append(float(t))
        return result

    @staticmethod
    def _find_header_indices(lines: list[str]) -> tuple[int, int, int]:
        """투약량/횟수/일수 헤더 줄 인덱스 반환. 헤더 순서 무관하게 탐색."""
        dose_idx = freq_idx = days_idx = -1
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped == "투약량" and dose_idx == -1:
                dose_idx = i
            elif stripped == "횟수" and freq_idx == -1:
                freq_idx = i
            elif stripped in ("일수", "밀수") and days_idx == -1:  # 밀수: 일수 OCR 오인식
                days_idx = i
        return dose_idx, freq_idx, days_idx

    @staticmethod
    def _collect_forward_nums(
        lines: list[str],
        header_idx: int,
        next_idx: int,
        _nums: Callable[[str], list[float]],
        max_count: int,
    ) -> list[float]:
        """헤더 이후 숫자 순방향 수집."""
        result: list[float] = []
        for line in lines[header_idx + 1 : next_idx]:
            for n in _nums(line):
                has_float = any(x != int(x) for x in result)
                if max_count > 0 and has_float and n == int(n):
                    continue
                result.append(n)
            if max_count > 0 and len(result) >= max_count:
                break
        return result

    @staticmethod
    def _collect_backward_nums(
        lines: list[str],
        header_idx: int,
        ordered_idxs: list[int],
        _nums: Callable[[str], list[float]],
        max_count: int,
    ) -> list[float]:
        """헤더 이전 숫자 역방향 탐색."""
        prev_idx = next((j for j in reversed(ordered_idxs) if j < header_idx), -1)
        start = prev_idx + 1 if prev_idx >= 0 else max(0, header_idx - 20)
        result: list[float] = []
        for line in lines[start:header_idx]:
            result.extend(_nums(line))
        return result[-max_count:] if max_count > 0 else result

    @staticmethod
    def _collect_header_nums(
        lines: list[str],
        header_idx: int,
        ordered_idxs: list[int],
        num_re: re.Pattern,
        noise_num_re: re.Pattern,
        expand: bool = False,
        max_count: int = 0,
    ) -> list[float]:
        """헤더 다음 숫자 수집. max_count > 0이면 최대 max_count개만 수집."""

        def _nums(line: str) -> list[float]:
            tokens = line.split()
            if expand:
                tokens = OcrService._expand_numeric_tokens(tokens, num_re)
            return OcrService._extract_line_nums(tokens, num_re, noise_num_re)

        inline = _nums(lines[header_idx])
        if inline:
            return inline
        next_idx = next((j for j in ordered_idxs if j > header_idx), len(lines))
        result = OcrService._collect_forward_nums(lines, header_idx, next_idx, _nums, max_count)
        if not result:
            result = OcrService._collect_backward_nums(lines, header_idx, ordered_idxs, _nums, max_count)
        return result[:max_count] if max_count > 0 else result

    @staticmethod
    def _parse_column_layout(lines: list[str]) -> list[dict]:
        """컬럼 분리형 처방전 파싱."""
        num_re = re.compile(r"^\d+\.?\d*$")
        # 금액성 큰 숫자(3자리 이상 정수 또는 10 이상 정수) 및 한글/영문 접미 숫자 제외
        noise_num_re = re.compile(r"^(\d{3,}|[1-9]\d+|\d+\.?\d*[\uAC00-\uD7A3a-zA-Z])")
        noise_drug_re = re.compile(r"약제비|연간액|수납금액|총액|병원|환자|본인|전액|규정|연정|용액")

        dose_idx, freq_idx, days_idx = OcrService._find_header_indices(lines)
        if dose_idx == -1 or freq_idx == -1 or days_idx == -1:
            return []

        ordered_idxs = sorted([dose_idx, freq_idx, days_idx])

        drug_names = OcrService._filter_noise_tokens(OcrService._tokenize_lines(lines), noise_drug_re)
        n = len(drug_names)
        if n == 0:
            return []

        def collect_n(header_idx: int, expand: bool = False) -> list[float]:
            return OcrService._collect_header_nums(
                lines, header_idx, ordered_idxs, num_re, noise_num_re, expand, max_count=n
            )

        doses = collect_n(dose_idx)
        freqs = collect_n(freq_idx, expand=True)
        days_list = collect_n(days_idx)

        if not doses or not freqs or not days_list:
            return []

        def pad(lst: list[float]) -> list[float]:
            return (lst + [lst[-1]] * (n - len(lst)))[:n]

        doses, freqs, days_list = pad(doses), pad(freqs), pad(days_list)
        return [
            {
                "drug_name": name,
                "dose_per_intake": d,
                "daily_frequency": int(f),
                "total_days": int(dy),
            }
            for name, d, f, dy in zip(drug_names, doses, freqs, days_list, strict=True)
        ]

    @staticmethod
    def _find_header_end(lines: list[str], header_keywords: set[str]) -> int:
        header_end = 0
        in_header = False
        for i, line in enumerate(lines):
            if line.strip() in header_keywords:
                in_header = True
                header_end = i + 1
            elif in_header:
                break
        return header_end

    @staticmethod
    def _assign_freq_days(ints: list[int]) -> tuple[int, int]:
        """2개 정수를 횟수/일수로 매핑. b >= 5이면 일수, 아니면 횟수."""
        a, b = sorted(ints)
        if b >= 5:
            return int(a), int(b)
        return int(b), int(a)

    @staticmethod
    def _build_interleaved_item(drug_name: str, pending_nums: list[float]) -> dict:
        nums = pending_nums[-3:]
        float_vals = [n for n in nums if n != int(n)]
        int_vals = [int(n) for n in nums if n == int(n)]
        if float_vals:
            dose = float_vals[0]
            remaining = [int(n) for n in nums if n != dose]
            freq, days = (
                OcrService._assign_freq_days(remaining)
                if len(remaining) == 2
                else (remaining[0], remaining[1] if len(remaining) > 1 else 0)
            )
        else:
            sorted_nums = sorted(int_vals)
            dose = float(sorted_nums[0])
            freq, days = OcrService._assign_freq_days(sorted_nums[1:])
        return {
            "drug_name": drug_name,
            "dose_per_intake": dose,
            "daily_frequency": freq,
            "total_days": days,
        }

    @staticmethod
    def _parse_interleaved_layout(lines: list[str]) -> list[dict]:
        """인터리브형 처방전 파싱."""
        num_re = re.compile(r"^\d+\.?\d*$")
        header_keywords = {"일수", "횟수", "투약량", "약품명"}

        header_end = OcrService._find_header_end(lines, header_keywords)
        if header_end == 0:
            return []

        results: list[dict] = []
        pending_nums: list[float] = []

        for line in lines[header_end:]:
            stripped = line.strip()
            drug_m = _DRUG_SUFFIX_RE.match(stripped)
            if drug_m:
                if len(pending_nums) >= 3:
                    results.append(OcrService._build_interleaved_item(drug_m.group("name"), pending_nums))
                pending_nums = []
            else:
                pending_nums.extend(float(t) for t in stripped.split() if num_re.match(t))

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
        results = (
            await Medicine.filter(search_keyword__startswith=cleaned_name, is_active=True)
            .limit(10)
            .values("item_seq", "item_name", "entp_name")
        )
        if results:
            return list(results)

        base_name = _DOSE_STRIP.sub("", cleaned_name).strip()
        if base_name == cleaned_name:
            return []
        results = (
            await Medicine.filter(search_keyword__startswith=base_name, is_active=True)
            .limit(10)
            .values("item_seq", "item_name", "entp_name")
        )
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

        message = json.dumps(
            {
                "version": "V2",
                "requestId": str(uuid.uuid4()),
                "timestamp": 0,
                "images": [{"format": file_type.split("/")[-1], "name": "prescription"}],
            }
        )
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
