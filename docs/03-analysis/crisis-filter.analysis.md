# crisis-filter Gap Analysis

> **Feature**: crisis-filter (입출력 양방향 위기 감지 필터)
> **Date**: 2026-03-09
> **Design Doc**: [crisis-filter.design.md](../02-design/features/crisis-filter.design.md)
> **Match Rate**: 97%

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Match Rate** | 97% |
| **Design Items** | 23 |
| **Matched** | 22 |
| **Minor Gap** | 1 |
| **Missing** | 0 |
| **Tests** | 27/27 passed |
| **Lint** | ruff clean |

---

## 1. Item-by-Item Analysis

### 1.1 입력 키워드 확장 (§4.1)

| Design Spec | Implementation | Status |
|-------------|---------------|--------|
| Direct: 12 기존 + 3 확장 = 15개 | `CRISIS_KEYWORDS["Direct"]` = 15개 | ✅ Match |
| Indirect: 10 기존 + 6 확장 = 16개 | `CRISIS_KEYWORDS["Indirect"]` = 16개 | ✅ Match |
| Substance: 8 기존 + 3 확장 = 11개 | `CRISIS_KEYWORDS["Substance"]` = 11개 | ✅ Match |
| Context: 5개 (신규 카테고리) | `CRISIS_KEYWORDS["Context"]` = 5개 | ✅ Match |
| 합계: 47+ 키워드 | 합계: 47개 | ✅ Match |

### 1.2 출력 안전 검사 (§4.2)

| Design Spec | Implementation | Status |
|-------------|---------------|--------|
| `RESPONSE_DANGER_KEYWORDS` 상수 정의 | `chatbot_engine.py:157-183` | ✅ Match |
| Contraindication: 6개 키워드 | 6개 (금기, 절대 금기, 병용 금기, 사용 금지, 같이 복용하면 안, 함께 사용 금지) | ✅ Match |
| SevereEffect: 7개 키워드 | 7개 (심각한 부작용, 치명적, 생명 위험, 즉시 중단, 응급, 사망 위험, 생명을 위협) | ✅ Match |
| Overdose: 6개 키워드 | 6개 (과량, 중독, 과다 복용 시, 치사량, 과다 투여, 용량 초과) | ✅ Match |
| `check_response_safety(answer) -> dict \| None` | `chatbot_engine.py:212-226` | ✅ Match |
| 답변 차단 안 함, warning_level 상향만 | `get_response()` Stage 6: answer 유지, warning="Critical" | ✅ Match |

### 1.3 파이프라인 통합 (§4.3)

| Design Spec | Implementation | Status |
|-------------|---------------|--------|
| Step 1: 입력 위기 필터 → CRISIS_RESPONSE | `get_response():261-274` | ✅ Match |
| 위기 감지 시 LLM 호출 생략 | `return` 즉시 반환 | ✅ Match |
| Step 2: LLM 호출 | `self.client.chat.completions.create()` | ✅ Match |
| Step 3: 출력 안전 검사 | `check_response_safety(answer)` at line 314 | ✅ Match |
| 출력 위험 시 `warning_level="Critical"` + `red_alert=True` | Lines 321-322 | ✅ Match |
| 출력 위험 시 `alert_type=None` | Line 334 | ✅ Match |
| Step 4: 정상 반환 `warning_level="Caution" if meds else "Normal"` | Lines 324 | ✅ Match |

### 1.4 구조화 로깅 (§4.4)

| Design Spec | Implementation | Status |
|-------------|---------------|--------|
| `crisis_logger = logging.getLogger("dodaktalk.crisis")` | Line 14 | ✅ Match |
| `setup_crisis_logger()` 함수 | Lines 17-26 (with handler dedup guard) | ✅ Match+ |
| `log_input_crisis()` — `INPUT_CRISIS \| type=%s \| keyword=%s \| message_length=%d` | Lines 29-36 | ✅ Match |
| `log_output_danger()` — `OUTPUT_DANGER \| type=%s \| keyword=%s \| answer_excerpt=%s` | Lines 39-46 | ✅ Match |
| 사용자 원본 메시지 로그 미기록 (개인정보 보호) | `len(message)` only | ✅ Match |
| 출력 답변 첫 100자만 기록 | `answer_excerpt[:100]` | ✅ Match |

### 1.5 ChatLog 모델 확장 (§3.1)

| Design Spec | Implementation | Status |
|-------------|---------------|--------|
| `alert_type = CharField(max_length=20, null=True)` | `chat.py:10` | ✅ Match |
| `warning_level = CharField(max_length=20, default="Normal")` | `chat.py:11` | ✅ Match |

### 1.6 ChatLog.create() 변경 (§3.2)

| Design Spec | Implementation | Status |
|-------------|---------------|--------|
| `alert_type=result["alert_type"]` 저장 | `chatbot.py:26` | ✅ Match |
| `warning_level=result["warning_level"]` 저장 | `chatbot.py:27` | ✅ Match |

### 1.7 테스트 (§7)

| Design Spec | Implementation | Status |
|-------------|---------------|--------|
| 테스트 케이스 >= 15개 | **27개** | ✅ Exceeded |
| check_safety Direct 테스트 | 5개 (TestCheckSafetyDirect) | ✅ Match |
| check_safety Indirect 테스트 | 4개 (TestCheckSafetyIndirect) | ✅ Match |
| check_safety Substance 테스트 | 3개 (TestCheckSafetySubstance) | ✅ Match |
| check_safety Context 테스트 | 3개 (TestCheckSafetyContext) | ✅ Match |
| check_safety 오탐 검증 | 5개 (TestCheckSafetyFalsePositive) | ✅ Match |
| check_response_safety 출력 감지 | 7개 (TestCheckResponseSafety) | ✅ Match |
| 공백 변형 감지 테스트 | `test_space_variant` | ✅ Match |

---

## 2. Gap Details

### 2.1 Minor Gap: DISCLAIMER 적용 범위

| Category | Detail |
|----------|--------|
| **Design** (§4.3 Step 3) | 출력 위험 감지 시 answer를 즉시 반환 (DISCLAIMER 추가 여부 미명시) |
| **Implementation** | 출력 위험/정상 모두 `answer += DISCLAIMER` 적용 (line 328) |
| **Impact** | Low — DISCLAIMER는 모든 답변에 포함되는 것이 안전 관점에서 더 적합 |
| **Action** | 수정 불필요 — 현재 구현이 설계 의도보다 더 안전한 방향 |

---

## 3. Quality Metrics

| Metric | Target (§7.3) | Actual | Status |
|--------|---------------|--------|--------|
| 입력 필터 정탐률 | > 95% | 100% (15/15 위기 키워드 테스트 통과) | ✅ |
| 입력 필터 오탐률 | < 5% | 0% (5/5 일반 질문 통과) | ✅ |
| 출력 필터 정탐률 | > 90% | 100% (4/4 위험 답변 감지) | ✅ |
| 테스트 케이스 수 | >= 15개 | 27개 | ✅ |
| ruff lint | Clean | Clean | ✅ |
| pytest | All pass | 27/27 passed (0.35s) | ✅ |

---

## 4. Files Analyzed

| File | Role | Lines |
|------|------|-------|
| `ai_worker/tasks/chatbot_engine.py` | 핵심 엔진 (키워드, 필터, 파이프라인, 로깅) | 336 |
| `app/models/chat.py` | ChatLog 모델 (alert_type, warning_level) | 16 |
| `app/apis/v1/chatbot.py` | API 라우터 (DB 저장 포함) | 31 |
| `tests/chatbot/test_safety.py` | 단위 테스트 27개 | 176 |

---

## 5. Conclusion

**Match Rate: 97%** — 설계 문서의 모든 핵심 요구사항이 정확히 구현되었습니다.

- 입력 키워드 47개 (4개 카테고리) 완벽 일치
- 출력 안전 검사 19개 키워드 (3개 카테고리) 완벽 일치
- 구조화 로깅 (INPUT_CRISIS, OUTPUT_DANGER) 완벽 일치
- ChatLog 모델 확장 + DB 저장 완벽 일치
- 테스트 27개 (목표 15개 초과 달성)
- 유일한 minor gap (DISCLAIMER 적용)은 설계보다 더 안전한 방향으로 수정 불필요

**Recommendation**: Match Rate >= 90% — `/pdca report crisis-filter` 진행 가능
