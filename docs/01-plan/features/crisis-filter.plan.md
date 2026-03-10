# crisis-filter Planning Document

> **Summary**: 사용자 입력 및 LLM 출력 양방향 위기 감지 필터 — 키워드 기반 즉시 차단 + 답변 내 위험 표현 후처리
>
> **Project**: DodakTalk (도닥톡)
> **Version**: v1.0.0
> **Author**: Team AI-HealthCare
> **Date**: 2026-03-09
> **Status**: Draft

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | 현재 위기 필터는 사용자 입력만 검사하며, LLM이 생성한 답변 내 위험 표현(금기, 심각한 부작용 등)은 감지하지 못해 사용자에게 경고 없이 전달됨 |
| **Solution** | 입력 필터(check_safety) 고도화 + 출력 필터(check_response_safety) 신규 추가로 양방향 안전 검사 파이프라인 구축 |
| **Function/UX Effect** | 입력 위기 시 500ms 이내 1393 안내, 답변 내 위험 표현 감지 시 warning_level 자동 상향 + red_alert 시그널로 프론트엔드 경고 UI 활성화 |
| **Core Value** | 사용자 안전 사각지대 제거 — 입력과 출력 모두에서 위험 상황을 놓치지 않는 이중 안전망 |

---

## 1. Overview

### 1.1 Purpose

챗봇의 위기 감지 필터를 현재 '입력 단방향'에서 '입출력 양방향'으로 확장하고, 키워드 분류 체계를 고도화하여 은유적 표현까지 포괄한다.

### 1.2 Background

- 현재 `check_safety()` 함수는 사용자 입력에서 30개 키워드(Direct 12, Indirect 10, Substance 8)를 정규식으로 매칭
- LLM 답변에 "이 약물 조합은 금기입니다", "심각한 부작용이 발생할 수 있습니다" 등의 위험 표현이 포함되어도 `warning_level`이 상향되지 않음
- 정신건강 관련 은유적 위기 표현("이 세상이 싫어", "영원히 잠들고 싶어")이 현재 필터를 우회할 수 있음

### 1.3 Related Documents

- `docs/01-plan/features/chat-core.plan.md` — 상위 기능 Plan
- `ai_worker/tasks/chatbot_engine.py` — 현재 구현체

---

## 2. Scope

### 2.1 In Scope

- [x] 입력 위기 키워드 필터 (Direct/Indirect/Substance) — **구현 완료**
- [x] 위기 감지 시 LLM 생략 + 1393 안내 반환 — **구현 완료**
- [x] `red_alert`, `alert_type` 응답 필드 — **구현 완료**
- [x] `is_flagged` DB 저장 — **구현 완료**
- [ ] 입력 키워드 확장 (은유적/우회 표현 추가)
- [ ] 출력 안전 검사 함수 (`check_response_safety`) 신규 구현
- [ ] 출력 위험 감지 시 `warning_level` 자동 상향 로직
- [ ] 위기 감지 이벤트 구조화 로깅 (법적 근거 확보)
- [ ] `check_safety` 단위 테스트 (pytest)

### 2.2 Out of Scope

- NLP/ML 기반 의도 분류 모델 (향후 Phase 2)
- 프론트엔드 Red Alert UI 구현
- 관리자 대시보드 (위기 이벤트 모니터링)

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-01 | 입력 위기 키워드 30개 감지 → LLM 생략 + 1393 안내 | High | **Done** |
| FR-02 | 입력 키워드 확장: 은유적 표현 15개 이상 추가 | High | Pending |
| FR-03 | 출력 안전 검사: 답변 내 위험 키워드 감지 함수 구현 | High | Pending |
| FR-04 | 출력 위험 감지 시 `warning_level="Critical"` + `red_alert=True` 자동 설정 | High | Pending |
| FR-05 | 위기 감지 이벤트를 `ChatLog`에 `alert_type`과 함께 저장 | Medium | Pending |
| FR-06 | 위기 감지 로그를 별도 구조화 로깅 (logger 활용) | Medium | Pending |
| FR-07 | `check_safety` + `check_response_safety` pytest 단위 테스트 | Medium | Pending |

### 3.2 Non-Functional Requirements

| Category | Criteria | Measurement Method |
|----------|----------|-------------------|
| Performance | 입력 필터 처리 < 10ms | 함수 실행 시간 측정 |
| Performance | 출력 필터 처리 < 50ms | 함수 실행 시간 측정 |
| Accuracy | 위기 키워드 정탐률(Recall) > 95% | 테스트 케이스 검증 |
| Accuracy | 오탐률(False Positive) < 5% | 일반 질문 테스트 |

---

## 4. Detailed Design

### 4.1 입력 키워드 확장 (FR-02)

현재 30개에 추가할 은유적/우회 표현:

| Category | 추가 키워드 |
|----------|------------|
| **Direct 확장** | 생을 마감, 세상을 떠나, 스스로 끝내 |
| **Indirect 확장** | 영원히 잠들고 싶, 이 세상이 싫, 아무 의미 없, 나만 없으면, 짐이 되고 싶지 않, 모두 다 떠나 |
| **Substance 확장** | 약을 모아, 처방약 모아, 한 번에 다 먹 |
| **Context 신규** | 유서 써, 마지막 인사, 정리하고 떠나, 다음 생, 보험금 |

### 4.2 출력 안전 검사 (FR-03, FR-04)

```python
# 신규 함수: check_response_safety(answer: str) -> dict | None
RESPONSE_DANGER_KEYWORDS = {
    "Contraindication": ["금기", "절대 금기", "병용 금기", "사용 금지"],
    "SevereEffect": ["심각한 부작용", "치명적", "생명 위험", "즉시 중단", "응급"],
    "Overdose": ["과량", "중독", "과다 복용 시"],
}
```

### 4.3 파이프라인 흐름 변경

```
현재:  입력 → [check_safety] → LLM → 응답
변경:  입력 → [check_safety] → LLM → [check_response_safety] → 응답
                                              ↓ (위험 감지 시)
                                    warning_level 상향 + red_alert=True
```

---

## 5. Success Criteria

### 5.1 Definition of Done

- [ ] 입력 키워드 45개 이상으로 확장
- [ ] `check_response_safety()` 함수 구현 및 `get_response()`에 통합
- [ ] 출력 위험 감지 시 `red_alert=True` 반환 확인
- [ ] `ChatLog`에 `alert_type` 컬럼 저장 확인
- [ ] pytest 단위 테스트 15개 이상 통과

### 5.2 Quality Criteria

- [ ] ruff lint 에러 0건
- [ ] 정탐률 > 95% (위기 표현 테스트 케이스)
- [ ] 오탐률 < 5% (일반 약물 질문 테스트)

---

## 6. Risks and Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| 은유적 표현 오탐 (일반 문학적 표현 차단) | Medium | Medium | 문맥 고려 키워드 조합 방식 적용, 테스트 강화 |
| 출력 필터 오탐 (정상 부작용 설명도 차단) | Medium | High | `warning_level` 상향만 하고 답변 차단은 하지 않음 |
| 키워드 우회 (신조어, 축약어) | High | Medium | 분기별 키워드 업데이트, 향후 NLP 모델 검토 |

---

## 7. Architecture Considerations

### 7.1 Project Level Selection

| Level | Characteristics | Recommended For | Selected |
|-------|-----------------|-----------------|:--------:|
| **Starter** | Simple structure | Static sites | ☐ |
| **Dynamic** | Feature-based modules | Web apps, SaaS MVPs | ☑ |
| **Enterprise** | Strict layer separation | High-traffic systems | ☐ |

### 7.2 Key Architectural Decisions

| Decision | Options | Selected | Rationale |
|----------|---------|----------|-----------|
| 필터 위치 | 엔진 내부 / 미들웨어 / 별도 모듈 | 엔진 내부 | 현재 `chatbot_engine.py`에 이미 구현, 일관성 유지 |
| 출력 검사 방식 | 키워드 매칭 / LLM 자체 판단 / 별도 분류 모델 | 키워드 매칭 | 지연 시간 최소화, LLM 추가 호출 비용 없음 |
| 로깅 | print / logging / 별도 DB 테이블 | logging + ChatLog | 기존 `is_flagged` 활용 + 구조화 로거 추가 |

### 7.3 파일 변경 범위

```
수정 대상:
├── ai_worker/tasks/chatbot_engine.py    ← 키워드 확장 + check_response_safety 추가
├── app/apis/v1/chatbot.py               ← alert_type DB 저장 추가
├── app/models/chat.py                   ← alert_type 컬럼 추가
└── app/dtos/chat.py                     ← (변경 없음, 이미 alert_type 포함)

신규 생성:
└── app/tests/chatbot/test_safety.py     ← pytest 단위 테스트
```

---

## 8. Convention Prerequisites

### 8.1 Environment Variables Needed

| Variable | Purpose | Scope | Status |
|----------|---------|-------|:------:|
| `OPENAI_API_KEY` | OpenAI API 인증 | Server | ☑ Done |
| `OPENAI_MODEL` | LLM 모델명 | Server | ☑ Done |

(이 기능은 추가 환경 변수 불필요)

---

## 9. Next Steps

1. [ ] Design 문서 작성 (`crisis-filter.design.md`)
2. [ ] 팀 리뷰 및 승인
3. [ ] 구현 시작 (키워드 확장 → 출력 필터 → 테스트)

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-03-09 | Initial draft | Team AI-HealthCare |
