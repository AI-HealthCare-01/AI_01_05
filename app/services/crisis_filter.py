"""위기 감지 2중 안전장치 모듈.

1단계: Regex 키워드 매칭 (LLM 호출 전) - 감지 시 LLM 생략
2단계: LLM Structured Output 판단 - is_flagged=True 시 위기 처리
"""

import re
from dataclasses import dataclass

# ── 위기 키워드 정의 ─────────────────────────────────────────
# 1단계 감지 시 LLM 호출 완전 생략
IMMEDIATE_CRISIS_KEYWORDS: list[str] = [
    "자살",
    "자해",
    "죽고싶",
    "죽고 싶",
    "죽어버리",
    "목매",
    "투신",
    "약을 많이 먹",
    "overdose",
    "사라지고싶",
    "사라지고 싶",
    "없어지고싶",
    "없어지고 싶",
    "끝내고싶",
    "끝내고 싶",
]

# 추가 위기 키워드 (LLM 판단 참고용, 1단계에서는 미감지)
EXTENDED_CRISIS_KEYWORDS: dict[str, list[str]] = {
    "Direct": [
        "죽을래",
        "죽겠",
        "목숨",
        "유서",
        "손목을 긋",
        "극단적 선택",
        "스스로 목숨",
    ],
    "Indirect": [
        "살기 싫",
        "삶이 의미 없",
        "다 끝내고 싶",
        "더 이상 못 버티",
        "포기하고 싶",
        "힘들어서 못 살",
        "세상에 나 혼자",
        "아무도 나를",
    ],
    "Substance": [
        "약 한꺼번에",
        "약물 과다",
        "수면제 많이",
        "진통제 많이",
        "약으로 죽",
        "음독",
        "과량 복용",
    ],
}

CRISIS_RESPONSE_MESSAGE = (
    "지금 많이 힘드시군요. 그 마음이 느껴져요.\n\n"
    "혼자 감당하기 너무 힘들 때는 전문가와 이야기 나눠보는 것도 큰 도움이 돼요. "
    "언제든지 연락할 수 있는 곳이 있어요.\n\n"
    "- 자살예방상담전화: 1393 (24시간)\n"
    "- 정신건강위기상담전화: 1577-0199\n"
    "- 생명의전화: 1588-9191\n\n"
    "지금 어떤 상황인지 조금 더 이야기해 주실 수 있어요? "
    "제가 곁에서 들을게요."
)


@dataclass
class CrisisResult:
    """위기 감지 결과."""

    is_crisis: bool  # 위기 상황 여부
    should_skip_llm: bool  # True면 LLM 호출 생략하고 즉시 CRISIS_DETECTED 반환
    alert_type: str | None = None  # Direct, Indirect, Substance
    matched_keyword: str | None = None  # 감지된 키워드


def check_immediate_crisis(text: str) -> CrisisResult:
    """1단계: 즉시 감지 키워드 체크.

    감지 시 LLM 호출 없이 바로 위기 응답 반환.
    """
    normalized = text.replace(" ", "").lower()

    for keyword in IMMEDIATE_CRISIS_KEYWORDS:
        pattern = re.escape(keyword.replace(" ", "").lower())
        if re.search(pattern, normalized):
            # 키워드로 alert_type 추론
            alert_type = _infer_alert_type(keyword)
            return CrisisResult(
                is_crisis=True,
                should_skip_llm=True,
                alert_type=alert_type,
                matched_keyword=keyword,
            )

    return CrisisResult(is_crisis=False, should_skip_llm=False)


def check_extended_crisis(text: str) -> CrisisResult:
    """확장 위기 키워드 체크 (1단계 미감지 시 참고용).

    LLM 호출은 진행하되, 감지 시 LLM 판단과 함께 고려.
    """
    normalized = text.replace(" ", "").lower()

    for alert_type, keywords in EXTENDED_CRISIS_KEYWORDS.items():
        for keyword in keywords:
            pattern = re.escape(keyword.replace(" ", "").lower())
            if re.search(pattern, normalized):
                return CrisisResult(
                    is_crisis=True,
                    should_skip_llm=False,  # LLM 호출은 진행
                    alert_type=alert_type,
                    matched_keyword=keyword,
                )

    return CrisisResult(is_crisis=False, should_skip_llm=False)


def _infer_alert_type(keyword: str) -> str:
    """키워드로부터 alert_type 추론."""
    substance_keywords = ["약을 많이 먹", "overdose"]
    indirect_keywords = ["사라지고싶", "사라지고 싶", "없어지고싶", "없어지고 싶", "끝내고싶", "끝내고 싶"]

    if any(k in keyword for k in substance_keywords):
        return "Substance"
    if any(k in keyword for k in indirect_keywords):
        return "Indirect"
    return "Direct"


def check(text: str) -> CrisisResult:
    """위기 감지 메인 함수.

    1단계 즉시 감지 → 2단계 확장 감지 순서로 체크.
    """
    # 1단계: 즉시 감지 (LLM 생략 대상)
    result = check_immediate_crisis(text)
    if result.is_crisis:
        return result

    # 2단계: 확장 감지 (LLM 호출은 진행, 참고용)
    return check_extended_crisis(text)
