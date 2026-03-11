# crisis-filter Design Document

> **Summary**: 입출력 양방향 위기 감지 필터 상세 설계 — 키워드 확장(30→50+) + 출력 안전 검사 + 구조화 로깅 + pytest 테스트
>
> **Project**: DodakTalk (도닥톡)
> **Version**: v1.0.0
> **Author**: Team AI-HealthCare
> **Date**: 2026-03-09
> **Status**: Draft
> **Planning Doc**: [crisis-filter.plan.md](../../01-plan/features/crisis-filter.plan.md)

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | 현재 위기 필터는 사용자 입력만 검사(30개 키워드)하며, LLM 출력 내 위험 표현(금기, 치명적 부작용)은 무검사 통과하고 은유적 위기 표현이 필터를 우회함 |
| **Solution** | 입력 키워드 50+개 확장(은유적 표현 포함) + `check_response_safety()` 출력 필터 신규 구현 + 구조화 로깅으로 양방향 안전망 구축 |
| **Function/UX Effect** | 은유적 위기 표현("영원히 잠들고 싶어") 감지율 95%+ 달성, LLM 답변 내 금기/위험 키워드 감지 시 `warning_level` 자동 상향 + `red_alert=True` |
| **Core Value** | 입력·출력 양방향 이중 안전망으로 사용자 안전 사각지대 완전 제거 |

---

## 1. Overview

### 1.1 Design Goals

- 기존 `check_safety()` 함수의 키워드를 30개에서 50개 이상으로 확장하여 은유적/우회 표현까지 포괄
- LLM 출력을 검사하는 `check_response_safety()` 함수를 신규 구현하여 양방향 필터링 달성
- 위기 이벤트를 구조화된 로깅으로 기록하여 법적 근거 확보
- 모든 필터 로직에 대한 pytest 단위 테스트로 정탐률 > 95%, 오탐률 < 5% 보장

### 1.2 Design Principles

- **Fail-Safe First**: 의심스러운 표현은 놓치는 것보다 오탐이 낫다 (안전 우선)
- **Non-Blocking Output Filter**: 출력 필터는 답변을 차단하지 않고 `warning_level`만 상향 (정보 접근권 보장)
- **Zero External Dependency**: 키워드 매칭 기반, 추가 ML 모델 불필요 (지연 시간 < 10ms)
- **Testability**: 모든 필터 함수는 순수 함수로 설계하여 단위 테스트 용이

---

## 2. Architecture

### 2.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  chatbot_engine.py                                               │
│                                                                   │
│  ┌───────────────────┐                                           │
│  │  CRISIS_KEYWORDS   │  30 → 50+ 키워드 확장                   │
│  │  (Direct/Indirect/ │  + Context 카테고리 신규                 │
│  │   Substance/Context)│                                         │
│  └────────┬──────────┘                                           │
│           │                                                       │
│           ▼                                                       │
│  ┌───────────────────┐     위기 감지 → LLM 생략, 1393 반환      │
│  │  check_safety()   │──────────────────────────────────────┐    │
│  │  (입력 필터)       │                                      │    │
│  └────────┬──────────┘                                      │    │
│           │ 미감지                                           │    │
│           ▼                                                  │    │
│  ┌───────────────────┐                                      │    │
│  │  LLM (GPT-4o-mini)│                                      │    │
│  └────────┬──────────┘                                      │    │
│           │                                                  │    │
│           ▼                                                  │    │
│  ┌─────────────────────────┐  위험 감지 → warning_level 상향 │    │
│  │  check_response_safety()│  + red_alert=True               │    │
│  │  (출력 필터 — 신규)      │                                 │    │
│  └────────┬────────────────┘                                 │    │
│           │                                                  │    │
│           ▼                                                  ▼    │
│  ┌───────────────────┐                                           │
│  │  crisis_logger     │  구조화 로깅 (입력/출력 위기 이벤트)     │
│  └───────────────────┘                                           │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow (양방향 필터 파이프라인)

```
사용자 입력 (message)
    │
    ▼
[입력 필터] check_safety(message)
    │
    ├─ 위기 감지 ──▶ CRISIS_RESPONSE + red_alert=True
    │                   + alert_type (Direct/Indirect/Substance/Context)
    │                   + crisis_logger.log_input_crisis()
    │                   ★ LLM 호출 생략
    │
    └─ 미감지 ──▶ LLM 호출 (GPT-4o-mini)
                    │
                    ▼
               [출력 필터] check_response_safety(answer)
                    │
                    ├─ 위험 감지 ──▶ warning_level="Critical"
                    │                + red_alert=True
                    │                + crisis_logger.log_output_danger()
                    │                ★ 답변은 그대로 전달 (차단 안 함)
                    │
                    └─ 미감지 ──▶ warning_level 유지 (Normal/Caution)
                                    │
                                    ▼
                              ChatResponse 반환 + ChatLog DB 저장
```

### 2.3 Dependencies

| Component | Depends On | Purpose |
|-----------|-----------|---------|
| `check_safety()` | `CRISIS_KEYWORDS`, `re` | 입력 위기 키워드 매칭 |
| `check_response_safety()` | `RESPONSE_DANGER_KEYWORDS` | 출력 위험 키워드 매칭 |
| `crisis_logger` | `logging` (stdlib) | 구조화 위기 이벤트 로깅 |
| `chatbot_engine.py` | 위 3개 모듈 | 파이프라인 통합 |
| `chatbot.py` (Router) | `ChatLog` model | alert_type DB 저장 |

---

## 3. Data Model

### 3.1 ChatLog 모델 확장

```python
# app/models/chat.py — 확장 필드 추가
class ChatLog(models.Model):
    id = fields.IntField(primary_key=True)
    user_id = fields.IntField(index=True)
    message_content = fields.TextField()
    response_content = fields.TextField()
    is_flagged = fields.BooleanField(default=False)
    alert_type = fields.CharField(max_length=20, null=True)       # 신규: Direct/Indirect/Substance/Context
    warning_level = fields.CharField(max_length=20, default="Normal")  # 신규: Normal/Caution/Critical
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "chat_logs"
```

### 3.2 ChatLog.create() 호출 변경

```python
# app/apis/v1/chatbot.py — alert_type, warning_level 저장 추가
await ChatLog.create(
    user_id=1,  # TODO: 카카오 user_id 연동 시 교체
    message_content=request.message,
    response_content=result["answer"],
    is_flagged=result["red_alert"],
    alert_type=result["alert_type"],          # 신규
    warning_level=result["warning_level"],    # 신규
)
```

---

## 4. Module Design

### 4.1 입력 키워드 확장 (FR-02)

**기존 30개 → 확장 50+개**

```python
CRISIS_KEYWORDS: dict[str, list[str]] = {
    "Direct": [
        # 기존 12개 유지
        "자살", "죽고 싶", "죽을래", "죽겠", "목숨", "유서",
        "목매", "투신", "손목을 긋", "극단적 선택", "스스로 목숨", "자해",
        # 확장 3개
        "생을 마감", "세상을 떠나", "스스로 끝내",
    ],
    "Indirect": [
        # 기존 10개 유지
        "사라지고 싶", "없어지고 싶", "살기 싫", "삶이 의미 없",
        "다 끝내고 싶", "더 이상 못 버티", "포기하고 싶",
        "힘들어서 못 살", "세상에 나 혼자", "아무도 나를",
        # 확장 6개
        "영원히 잠들고 싶", "이 세상이 싫", "아무 의미 없",
        "나만 없으면", "짐이 되고 싶지 않", "모두 다 떠나",
    ],
    "Substance": [
        # 기존 8개 유지
        "약 많이 먹", "약을 한꺼번에", "약물 과다", "수면제 많이",
        "진통제 많이", "약으로 죽", "음독", "과량 복용",
        # 확장 3개
        "약을 모아", "처방약 모아", "한 번에 다 먹",
    ],
    "Context": [
        # 신규 카테고리 — 문맥적 위기 표현
        "유서 써", "마지막 인사", "정리하고 떠나", "다음 생", "보험금",
    ],
}
```

**키워드 수 요약:**

| Category | 기존 | 추가 | 합계 |
|----------|------|------|------|
| Direct | 12 | 3 | 15 |
| Indirect | 10 | 6 | 16 |
| Substance | 8 | 3 | 11 |
| Context | 0 | 5 | 5 |
| **합계** | **30** | **17** | **47+** |

> 향후 운영 중 오탐/미탐 분석을 통해 지속적으로 키워드를 추가/제거한다.

### 4.2 출력 안전 검사 — `check_response_safety()` (FR-03, FR-04)

```python
RESPONSE_DANGER_KEYWORDS: dict[str, list[str]] = {
    "Contraindication": [
        "금기", "절대 금기", "병용 금기", "사용 금지",
        "같이 복용하면 안", "함께 사용 금지",
    ],
    "SevereEffect": [
        "심각한 부작용", "치명적", "생명 위험", "즉시 중단",
        "응급", "사망 위험", "생명을 위협",
    ],
    "Overdose": [
        "과량", "중독", "과다 복용 시", "치사량",
        "과다 투여", "용량 초과",
    ],
}


def check_response_safety(answer: str) -> dict | None:
    """LLM 답변 내 위험 키워드를 감지합니다.

    Args:
        answer: LLM이 생성한 답변 텍스트

    Returns:
        위험 감지 시 {"danger_type": str, "keyword": str} 딕셔너리,
        감지되지 않으면 None.
    """
    for danger_type, keywords in RESPONSE_DANGER_KEYWORDS.items():
        for keyword in keywords:
            if keyword in answer:
                return {"danger_type": danger_type, "keyword": keyword}
    return None
```

**설계 결정: 답변 차단 vs 경고만**

| 옵션 | 설명 | 선택 |
|------|------|------|
| 답변 차단 + 대체 메시지 | 위험 답변 숨기고 안전 메시지로 교체 | ❌ |
| **경고 레벨 상향만** | 답변은 그대로 전달, `warning_level="Critical"` + `red_alert=True` | ✅ |

**근거**: 약물 금기 정보는 사용자에게 중요한 안전 정보이므로 차단하면 안 됨. 프론트엔드에서 Red Alert UI로 시각적 강조만 추가.

### 4.3 파이프라인 통합 — `get_response()` 변경

```python
async def get_response(self, user_message, meds, user_note=None) -> dict:
    # Step 1: 입력 위기 필터 (기존 + 확장)
    safety = check_safety(user_message)
    if safety is not None:
        crisis_logger.log_input_crisis(
            message=user_message,
            alert_type=safety["alert_type"],
            keyword=safety["keyword"],
        )
        return {
            "answer": CRISIS_RESPONSE_MESSAGE,
            "warning_level": "Critical",
            "red_alert": True,
            "alert_type": safety["alert_type"],
        }

    # Step 2: LLM 호출
    answer = await self._call_llm(user_message, meds, user_note)

    # Step 3: 출력 안전 검사 (신규)
    danger = check_response_safety(answer)
    if danger is not None:
        crisis_logger.log_output_danger(
            answer_excerpt=answer[:200],
            danger_type=danger["danger_type"],
            keyword=danger["keyword"],
        )
        return {
            "answer": answer,
            "warning_level": "Critical",
            "red_alert": True,
            "alert_type": None,  # 출력 위험은 사용자 입력 유형이 아니므로 None
        }

    # Step 4: 정상 반환
    return {
        "answer": answer,
        "warning_level": "Caution" if meds else "Normal",
        "red_alert": False,
        "alert_type": None,
    }
```

### 4.4 구조화 로깅 — `crisis_logger` (FR-06)

```python
import logging

crisis_logger = logging.getLogger("dodaktalk.crisis")


def setup_crisis_logger() -> None:
    """위기 이벤트 전용 로거 설정."""
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s | CRISIS | %(levelname)s | %(message)s"
    )
    handler.setFormatter(formatter)
    crisis_logger.addHandler(handler)
    crisis_logger.setLevel(logging.WARNING)


def log_input_crisis(message: str, alert_type: str, keyword: str) -> None:
    """입력 위기 감지 이벤트 기록."""
    crisis_logger.warning(
        "INPUT_CRISIS | type=%s | keyword=%s | message_length=%d",
        alert_type,
        keyword,
        len(message),
    )


def log_output_danger(answer_excerpt: str, danger_type: str, keyword: str) -> None:
    """출력 위험 감지 이벤트 기록."""
    crisis_logger.warning(
        "OUTPUT_DANGER | type=%s | keyword=%s | answer_excerpt=%s",
        danger_type,
        keyword,
        answer_excerpt[:100],
    )
```

**로깅 정책:**
- 사용자 원본 메시지는 로그에 기록하지 않음 (개인정보 보호)
- `message_length`만 기록하여 통계 분석 지원
- 출력 답변은 첫 100자만 기록 (디버깅 용도)

---

## 5. Error Handling

### 5.1 에러 시나리오별 처리

| Scenario | Impact | Handling |
|----------|--------|----------|
| 입력 필터 정규식 오류 | 위기 미감지 위험 | 정규식은 빌드 타임에 검증, 예외 시 안전 방향(위기 아님)으로 처리 |
| 출력 필터에서 예외 발생 | warning_level 누락 | try-except로 감싸서 `None` 반환 (정상 답변은 차단 안 됨) |
| 로거 핸들러 설정 실패 | 이벤트 미기록 | 로깅 실패가 메인 로직에 영향 없도록 분리 |

### 5.2 오탐 관리 정책

| 상황 | 예시 | 대응 |
|------|------|------|
| 일반 문학 표현이 Indirect 필터에 걸림 | "이 세상이 싫어질 정도로 맛있다" | 키워드 조합 길이 기반 완화 (3자 이하 단독 키워드 제외 검토) |
| 정상 부작용 설명이 출력 필터에 걸림 | "이 약은 과량 복용 시 주의가 필요합니다" | 답변 차단 안 함 (warning_level 상향만), 오탐 허용 범위 내 |
| 신조어/축약어 우회 | "ㅈㅅ" (자살 축약) | 분기별 키워드 업데이트, 향후 NLP 모델 검토 |

---

## 6. Security Considerations

- [x] 키워드 리스트는 코드 내 상수로 관리 (외부 주입 불가)
- [x] 정규식 패턴에 ReDoS 취약점 없음 확인 (`re.escape` 사용)
- [ ] 위기 이벤트 로그에 개인정보(원문 메시지) 포함하지 않음
- [ ] 로그 파일 접근 권한 제한 (운영 환경)
- [ ] 키워드 업데이트 시 변경 이력 관리 (git)

---

## 7. Test Plan

### 7.1 Test Scope

| Type | Target | Tool | File |
|------|--------|------|------|
| Unit Test | `check_safety()` — 기존 키워드 30개 | pytest | `test_safety.py` |
| Unit Test | `check_safety()` — 확장 키워드 17개 | pytest | `test_safety.py` |
| Unit Test | `check_safety()` — 오탐 검증 (일반 질문 통과) | pytest | `test_safety.py` |
| Unit Test | `check_response_safety()` — 출력 위험 감지 | pytest | `test_safety.py` |
| Unit Test | `check_response_safety()` — 정상 답변 통과 | pytest | `test_safety.py` |
| Integration | 위기 입력 → red_alert 응답 | pytest-asyncio | `test_engine.py` |
| Integration | 출력 위험 → warning_level 상향 | pytest-asyncio | `test_engine.py` |

### 7.2 Test Cases

```python
# ── check_safety() 입력 필터 테스트 ──

# Direct 카테고리 (기존 + 확장)
def test_direct_suicide():
    assert check_safety("죽고 싶어요")["alert_type"] == "Direct"

def test_direct_extended_end_life():
    assert check_safety("생을 마감하고 싶다")["alert_type"] == "Direct"

# Indirect 카테고리 (기존 + 확장)
def test_indirect_disappear():
    assert check_safety("사라지고 싶어")["alert_type"] == "Indirect"

def test_indirect_eternal_sleep():
    assert check_safety("영원히 잠들고 싶어")["alert_type"] == "Indirect"

def test_indirect_burden():
    assert check_safety("짐이 되고 싶지 않아")["alert_type"] == "Indirect"

# Substance 카테고리 (기존 + 확장)
def test_substance_hoard_pills():
    assert check_safety("약을 모아두고 있어")["alert_type"] == "Substance"

# Context 카테고리 (신규)
def test_context_farewell():
    assert check_safety("마지막 인사를 하려고")["alert_type"] == "Context"

def test_context_insurance():
    assert check_safety("보험금 받는 방법")["alert_type"] == "Context"

# 오탐 검증 — 일반 질문은 통과해야 함
def test_normal_drug_interaction():
    assert check_safety("혈압약과 감기약 같이 먹어도 되나요?") is None

def test_normal_side_effect():
    assert check_safety("이 약의 부작용이 뭔가요?") is None

def test_normal_sleep():
    assert check_safety("수면제 처방받고 싶어요") is None

# 공백 변형 감지
def test_space_variant():
    assert check_safety("죽 고 싶 어")["alert_type"] == "Direct"


# ── check_response_safety() 출력 필터 테스트 ──

def test_output_contraindication():
    answer = "이 약물 조합은 절대 금기에 해당합니다."
    result = check_response_safety(answer)
    assert result is not None
    assert result["danger_type"] == "Contraindication"

def test_output_severe_effect():
    answer = "이 경우 심각한 부작용이 발생할 수 있습니다."
    result = check_response_safety(answer)
    assert result is not None
    assert result["danger_type"] == "SevereEffect"

def test_output_overdose():
    answer = "과다 복용 시 생명이 위험할 수 있습니다."
    result = check_response_safety(answer)
    assert result is not None
    assert result["danger_type"] == "Overdose"

def test_output_normal_safe():
    answer = "이 약은 식후 30분에 복용하시면 됩니다."
    assert check_response_safety(answer) is None

def test_output_normal_mild_side_effect():
    answer = "가벼운 두통이 나타날 수 있지만 보통 며칠 내에 사라집니다."
    assert check_response_safety(answer) is None
```

### 7.3 품질 목표

| Metric | Target | Measurement |
|--------|--------|-------------|
| 입력 필터 정탐률 (Recall) | > 95% | 위기 키워드 테스트 케이스 통과율 |
| 입력 필터 오탐률 (FPR) | < 5% | 일반 약물 질문 100개 테스트 |
| 출력 필터 정탐률 | > 90% | 위험 답변 샘플 테스트 |
| 입력 필터 처리 시간 | < 10ms | `time.perf_counter` 측정 |
| 출력 필터 처리 시간 | < 50ms | `time.perf_counter` 측정 |
| 테스트 케이스 수 | >= 15개 | pytest count |

---

## 8. Implementation Guide

### 8.1 File Structure (변경/신규)

```
ai_worker/tasks/
└── chatbot_engine.py      ← 수정:
                              - CRISIS_KEYWORDS 확장 (30→47+)
                              - Context 카테고리 추가
                              - RESPONSE_DANGER_KEYWORDS 상수 추가
                              - check_response_safety() 함수 추가
                              - crisis_logger 설정/함수 추가
                              - get_response() 출력 필터 단계 추가

app/models/
└── chat.py                ← 수정:
                              - alert_type 컬럼 추가
                              - warning_level 컬럼 추가

app/apis/v1/
└── chatbot.py             ← 수정:
                              - ChatLog.create()에 alert_type, warning_level 추가

tests/chatbot/
└── test_safety.py         ← 신규: check_safety + check_response_safety 단위 테스트
```

### 8.2 Implementation Order

1. [ ] `CRISIS_KEYWORDS` 확장 — Direct 3개 + Indirect 6개 + Substance 3개 + Context 5개 추가
2. [ ] `RESPONSE_DANGER_KEYWORDS` 상수 + `check_response_safety()` 함수 추가
3. [ ] `crisis_logger` 구조화 로깅 함수 추가 (`setup_crisis_logger`, `log_input_crisis`, `log_output_danger`)
4. [ ] `get_response()` 파이프라인에 출력 필터 단계 통합
5. [ ] `ChatLog` 모델에 `alert_type`, `warning_level` 컬럼 추가
6. [ ] `chatbot.py` 라우터에서 `alert_type`, `warning_level` DB 저장
7. [ ] `tests/chatbot/test_safety.py` 단위 테스트 15+개 작성
8. [ ] ruff lint + pytest 전체 통과 확인

### 8.3 DB 마이그레이션

```bash
# aerich로 마이그레이션 생성
aerich migrate --name add_alert_type_warning_level
aerich upgrade
```

**마이그레이션 SQL (예상):**
```sql
ALTER TABLE chat_logs ADD COLUMN alert_type VARCHAR(20) NULL;
ALTER TABLE chat_logs ADD COLUMN warning_level VARCHAR(20) DEFAULT 'Normal' NOT NULL;
```

---

## 9. Coding Convention Reference

### 9.1 Naming Conventions

| Target | Rule | Example |
|--------|------|---------|
| 상수 | UPPER_SNAKE_CASE | `CRISIS_KEYWORDS`, `RESPONSE_DANGER_KEYWORDS` |
| 함수 | snake_case | `check_safety()`, `check_response_safety()` |
| 로거 | dotted namespace | `dodaktalk.crisis` |
| 테스트 함수 | `test_` prefix + snake_case | `test_direct_suicide()` |

### 9.2 Import Order

```python
# 1. stdlib
import logging
import os
import re

# 2. third-party
from openai import AsyncOpenAI

# 3. local
from app.dtos.chat import ChatResponse
```

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-03-09 | Initial draft | Team AI-HealthCare |
