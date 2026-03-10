# chat-core Design Document

> **Summary**: AI 헬스케어 챗봇 6단계 파이프라인 상세 설계 — 위기 필터 + 페르소나 + 식약처 API + RAG + LLM + DB 저장
>
> **Project**: DodakTalk (도닥톡)
> **Version**: v1.0.0
> **Author**: Team AI-HealthCare
> **Date**: 2026-03-09
> **Status**: Draft
> **Planning Doc**: [chat-core.plan.md](../../01-plan/features/chat-core.plan.md)

---

## 1. Overview

### 1.1 Design Goals

- 6단계 파이프라인(입력 → 필터링 → 컨텍스트 → RAG → LLM → 출력) 전체를 `MedicationChatbot` 클래스 내부에 일관된 비동기 흐름으로 구현
- 각 단계를 독립 메서드로 분리하여 테스트 가능성과 확장성 확보
- 기존 구현(check_safety, AsyncOpenAI, ChatLog)을 유지하며 점진적 확장

### 1.2 Design Principles

- **Fail-Safe First**: 위기 감지가 항상 LLM보다 먼저 실행, 에러 시 안전한 폴백
- **Single Responsibility**: 파이프라인 각 단계를 독립 메서드/모듈로 분리
- **Graceful Degradation**: 식약처 API/ChromaDB 장애 시에도 기본 LLM 답변 유지

---

## 2. Architecture

### 2.1 Component Diagram

```
┌──────────┐    ┌──────────────────────────────────────────────────────┐    ┌─────────┐
│  Client  │───▶│  FastAPI Server                                      │───▶│  MySQL  │
│(Browser) │    │  ┌─────────┐  ┌──────────────────────────────────┐  │    │chat_logs│
│          │◀───│  │ Router  │─▶│  MedicationChatbot               │  │    └─────────┘
└──────────┘    │  │/chat/ask│  │  ┌────────┐  ┌────────┐  ┌────┐ │  │
                │  └─────────┘  │  │Safety  │─▶│Context │─▶│RAG │ │  │    ┌─────────┐
                │               │  │Filter  │  │Builder │  │    │ │  │───▶│ChromaDB │
                │               │  └────────┘  └────────┘  └──┬─┘ │  │    └─────────┘
                │               │                             │    │  │
                │               │  ┌────────┐  ┌────────────┐ │   │  │    ┌─────────┐
                │               │  │Output  │◀─│LLM (GPT-4o)│◀┘   │  │───▶│OpenAI   │
                │               │  │Filter  │  │            │      │  │    │  API    │
                │               │  └────────┘  └────────────┘      │  │    └─────────┘
                │               └──────────────────────────────────┘  │
                │                                                      │    ┌─────────┐
                │               ┌──────────────────┐                   │───▶│식약처API│
                │               │  KFDA Client     │                   │    └─────────┘
                │               └──────────────────┘                   │
                └──────────────────────────────────────────────────────┘
```

### 2.2 Data Flow (6단계 파이프라인)

```
사용자 입력
    │
    ▼
[1. 입력 수신] ─── ChatRequest (message, medication_list, user_note)
    │
    ▼
[2. 위기 필터] ─── check_safety(message)
    │                 ├─ 감지 → CRISIS_RESPONSE + red_alert=True (LLM 생략)
    │                 └─ 미감지 → 다음 단계
    ▼
[3. 컨텍스트 준비] ─── build_context(meds, user_note)
    │                     ├─ 식약처 API → 약물 상세 정보 조회
    │                     └─ 약물 리스트 + 주의사항 텍스트 조합
    ▼
[4. RAG 검색] ─── search_guidelines(message, meds)
    │               ├─ ChromaDB에서 관련 의학 가이드라인 검색
    │               └─ top-3 결과를 context에 추가
    ▼
[5. LLM 추론] ─── generate_response(system_prompt, context, message)
    │               ├─ 시스템 페르소나 ("다정한 약사")
    │               ├─ RAG 컨텍스트 주입
    │               └─ AsyncOpenAI GPT-4o-mini 호출
    ▼
[6. 출력 처리] ─── check_response_safety(answer) + 면책 조항 추가
    │               ├─ 위험 키워드 감지 → warning_level 상향
    │               └─ ChatLog DB 저장
    ▼
ChatResponse 반환
```

### 2.3 Dependencies

| Component | Depends On | Purpose |
|-----------|-----------|---------|
| `chatbot.py` (Router) | `chatbot_engine.py`, `ChatLog`, DTOs | 요청 라우팅, DB 저장 |
| `chatbot_engine.py` | `AsyncOpenAI`, `kfda_client`, `ChromaDB` | 6단계 파이프라인 실행 |
| `kfda_client.py` (신규) | `httpx`, 식약처 API | 약물 정보 조회 |
| `rag_service.py` (신규) | `chromadb`, `sentence-transformers` | 벡터 검색 |

---

## 3. Data Model

### 3.1 Entity Definition

```python
# app/models/chat.py (기존)
class ChatLog(models.Model):
    id = fields.IntField(primary_key=True)
    user_id = fields.IntField(index=True)
    message_content = fields.TextField()
    response_content = fields.TextField()
    is_flagged = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "chat_logs"
```

```python
# app/models/chat.py (확장 — FR-10 시)
class ChatLog(models.Model):
    # 기존 필드 유지
    alert_type = fields.CharField(max_length=20, null=True)  # 신규: Direct/Indirect/Substance
    warning_level = fields.CharField(max_length=20, default="Normal")  # 신규
```

### 3.2 Entity Relationships

```
[User] 1 ──── N [ChatLog]
  │                 │
  └─ user_id ───────┘
```

### 3.3 DTO 스펙

```python
# app/dtos/chat.py (기존, 변경 없음)
class ChatRequest(BaseModel):
    message: str
    medication_list: list[str] = []
    user_note: str | None = None

class ChatResponse(BaseModel):
    answer: str
    warning_level: str = "Normal"       # Normal / Caution / Critical
    red_alert: bool = False
    alert_type: str | None = None       # Direct / Indirect / Substance
```

---

## 4. API Specification

### 4.1 Endpoint List

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/v1/chat/ask` | AI 챗봇 질문/답변 | 미인증 (Phase 4에서 추가) |

### 4.2 Detailed Specification

#### `POST /api/v1/chat/ask`

**Request:**
```json
{
  "message": "혈압약과 감기약 같이 먹어도 되나요?",
  "medication_list": ["아모디핀 5mg", "타이레놀 500mg"],
  "user_note": "고혈압 진단 3년차"
}
```

**Response — 일반 (200 OK):**
```json
{
  "answer": "아모디핀과 타이레놀은 일반적으로... \n\n⚕️ 이 정보는 참고용이며, 정확한 판단은 담당 의사나 약사와 상담하세요.",
  "warning_level": "Caution",
  "red_alert": false,
  "alert_type": null
}
```

**Response — 위기 감지 (200 OK):**
```json
{
  "answer": "지금 많이 힘드시군요... ▶ 자살예방상담전화: 1393 (24시간)...",
  "warning_level": "Critical",
  "red_alert": true,
  "alert_type": "Direct"
}
```

**Response — 출력 위험 감지 (200 OK):**
```json
{
  "answer": "이 약물 조합은 금기 사항에 해당합니다... \n\n⚕️ 면책 조항...",
  "warning_level": "Critical",
  "red_alert": true,
  "alert_type": null
}
```

---

## 5. Module Design

### 5.1 시스템 페르소나 (FR-04)

```python
SYSTEM_PERSONA = """당신은 '도닥이'라는 이름의 다정한 약사 AI 상담사입니다.

## 핵심 규칙
1. 전문 의학 용어는 쉽게 풀어서 설명하되, 절대 공포감을 주지 마세요.
2. 답변 끝에는 반드시 실질적인 대처법(물 많이 마시기, 식후 복용 등)을 포함하세요.
3. 오프라벨 처방의 경우, "이 약은 원래 [원래 적응증]이지만, [작용 기전]을 통해 [현재 증상]에도 효과가 있어 정신과에서 자주 쓰입니다"라고 부드럽게 설명하세요.
4. 절대로 직접적인 진단이나 처방 변경을 지시하지 마세요.
5. 사용자가 불안해하면 공감 먼저, 정보 제공은 그 다음에 하세요.

## 답변 형식
- 핵심 답변 (2~3문장)
- 실질적 대처법 (1~2가지)
- 면책 조항 (자동 추가됨)
"""
```

### 5.2 면책 조항 (FR-05)

```python
DISCLAIMER = "\n\n⚕️ 이 정보는 일반적인 참고용이며, 개인의 상태에 따라 다를 수 있습니다. 정확한 판단은 담당 의사나 약사와 상담하세요."
```

### 5.3 출력 안전 검사 (FR-06)

```python
RESPONSE_DANGER_KEYWORDS = {
    "Contraindication": ["금기", "절대 금기", "병용 금기", "사용 금지"],
    "SevereEffect": ["심각한 부작용", "치명적", "생명 위험", "즉시 중단", "응급"],
    "Overdose": ["과량", "중독", "과다 복용 시"],
}

def check_response_safety(answer: str) -> dict | None:
    """LLM 답변 내 위험 키워드를 감지합니다."""
    for danger_type, keywords in RESPONSE_DANGER_KEYWORDS.items():
        for keyword in keywords:
            if keyword in answer:
                return {"danger_type": danger_type, "keyword": keyword}
    return None
```

### 5.4 식약처 API 클라이언트 (FR-07)

```python
# ai_worker/tasks/kfda_client.py (신규)
class KFDAClient:
    BASE_URL = "https://apis.data.go.kr/1471000/DrbEasyDrugInfoService"

    async def search_drug(self, drug_name: str) -> dict | None:
        """e약은요 API로 약물 정보 조회"""
        # itemName 파라미터로 검색
        # 반환: 효능효과, 용법용량, 주의사항, 상호작용

    async def get_drug_context(self, meds: list[str]) -> str:
        """약물 리스트로 컨텍스트 문자열 생성"""
        # 각 약물의 주의사항을 조합하여 LLM 프롬프트용 텍스트 반환
```

### 5.5 RAG 서비스 (FR-08)

```python
# ai_worker/tasks/rag_service.py (신규)
class RAGService:
    def __init__(self):
        self.collection = chromadb.PersistentClient(path=CHROMA_DIR).get_or_create_collection("guidelines")
        self.embedder = SentenceTransformer("jhgan/ko-sroberta-multitask")

    async def search(self, query: str, n_results: int = 3) -> list[str]:
        """의학 가이드라인에서 관련 문맥 검색"""

    def ingest_pdf(self, pdf_path: str) -> int:
        """PDF를 청크 분할 → 임베딩 → ChromaDB 저장"""
```

### 5.6 MedicationChatbot 리팩토링

```python
# ai_worker/tasks/chatbot_engine.py (확장)
class MedicationChatbot:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.kfda = KFDAClient()          # 신규
        self.rag = RAGService()            # 신규

    async def get_response(self, user_message, meds, user_note=None) -> dict:
        # Step 1: 위기 필터 (기존)
        safety = check_safety(user_message)
        if safety:
            return crisis_response(safety)

        # Step 2: 컨텍스트 준비 (신규)
        drug_context = await self.kfda.get_drug_context(meds)

        # Step 3: RAG 검색 (신규)
        rag_context = await self.rag.search(user_message)

        # Step 4: LLM 호출 (확장 — 페르소나 + 컨텍스트)
        answer = await self._call_llm(
            system=SYSTEM_PERSONA,
            drug_info=drug_context,
            rag_results=rag_context,
            user_message=user_message,
            meds=meds,
            user_note=user_note,
        )

        # Step 5: 출력 안전 검사 (신규)
        danger = check_response_safety(answer)
        warning_level = "Critical" if danger else ("Caution" if meds else "Normal")
        red_alert = danger is not None

        # Step 6: 면책 조항 추가
        answer += DISCLAIMER

        return {
            "answer": answer,
            "warning_level": warning_level,
            "red_alert": red_alert,
            "alert_type": None,
        }
```

---

## 6. Error Handling

### 6.1 에러 시나리오별 처리

| Scenario | Impact | Handling |
|----------|--------|----------|
| OpenAI API 장애/타임아웃 | LLM 답변 불가 | "답변 생성 중 문제 발생" 안전 메시지 + 로깅 |
| 식약처 API 장애 | 약물 정보 누락 | drug_context를 빈 문자열로 대체, LLM만으로 답변 |
| ChromaDB 검색 실패 | RAG 컨텍스트 누락 | rag_context를 빈 리스트로 대체, LLM만으로 답변 |
| 잘못된 약물명 입력 | 식약처 검색 결과 없음 | "해당 약물 정보를 찾지 못했습니다" 안내 포함 |

### 6.2 에러 응답 형식

```python
# 모든 에러 상황에서도 ChatResponse 형식 유지
{
    "answer": "죄송합니다. 답변을 생성하는 중에 문제가 발생했습니다.",
    "warning_level": "Normal",
    "red_alert": False,
    "alert_type": None
}
```

---

## 7. Security Considerations

- [x] API 키 환경변수 관리 (`os.getenv`, 하드코딩 금지)
- [x] CORS 설정 (FastAPI 미들웨어)
- [ ] Rate Limiting (`slowapi` 적용 — 비용 보호)
- [ ] 입력 길이 제한 (`message` 최대 2000자)
- [ ] 의료법 준수 (시스템 프롬프트에 "진단/처방 금지" 강제)
- [ ] 위기 이벤트 구조화 로깅 (법적 근거 확보)

---

## 8. Test Plan

### 8.1 Test Scope

| Type | Target | Tool |
|------|--------|------|
| Unit Test | `check_safety`, `check_response_safety`, 페르소나 | pytest |
| Unit Test | `KFDAClient.search_drug` (모킹) | pytest + httpx mock |
| Unit Test | `RAGService.search` (모킹) | pytest |
| Integration Test | `POST /api/v1/chat/ask` 전체 흐름 | pytest-asyncio + httpx |

### 8.2 Test Cases

- [ ] 위기 키워드 Direct/Indirect/Substance 각 카테고리 감지
- [ ] 일반 약물 질문 → LLM 답변 + 면책 조항 포함 확인
- [ ] 출력 위험 키워드 감지 → `red_alert=True` 확인
- [ ] 식약처 API 장애 시 graceful fallback
- [ ] ChromaDB 검색 실패 시 LLM만으로 답변 유지
- [ ] 빈 medication_list → `warning_level="Normal"`
- [ ] 오프라벨 약물 → 부드러운 설명 포함 확인

---

## 9. Clean Architecture

### 9.1 Layer Structure (Python FastAPI)

| Layer | Responsibility | Location |
|-------|---------------|----------|
| **Presentation** | API 라우팅, 요청/응답 직렬화 | `app/apis/v1/chatbot.py` |
| **Application** | 비즈니스 오케스트레이션 (파이프라인) | `ai_worker/tasks/chatbot_engine.py` |
| **Domain** | DTO, 모델 정의 | `app/dtos/chat.py`, `app/models/chat.py` |
| **Infrastructure** | 외부 서비스 클라이언트 | `ai_worker/tasks/kfda_client.py`, `ai_worker/tasks/rag_service.py` |

### 9.2 Dependency Rules

```
┌────────────────────────────────────────────────────────┐
│                Dependency Direction                     │
├────────────────────────────────────────────────────────┤
│                                                         │
│  chatbot.py ──▶ chatbot_engine.py ──▶ DTOs/Models      │
│  (Presentation)   (Application)       (Domain)          │
│                       │                                  │
│                       ├──▶ kfda_client.py                │
│                       ├──▶ rag_service.py                │
│                       └──▶ AsyncOpenAI                   │
│                            (Infrastructure)              │
│                                                         │
└────────────────────────────────────────────────────────┘
```

---

## 10. Coding Convention Reference

### 10.1 Naming Conventions (Python)

| Target | Rule | Example |
|--------|------|---------|
| Class | PascalCase | `MedicationChatbot`, `KFDAClient` |
| Function/Method | snake_case | `check_safety()`, `get_response()` |
| Constants | UPPER_SNAKE_CASE | `CRISIS_KEYWORDS`, `SYSTEM_PERSONA` |
| Module file | snake_case.py | `chatbot_engine.py`, `kfda_client.py` |

### 10.2 Import Order (ruff I)

```python
# 1. stdlib
import os
import re

# 2. third-party
from openai import AsyncOpenAI
import chromadb

# 3. local
from app.dtos.chat import ChatRequest, ChatResponse
from app.models.chat import ChatLog
```

### 10.3 Environment Variables

| Variable | Purpose | Scope |
|----------|---------|-------|
| `OPENAI_API_KEY` | OpenAI 인증 | Server |
| `OPENAI_MODEL` | LLM 모델명 | Server |
| `KFDA_API_KEY` | 식약처 e약은요 API 키 | Server |
| `CHROMA_PERSIST_DIR` | ChromaDB 저장 경로 | Server |

---

## 11. Implementation Guide

### 11.1 File Structure (변경/신규)

```
ai_worker/tasks/
├── chatbot_engine.py     ← 확장 (페르소나, 면책, 출력 검사, 컨텍스트 통합)
├── kfda_client.py        ← 신규 (식약처 API 클라이언트)
└── rag_service.py        ← 신규 (ChromaDB RAG 서비스)

app/apis/v1/
└── chatbot.py            ← 수정 (alert_type DB 저장)

app/tests/chatbot/
├── test_safety.py        ← 신규 (check_safety + check_response_safety 테스트)
├── test_engine.py        ← 신규 (MedicationChatbot 통합 테스트)
└── test_kfda.py          ← 신규 (식약처 API 모킹 테스트)

data/
├── guidelines/           ← 신규 (의학 가이드라인 PDF)
└── embeddings/           ← 신규 (ChromaDB 저장소, .gitignore 추가)
```

### 11.2 Implementation Order

1. [ ] 시스템 페르소나 + 면책 조항 추가 (`chatbot_engine.py`)
2. [ ] 출력 안전 검사 `check_response_safety()` 구현 (`chatbot_engine.py`)
3. [ ] 식약처 API 클라이언트 구현 (`kfda_client.py`)
4. [ ] RAG 서비스 구현 (`rag_service.py`)
5. [ ] `MedicationChatbot.get_response()` 6단계 통합
6. [ ] `ChatLog` 모델에 `alert_type`, `warning_level` 컬럼 추가
7. [ ] pytest 단위/통합 테스트 작성
8. [ ] 카카오 `user_id` 연동

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-03-09 | Initial draft | Team AI-HealthCare |
