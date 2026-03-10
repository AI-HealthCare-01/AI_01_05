# plan.md (v3 — 2026-03-09 개정)

> **개정 이력 v3:** 프론트엔드 기술 스택 확정(React + TypeScript + Vite), 디자인 가이드 수립,
> LLM 교체(Claude → OpenAI GPT-4o mini), 외부 UI 라이브러리 사용 금지 원칙 추가.
>
> **개정 이력 v2:** Critical/High 이슈 반영 — DB 마이그레이션, API Fallback, Agent 안전장치,
> Python 3.13+ 타입 규칙, RAG 고도화, 테스트 전략 구체화, SQLAlchemy 2.0 전환 검토.

---

## 1. 프로젝트 개요 (DodakTalk)

- **목적:** 사용자 건강 데이터(복약, 일기, 기분) 기반의 하이브리드 AI 챗봇 서비스
- **핵심 가치:** 정서적 지지(Persona) + 의학적 근거(RAG) + 사용자 안전(Rule-based Filter)
- **기술 스택 (백엔드):** Python 3.13+, FastAPI, LangGraph 0.2+, SQLAlchemy 2.0 (async), Alembic, Ruff
- **기술 스택 (프론트엔드):** React 18+, TypeScript, Vite
- **LLM:** OpenAI GPT-4o mini (`gpt-4o-mini`)

---

## 2. 하이브리드 챗봇 아키텍처 & 데이터 플로우

### [단계별 워크플로우]

1. **입력 단계:** 사용자 메시지 수신.
2. **필터링 (Rule-based):**
   - Regex 기반 '위기 키워드'(`자살`, `자해`, `죽고싶` 등) 즉시 매칭.
   - 감지 시 LLM 호출을 **완전히 생략**하고 `CRISIS_DETECTED` 에러 코드 및 비상 UI 시그널 반환.
   - ✅ **[CRITICAL Fix]** 필터는 단독 모듈(`crisis_filter.py`)로 분리하여 단위 테스트 가능하게 구성.
3. **컨텍스트 준비 (Backend):** DB에서 `user_id` 기준 '현재 복용 약물 리스트' 추출.
4. **추론 및 검색 (Agentic RAG):**
   - **Re-Act Agent (LangGraph 0.2+):** 질문 의도에 따라 Tools 선택적 호출.
   - ✅ **[CRITICAL Fix]** `max_iterations=10`, `timeout_seconds=30` 명시적 설정 — 무한루프 방지.
   - **Tool 1 (ChromaDB/FAISS):** 정신의학 가이드라인 Vector DB 검색. *(§6 참고)*
   - **Tool 2 (API):** 식약처 'e약은요' API 실시간 연동 + **Circuit Breaker 패턴 적용.**
   - **Tool 3 (DB):** 사용자 복약 이력 및 부작용 기록 조회.
5. **LLM 생성 (GPT-4o mini):** `[페르소나 + RAG 결과 + 복용 약물 + 질문]` 기반 프롬프트 실행.
   - OpenAI `response_format` 파라미터로 JSON Structured Output 강제.
6. **출력 검증 (Guardrails):**
   - ✅ **[HIGH Fix]** LLM 응답을 단순 키워드 매칭이 아닌 **구조화된 출력 스키마(Pydantic)**로 검증.
   - `is_flagged`, `red_alert` 필드를 LLM이 직접 판단하도록 structured output 활용.
7. **출력 및 저장:** 답변 출력 + Red Alert 팝업 활성화 여부 결정 + `chatlogs` 저장.

---

## 3. 상세 구현 가이드

### 3.1. 백엔드 (FastAPI & LangGraph Stack)

#### Python 3.13+ 타입 규칙 (SYSTEM_DESIGN.md 1순위)
```python
# ✅ 올바른 타입 힌트 — built-in types 사용
def get_medicines(user_id: int) -> list[dict]:
    ...

# ❌ 금지 — typing 모듈 사용 불가
from typing import List, Dict  # SYSTEM_DESIGN.md 위반
```

#### Vector DB 선택
- **기본:** ChromaDB (로컬 persistent 모드, Python-native, 갱신 용이)
- **대안:** FAISS (고성능 유사도 검색, 단 인덱스 재구축 시 서비스 중단 위험 — §6 참고)
- ✅ **[HIGH Fix]** `VectorSearchTool` 추상 인터페이스로 구현 → 벤더 교체 가능.

```python
# 추상 인터페이스 예시
class VectorSearchTool:
    def search(self, query: str, top_k: int) -> list[dict]:
        raise NotImplementedError
```

#### Tool Calling
- LangGraph 0.2+ `ToolNode` 패턴 사용.
- `get_user_medicines`, `search_medicine_api`, `search_vector_db` 함수 모듈화.
- ✅ **[CRITICAL Fix]** 모든 `import`는 **파일 최상단**에만 위치 (AGENTS.md 규칙).

#### Safety Logic — Structured Output
```python
class ChatResponse(BaseModel):  # Pydantic v2
    answer: str
    is_flagged: bool
    red_alert: bool
    reasoning: str  # 판단 근거 (감사 추적용)
```
- 모든 API는 `/api/v1/` 프리픽스로 **버저닝** 관리.

#### 식약처 API Fallback (Circuit Breaker)
```python
# ✅ [CRITICAL Fix] — 외부 API 장애 대응
class MedicineAPITool:
    def search(self, medicine_name: str) -> dict:
        try:
            return self._call_external_api(medicine_name)
        except (TimeoutError, HTTPError):
            return self._get_cached_fallback(medicine_name)
        except CircuitBreakerOpen:
            return {"source": "cache", "data": self._get_cached_fallback(medicine_name)}
```
- Redis 캐싱: TTL 24시간, 인기 약물 선제 캐싱.

---

### 3.2. 프론트엔드 (React 18+ + TypeScript + Vite)

#### 기술 스택
| 항목 | 선택 | 비고 |
|------|------|------|
| 프레임워크 | React 18+ | Concurrent Mode, Suspense 지원 |
| 언어 | TypeScript | strict 모드 활성화 |
| 번들러 | Vite | HMR 고속, ESM 네이티브 |
| 스타일링 | CSS Modules 또는 인라인 스타일 | 외부 UI 라이브러리 **사용 금지** |
| 상태 관리 | React 내장 (`useState`, `useReducer`, `useContext`) | 별도 상태 라이브러리 불필요 |

> ⚠️ **외부 UI 라이브러리(MUI, Ant Design, Chakra, shadcn 등) 사용 금지.**
> 모든 컴포넌트는 직접 구현한다.

#### 디자인 가이드 (반드시 준수)

```typescript
// styles/tokens.ts — 디자인 토큰 중앙 관리
export const COLOR = {
  background:  '#F5F5F5',   // 전체 배경
  white:       '#FFFFFF',   // 말풍선 배경, 헤더/탭바 배경
  text:        '#2C2C2C',   // 기본 텍스트
  textSub:     '#5A5A5A',   // 보조 텍스트 (시간, 설명)
  danger:      '#FF0000',   // 경고 텍스트 (red_alert, is_flagged)
  placeholder: '#757575',   // 입력 필드 플레이스홀더
  btnBg:       '#99A988',   // 버튼 배경, 사용자 말풍선, 탭 액티브
  btnText:     '#F5F5F5',   // 버튼 텍스트
  border:      '#E2E2E2',   // 구분선, 입력 테두리, 카드 테두리
} as const;
```

- 스타일: **모던하고 미니멀** — 불필요한 장식 요소 배제, 여백과 타이포그래피 중심.
- 경고 상태(`red_alert: true`): `COLOR.danger(#FF0000)` 텍스트 + 시각적 경계 강조.
- 위기 상태(`is_crisis: true`): 전체 UI 오버레이 + 비상 연락처 모달 표시.

#### 컴포넌트 구조

```
src/
├── styles/
│   └── tokens.ts                  # 디자인 토큰 (COLOR 상수 9개)
├── types/
│   └── api.ts                     # ChatResponse, ChatRequest + MessageType
├── hooks/
│   ├── useChat.ts                 # 채팅 상태 + /api/v1/chat 통신
│   └── useCrisisGuard.ts          # CRISIS_DETECTED 상태 감시
└── components/
    ├── ChatHeader/                # 상단 네비 (뒤로가기 + 타이틀 + 햄버거)
    ├── ChatBubble/                # 말풍선 — type: "text" | "info_card"
    ├── ChatInput/                 # 메시지 입력 + 전송 버튼
    ├── QuickChipMenu/             # 칩 기반 퀵 메뉴
    ├── SideDrawer/                # 슬라이드 햄버거 메뉴 (Screen 9)
    ├── MedCalendar/               # 복약 캘린더 인라인 패널 (Screen 5-1)
    ├── AudioPlayer/               # 음성 안내 플레이어 (Screen 5-2)
    ├── InfoPanel/                 # 케어팁 / 관찰 정보 패널 (Screen 5-4, 8)
    ├── ObserveCard/               # 관찰 참가 카드 (Screen 8)
    ├── AlertOverlay/              # CrisisOverlay — CRISIS_DETECTED 시 전체 오버레이
    ├── BottomTabBar/              # 하단 탭 (채팅 / 복약 / 관찰 / 메뉴)
    └── Button/                    # 공통 버튼 (#99A988 배경)
```

#### API 타입 정의 (`/api/v1/` 버저닝 대응)

```typescript
// types/api.ts

// 백엔드 ChatResponse와 1:1 대응
export interface ChatResponse {
  answer: string;
  is_flagged: boolean;   // CRISIS_DETECTED → CrisisOverlay 표시
  red_alert: boolean;    // 위험 약물 → InfoCard border #FF0000
  reasoning: string;     // 오프라벨 근거 텍스트
}

export interface ChatRequest {
  user_id: number;
  message: string;
}

// 프론트엔드 내부 메시지 타입 (API 응답과 별개)
export type MessageRole = 'bot' | 'user';
export type MessageType = 'text' | 'info_card';  // info_card: red_alert 시 사용

export interface Message {
  id: number;
  role: MessageRole;
  type: MessageType;
  text: string;
  time: string;
  card?: {
    title: string;
    body: string;
    alert: boolean;  // true → border #FF0000
  };
}
```

#### 공통 버튼 컴포넌트 예시

```tsx
// components/Button/Button.tsx
import { COLOR } from '../../styles/tokens';

interface ButtonProps {
  label: string;
  onClick: () => void;
  disabled?: boolean;
}

export function Button({ label, onClick, disabled = false }: ButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        background: disabled ? '#ccc' : COLOR.btnBg,
        color: COLOR.btnText,
        border: 'none',
        borderRadius: '8px',
        padding: '10px 20px',
        fontSize: '14px',
        cursor: disabled ? 'not-allowed' : 'pointer',
      }}
    >
      {label}
    </button>
  );
}
```

---

### 3.3. 데이터베이스 (SQLAlchemy 2.0 async + Alembic)

#### ORM 선택 — SQLAlchemy 2.0 (async)
- ✅ **[HIGH Fix]** Tortoise ORM → **SQLAlchemy 2.0 async** 전환 권장.
  - 이유: 2025년 기준 생태계 성숙도, Alembic 마이그레이션 네이티브 지원, FastAPI 공식 예제 채택.
  - 전환 비용: `models.py` 재작성 + `asyncpg` 드라이버 교체 (약 1 스프린트 예상).

#### `chatlogs` Table Schema
```sql
-- ✅ [CRITICAL Fix] Alembic 마이그레이션으로 스키마 변경 관리
CREATE TABLE chatlogs (
    id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id     BIGINT NOT NULL,
    message     TEXT NOT NULL,
    response    TEXT NOT NULL,
    is_flagged  BOOLEAN NOT NULL DEFAULT FALSE,  -- 위기 키워드 포함 여부
    red_alert   BOOLEAN NOT NULL DEFAULT FALSE,  -- 심각한 부작용/금기 사항
    reasoning   TEXT,                            -- LLM 판단 근거 (감사 추적)
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at)
);
```

#### 마이그레이션 전략 (Alembic)
```python
# alembic/versions/001_add_chatlogs.py
def upgrade() -> None:
    op.create_table("chatlogs", ...)

def downgrade() -> None:
    op.drop_table("chatlogs")
```
- ✅ 모든 스키마 변경은 Alembic 마이그레이션으로 관리 — 직접 DDL 실행 금지.
- ✅ `is_flagged`, `red_alert` 컬럼에 `DEFAULT FALSE` 설정 → 기존 데이터 하위호환성 보장.

---

## 4. GPT-4o mini 활용 프롬프트 전략

- **모델:** `gpt-4o-mini` (OpenAI API)
- **페르소나:** "다정한 약사" (의학 용어 순화, 오프라벨 안심 시키기, 면책 조항 포함).
- **위기 대응:** 위기 키워드 감지 시 `CRISIS_DETECTED` 에러 코드 반환 — LLM 호출 완전 우회.
- **RAG 컨텍스트:** 약물 리스트와 API 데이터를 `Context` 섹션으로 정리하여 system prompt에 전달.
- **Structured Output:** OpenAI `response_format: { type: "json_object" }` 파라미터 사용.

```python
# GPT-4o mini Structured Output 호출 예시
from openai import AsyncOpenAI

client = AsyncOpenAI()

async def call_llm(system_prompt: str, user_message: str) -> ChatResponse:
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
    )
    raw = response.choices[0].message.content
    return ChatResponse.model_validate_json(raw)  # Pydantic v2
```

- **비용 최적화:** system prompt(페르소나 + 가이드라인)는 변경이 없으므로 최대한 간결하게 유지.
  - GPT-4o mini 입력 토큰: $0.15/1M tokens (2025 기준) — 불필요한 컨텍스트 제거로 절감.

---

## 5. 테스트 전략 (TDD — AGENTS.md 준수)

> **원칙:** 과잉·중복·자명한 테스트 금지. 행동(behavior) 기술 중심.

### 5.1. 단위 테스트 (pytest + pytest-asyncio)

```python
# ✅ 위기 필터 — 핵심 행동 테스트 (자살 / 자해 / 죽고싶)
def test_crisis_filter_returns_code_when_keyword_detected():
    result = crisis_filter("오늘 자해하고 싶어")
    assert result.code == "CRISIS_DETECTED"
    assert result.should_skip_llm is True

# ✅ LLM 미호출 검증 — Mock으로 경계 테스트
def test_crisis_filter_does_not_call_llm(mocker):
    mock_llm = mocker.patch("app.llm.openai_client.chat.completions.create")
    process_message("자살 충동이 있어")
    mock_llm.assert_not_called()

# ✅ Tool 인터페이스 계약 테스트
def test_medicine_api_tool_returns_fallback_on_timeout(mocker):
    mocker.patch("app.tools.medicine_api._call_external_api", side_effect=TimeoutError)
    result = MedicineAPITool().search("리스페리돈")
    assert result["source"] == "cache"
```

### 5.2. 제거 대상 테스트 (자명/중복)

- ❌ `test_user_id_returns_medicine_list` — 단순 DB SELECT, 자명함. SQLAlchemy가 이미 검증.
- ❌ `test_is_flagged_stored_in_db` — ORM 저장 동작 자체를 테스트하는 것은 중복.
- ❌ GPT-4o mini 응답 내용 단언 — 비결정적(non-deterministic), 통합 테스트로 커버.

### 5.3. 통합 테스트

```python
# ✅ Re-Act 에이전트 루프 제한 검증
async def test_agent_stops_at_max_iterations():
    agent = create_react_agent(mock_infinite_llm, tools, max_iterations=10)
    result = await agent.ainvoke({"input": "..."})
    assert result["iteration_count"] <= 10

# ✅ Red Alert 트리거 E2E
async def test_red_alert_triggered_for_dangerous_drug_combo():
    response = await client.post("/api/v1/chat", json={...})
    assert response.json()["red_alert"] is True
```

### 5.4. 테스트 실행

```bash
uv run pytest tests/ -v --asyncio-mode=auto
```

---

## 6. RAG 아키텍처 고도화 (2025/2026 Best Practices)

✅ **[HIGH Fix]** 단순 유사도 검색 → **Contextual Retrieval** 파이프라인:

```
Query → HyDE (가설 문서 생성) → Vector Search → Cross-Encoder Re-ranking → GPT-4o mini
```

1. **HyDE (Hypothetical Document Embeddings):** 사용자 질문으로 가설 답변 생성 후 임베딩 → 검색 정확도 향상.
2. **Re-ranking:** `cross-encoder/ms-marco-MiniLM` 모델로 Top-K 후보 재정렬.
3. **Contextual Retrieval:** 청크에 문서 맥락을 prepend → 검색 실패율 감소.

---

## 7. 핵심 구현 포인트

1. **오프라벨(Off-label) 설명:** GPT-4o mini structured output의 `reasoning` 필드로 "이 약은 원래 다른 용도지만, 신경전달물질 조절을 위해 흔히 쓰여요" 방식의 근거 자동 생성.
2. **테스트 코드 (Quality Assurance):** TDD Red→Green→Refactor 사이클 준수. 비결정적 LLM은 Mock으로 격리.
3. **데이터 시각화:** `chatlogs` + `reasoning` 필드를 분석하여 주간 복약 순응도 및 부작용 리포트 생성 (의사 전달용).

---

## 8. 기술 부채 및 개선 사항

- [x] ~~Re-Act 에이전트의 루프 제한(Max Iterations) 설정~~ → §2에서 해결
- [x] ~~식약처 API 응답 속도 저하에 따른 캐싱 전략~~ → §3.1 Circuit Breaker + Redis 캐싱
- [x] ~~LLM 교체: Claude → GPT-4o mini~~ → §4에서 확정
- [ ] Vector DB 선택 최종 확정: ChromaDB vs FAISS 벤치마크 (의학 가이드라인 문서 규모 기준)
- [ ] ChromaDB 인덱스 주기적 갱신 로직 — Blue/Green 방식으로 무중단 갱신
- [ ] Prometheus + Grafana: 에이전트 `iteration_count`, `tool_latency` 메트릭 수집
- [ ] SQLAlchemy 2.0 async 전환 완료 후 Tortoise ORM 의존성 제거
- [ ] OpenAI API 키 관리: 환경변수(`OPENAI_API_KEY`) + Secret Manager 연동
