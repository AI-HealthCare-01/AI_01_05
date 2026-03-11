# frontend-chat Design Document

> **Summary**: DodakTalk 채팅 프론트엔드 상세 설계 — React + Vite + Tailwind CSS 기반 7개 컴포넌트, Red Alert 오버레이, API 연동
>
> **Project**: DodakTalk (도닥톡)
> **Version**: v1.0.0
> **Author**: Team AI-HealthCare
> **Date**: 2026-03-09
> **Status**: Draft
> **Planning Doc**: [frontend-chat.plan.md](../../01-plan/features/frontend-chat.plan.md)

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | 백엔드 챗봇 API(`/api/v1/chat/ask`)는 완성되었지만, 사용자가 실제로 상호작용할 채팅 UI가 없어 서비스 이용이 불가능함 |
| **Solution** | React 18 + Vite + Tailwind CSS로 7개 컴포넌트(ChatBubble, ChatInput, ChipMenu, RedAlertOverlay, HamburgerMenu, TypingIndicator, Header) 구현, React Context로 상태 관리 |
| **Function/UX Effect** | 말풍선 대화 UI, 위기 시 전체 화면 붉은 경고 즉시 노출(1초 이내 인지), 칩 퀵 메뉴 원터치 접근, 모바일 360px 반응형 |
| **Core Value** | 정신건강 약물 상담의 접근성 극대화 + Red Alert로 위기 상황 즉시 인지하여 생명 보호 |

---

## 1. Overview

### 1.1 Design Goals

- 7개 독립 React 컴포넌트로 채팅 UI를 구성하여 재사용성과 테스트 용이성 확보
- Red Alert 오버레이를 최우선 레이어로 설계하여 위기 상황 즉각 인지 보장
- 모바일 우선(Mobile First) 반응형으로 360px ~ 1440px 전체 범위 지원
- `fetch` API로 백엔드 연동, 추가 라이브러리 의존성 최소화

### 1.2 Design Principles

- **Mobile First**: 360px 기준 설계 후 데스크톱 확장
- **Accessibility**: 키보드 네비게이션(Tab, Enter, Escape), 스크린 리더 대응
- **Progressive Enhancement**: Red Alert는 항상 동작, 애니메이션은 `prefers-reduced-motion` 존중
- **Separation of Concerns**: UI 컴포넌트 / API 레이어 / 상태 관리를 명확히 분리

---

## 2. Architecture

### 2.1 Component Tree

```
<App>
  └─ <ChatProvider>          ← React Context (상태 관리)
      ├─ <Header />           ← 햄버거 버튼 + 타이틀 + 약물 관리 버튼
      ├─ <HamburgerMenu />    ← 좌측 슬라이드 메뉴 (조건부 렌더링)
      ├─ <ChatPage>           ← 메인 페이지 컴포넌트
      │   ├─ <MessageList>    ← 메시지 목록 (스크롤 영역)
      │   │   ├─ <ChatBubble />   ← AI 말풍선 (좌측)
      │   │   ├─ <ChatBubble />   ← 사용자 말풍선 (우측)
      │   │   └─ <TypingIndicator />  ← 로딩 표시
      │   ├─ <ChipMenu />     ← 퀵 메뉴 칩 버튼
      │   └─ <ChatInput />    ← 입력창 + 전송 버튼
      └─ <RedAlertOverlay />  ← 위기 경고 (Portal, z-index 최상위)
```

### 2.2 Data Flow

```
사용자 입력 (ChatInput)
    │
    ├─ dispatch({ type: "ADD_USER_MESSAGE", payload: message })
    │
    ▼
ChatProvider (useReducer)
    │
    ├─ 메시지 리스트에 사용자 메시지 추가
    ├─ isLoading = true (TypingIndicator 표시)
    │
    ▼
chatApi.sendMessage(request)
    │
    ├─ POST /api/v1/chat/ask
    │
    ▼
응답 수신 (ChatResponse)
    │
    ├─ dispatch({ type: "ADD_AI_MESSAGE", payload: response })
    ├─ isLoading = false
    │
    ├─ red_alert === true
    │   └─ dispatch({ type: "SHOW_RED_ALERT", payload: response.answer })
    │
    ├─ warning_level === "Caution"
    │   └─ ChatBubble에 주황 테두리 props 전달
    │
    └─ warning_level === "Normal"
        └─ 일반 ChatBubble 렌더링
```

### 2.3 Dependencies (NPM)

| Package | Version | Purpose |
|---------|---------|---------|
| `react` | ^18.3 | UI 프레임워크 |
| `react-dom` | ^18.3 | DOM 렌더링 |
| `typescript` | ^5.4 | 타입 안전성 |
| `tailwindcss` | ^3.4 | 유틸리티 CSS |
| `vite` | ^5.4 | 빌드 도구 |
| `@vitejs/plugin-react` | ^4.3 | Vite React 플러그인 |

> **의존성 최소화 원칙**: 상태 관리(React Context), HTTP(fetch), 라우팅(SPA 단일 페이지) 모두 내장 기능 사용

---

## 3. Data Model (TypeScript Types)

### 3.1 API Types

```typescript
// src/types/chat.ts

export interface ChatRequest {
  message: string;
  medication_list: string[];
  user_note?: string;
}

export interface ChatResponse {
  answer: string;
  warning_level: "Normal" | "Caution" | "Critical";
  red_alert: boolean;
  alert_type: "Direct" | "Indirect" | "Substance" | "Context" | null;
}
```

### 3.2 UI State Types

```typescript
// src/types/chat.ts

export type MessageRole = "user" | "ai";

export interface Message {
  id: string;                    // crypto.randomUUID()
  role: MessageRole;
  content: string;
  timestamp: Date;
  warningLevel?: "Normal" | "Caution" | "Critical";
}

export interface ChatState {
  messages: Message[];
  isLoading: boolean;
  showRedAlert: boolean;
  redAlertMessage: string | null;
  isMenuOpen: boolean;
  medicationList: string[];
}

export type ChatAction =
  | { type: "ADD_USER_MESSAGE"; payload: string }
  | { type: "ADD_AI_MESSAGE"; payload: ChatResponse }
  | { type: "SET_LOADING"; payload: boolean }
  | { type: "SHOW_RED_ALERT"; payload: string }
  | { type: "HIDE_RED_ALERT" }
  | { type: "TOGGLE_MENU" }
  | { type: "CLOSE_MENU" }
  | { type: "SET_MEDICATIONS"; payload: string[] };
```

---

## 4. API Specification

### 4.1 API Client

```typescript
// src/api/chatApi.ts

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8001";

export async function sendMessage(request: ChatRequest): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/chat/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}
```

### 4.2 API 호출 흐름

```
ChatInput.onSubmit()
    │
    ▼
sendMessage({ message, medication_list, user_note })
    │
    ├─ 성공 (200 OK)
    │   ├─ red_alert=false → ADD_AI_MESSAGE (일반 말풍선)
    │   ├─ warning_level="Caution" → ADD_AI_MESSAGE (주황 말풍선)
    │   └─ red_alert=true → ADD_AI_MESSAGE + SHOW_RED_ALERT
    │
    └─ 실패 (네트워크/서버 에러)
        └─ ADD_AI_MESSAGE({ answer: "연결 오류...", warning_level: "Normal", ... })
```

---

## 5. UI/UX Design

### 5.1 컴포넌트 상세 설계

#### 5.1.1 Header (FR-08 관련)

```
┌─────────────────────────────────────────┐
│  [☰]     DodakTalk  도닥톡      [💊]    │
└─────────────────────────────────────────┘
```

| Props | Type | Description |
|-------|------|-------------|
| `onMenuToggle` | `() => void` | 햄버거 메뉴 토글 |
| `onMedicationClick` | `() => void` | 약물 관리 화면 이동 (Phase 2) |

**스타일:**
- 높이: `h-14` (56px)
- 배경: `bg-white shadow-sm`
- 고정: `sticky top-0 z-30`
- 타이틀: `text-lg font-bold text-teal-600`

#### 5.1.2 ChatBubble (FR-01, FR-06)

| Props | Type | Description |
|-------|------|-------------|
| `message` | `Message` | 메시지 데이터 |

**렌더링 규칙:**

| Condition | 정렬 | 배경 | 테두리 |
|-----------|------|------|--------|
| `role === "user"` | 우측 (`justify-end`) | `bg-teal-500 text-white` | 없음 |
| `role === "ai"` + `Normal` | 좌측 (`justify-start`) | `bg-gray-100` | 없음 |
| `role === "ai"` + `Caution` | 좌측 | `bg-orange-50` | `border-2 border-orange-400` |
| `role === "ai"` + `Critical` | 좌측 | `bg-red-50` | `border-2 border-red-400` |

**말풍선 스타일:**
- 최대 너비: `max-w-[80%]`
- 모서리: `rounded-2xl` (사용자), `rounded-2xl rounded-tl-sm` (AI)
- 패딩: `px-4 py-3`
- 글자 크기: `text-sm` (모바일), `text-base` (데스크톱)

#### 5.1.3 ChatInput (FR-02)

```
┌─────────────────────────────────────────┐
│  메시지를 입력하세요...           [전송]  │
└─────────────────────────────────────────┘
```

| Props | Type | Description |
|-------|------|-------------|
| `onSend` | `(message: string) => void` | 메시지 전송 콜백 |
| `disabled` | `boolean` | 로딩 중 비활성화 |

**동작:**
- Enter 키: 메시지 전송 (Shift+Enter: 줄바꿈)
- 빈 메시지 전송 방지
- 전송 후 입력창 자동 포커스 유지
- `disabled=true` 시 입력/버튼 비활성화

**스타일:**
- 고정: `sticky bottom-0`
- 배경: `bg-white border-t`
- 입력: `flex-1 rounded-full bg-gray-100 px-4 py-2`
- 전송 버튼: `bg-teal-500 text-white rounded-full w-10 h-10`

#### 5.1.4 TypingIndicator (FR-03)

```
  ┌──────────┐
  │  ● ● ●   │   ← 3개 점이 순차적으로 바운스
  └──────────┘
```

| Props | Type | Description |
|-------|------|-------------|
| `visible` | `boolean` | 표시 여부 |

**애니메이션:**
- 3개 원형 `div`가 `animation-delay`로 순차 바운스
- Tailwind `@keyframes bounce` 활용
- `prefers-reduced-motion` 시 정적 "..." 텍스트로 대체

#### 5.1.5 RedAlertOverlay (FR-04, FR-05)

| Props | Type | Description |
|-------|------|-------------|
| `visible` | `boolean` | 표시 여부 |
| `message` | `string \| null` | 위기 답변 메시지 |
| `onClose` | `() => void` | 닫기 콜백 |

**레이어 구조:**
- `z-50` (최상위), `fixed inset-0`
- Portal (`ReactDOM.createPortal`)로 DOM 트리 최상위에 렌더링

**애니메이션:**
- 테두리 붉은 깜빡임: `@keyframes red-pulse` (3회 후 정지)
- 배경: `bg-red-900/80` (반투명 어두운 빨강)
- `animation-iteration-count: 3` 로 과도한 시각 자극 방지

**상담 전화 카드:**

```typescript
const CRISIS_CONTACTS = [
  { name: "자살예방상담전화", number: "1393", desc: "24시간" },
  { name: "정신건강위기상담", number: "1577-0199", desc: "" },
  { name: "생명의전화", number: "1588-9191", desc: "" },
];
```

- 각 카드: `<a href="tel:1393">` 터치 시 전화 연결
- 스타일: `bg-white rounded-xl p-4 text-center shadow-lg`
- 닫기 버튼: "대화로 돌아가기" `bg-white/20 text-white rounded-full`

#### 5.1.6 ChipMenu (FR-07)

```
[부작용이 걱정돼요] [약 먹는 시간] [상호작용] [오프라벨이 뭔가요?]
```

| Props | Type | Description |
|-------|------|-------------|
| `onChipClick` | `(text: string) => void` | 칩 선택 시 메시지 전송 |
| `disabled` | `boolean` | 로딩 중 비활성화 |

**퀵 메뉴 항목:**

```typescript
const QUICK_QUESTIONS = [
  "부작용이 걱정돼요",
  "약 먹는 시간이 궁금해요",
  "다른 약과 같이 먹어도 되나요?",
  "오프라벨 처방이 뭔가요?",
];
```

**스타일:**
- 수평 스크롤: `overflow-x-auto flex gap-2 px-4 py-2`
- 각 칩: `whitespace-nowrap rounded-full bg-teal-50 text-teal-700 px-3 py-1.5 text-sm border border-teal-200`
- 호버: `hover:bg-teal-100`
- 스크롤바 숨김: `scrollbar-hide`

#### 5.1.7 HamburgerMenu (FR-08)

| Props | Type | Description |
|-------|------|-------------|
| `isOpen` | `boolean` | 열림 상태 |
| `onClose` | `() => void` | 닫기 콜백 |

**메뉴 항목:**

```typescript
const MENU_ITEMS = [
  { icon: "💊", label: "약물 관리", path: "/medications" },
  { icon: "📋", label: "대화 기록", path: "/history" },
  { icon: "⚙️", label: "설정", path: "/settings" },
  { icon: "❓", label: "도움말", path: "/help" },
];
```

**동작:**
- 좌측에서 슬라이드: `transform translateX(-100%) → translateX(0)`
- `transition-transform duration-300`
- 배경 오버레이: `bg-black/50` 클릭 시 닫기
- Escape 키로 닫기
- 너비: `w-64` (256px)

### 5.2 반응형 브레이크포인트

| Breakpoint | Width | Layout Changes |
|------------|-------|----------------|
| `sm` | 360px~ | 기본 모바일 레이아웃 |
| `md` | 768px~ | 말풍선 `max-w-[70%]`, 패딩 증가 |
| `lg` | 1024px~ | 채팅 영역 최대 `max-w-2xl mx-auto` (중앙 정렬) |

### 5.3 Color Palette (Tailwind)

| Purpose | Color | Tailwind Class |
|---------|-------|---------------|
| 브랜드 Primary | Teal 500 | `bg-teal-500`, `text-teal-500` |
| 사용자 말풍선 | Teal 500 | `bg-teal-500 text-white` |
| AI 말풍선 | Gray 100 | `bg-gray-100 text-gray-900` |
| Caution 강조 | Orange 400 | `border-orange-400 bg-orange-50` |
| Critical/Red Alert | Red 900 | `bg-red-900/80` |
| 배경 | White | `bg-white` |

---

## 6. State Management

### 6.1 ChatContext (React Context + useReducer)

```typescript
// src/context/ChatContext.tsx

const initialState: ChatState = {
  messages: [{
    id: "welcome",
    role: "ai",
    content: "안녕하세요! 도닥톡입니다. 약에 대해 궁금한 점이 있으시면 편하게 물어보세요.",
    timestamp: new Date(),
    warningLevel: "Normal",
  }],
  isLoading: false,
  showRedAlert: false,
  redAlertMessage: null,
  isMenuOpen: false,
  medicationList: [],
};

function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case "ADD_USER_MESSAGE":
      return {
        ...state,
        messages: [...state.messages, {
          id: crypto.randomUUID(),
          role: "user",
          content: action.payload,
          timestamp: new Date(),
        }],
      };

    case "ADD_AI_MESSAGE": {
      const response = action.payload;
      const newState = {
        ...state,
        isLoading: false,
        messages: [...state.messages, {
          id: crypto.randomUUID(),
          role: "ai" as const,
          content: response.answer,
          timestamp: new Date(),
          warningLevel: response.warning_level,
        }],
      };
      if (response.red_alert) {
        newState.showRedAlert = true;
        newState.redAlertMessage = response.answer;
      }
      return newState;
    }

    case "SET_LOADING":
      return { ...state, isLoading: action.payload };

    case "SHOW_RED_ALERT":
      return { ...state, showRedAlert: true, redAlertMessage: action.payload };

    case "HIDE_RED_ALERT":
      return { ...state, showRedAlert: false, redAlertMessage: null };

    case "TOGGLE_MENU":
      return { ...state, isMenuOpen: !state.isMenuOpen };

    case "CLOSE_MENU":
      return { ...state, isMenuOpen: false };

    case "SET_MEDICATIONS":
      return { ...state, medicationList: action.payload };

    default:
      return state;
  }
}
```

### 6.2 메시지 전송 핸들러

```typescript
// ChatPage.tsx 내부
async function handleSendMessage(text: string) {
  dispatch({ type: "ADD_USER_MESSAGE", payload: text });
  dispatch({ type: "SET_LOADING", payload: true });

  try {
    const response = await sendMessage({
      message: text,
      medication_list: state.medicationList,
    });
    dispatch({ type: "ADD_AI_MESSAGE", payload: response });
  } catch {
    dispatch({
      type: "ADD_AI_MESSAGE",
      payload: {
        answer: "네트워크 연결에 문제가 있습니다. 잠시 후 다시 시도해 주세요.",
        warning_level: "Normal",
        red_alert: false,
        alert_type: null,
      },
    });
  }
}
```

---

## 7. Error Handling

### 7.1 에러 시나리오별 처리

| Scenario | UI Behavior |
|----------|-------------|
| API 네트워크 에러 | AI 말풍선으로 "연결 오류" 메시지 표시 |
| API 500 에러 | AI 말풍선으로 "서버 오류" 메시지 표시 |
| API 응답 지연 (>15s) | 타이핑 인디케이터 유지 + "응답이 지연되고 있습니다" 안내 |
| 빈 메시지 전송 시도 | 전송 버튼 비활성화, 전송 방지 |
| Red Alert 오버레이 표시 중 추가 메시지 | 오버레이 닫기 전까지 입력 차단 |

### 7.2 API 타임아웃 처리

```typescript
// src/api/chatApi.ts
export async function sendMessage(request: ChatRequest): Promise<ChatResponse> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000); // 30초

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/chat/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
      signal: controller.signal,
    });
    if (!response.ok) throw new Error(`API error: ${response.status}`);
    return response.json();
  } finally {
    clearTimeout(timeoutId);
  }
}
```

---

## 8. Security Considerations

- [x] API Base URL은 환경 변수(`VITE_API_BASE_URL`)로 관리
- [ ] XSS 방지: `dangerouslySetInnerHTML` 사용 금지, React 기본 이스케이핑 활용
- [ ] CORS: FastAPI 서버에 프론트엔드 도메인 허용 설정 확인
- [ ] 입력 길이 제한: `maxLength={2000}` 적용
- [ ] Red Alert 오버레이에서 `tel:` 링크의 자동 다이얼 동작 사용자 확인 필수

---

## 9. Test Plan

### 9.1 Test Scope

| Type | Target | Tool |
|------|--------|------|
| Unit Test | ChatBubble 렌더링 (역할/경고 레벨별) | Vitest + React Testing Library |
| Unit Test | chatReducer 상태 변환 | Vitest |
| Unit Test | ChatInput 전송 동작 | Vitest + React Testing Library |
| Integration | 메시지 전송 → API 호출 → 말풍선 추가 | Vitest + MSW (Mock Service Worker) |
| Integration | Red Alert 응답 → 오버레이 표시 | Vitest + React Testing Library |
| E2E | 전체 채팅 흐름 (수동 테스트) | Chrome DevTools |

### 9.2 Key Test Cases

- [ ] 사용자 메시지 전송 → 우측 말풍선 렌더링
- [ ] AI 응답 수신 → 좌측 말풍선 렌더링
- [ ] `warning_level="Caution"` → 주황 테두리 말풍선
- [ ] `red_alert=true` → RedAlertOverlay 표시
- [ ] Red Alert "대화로 돌아가기" 클릭 → 오버레이 닫기
- [ ] 칩 메뉴 클릭 → 해당 텍스트로 메시지 전송
- [ ] 로딩 중 → TypingIndicator 표시 + 입력창 비활성화
- [ ] 햄버거 메뉴 열기/닫기 + Escape 키 닫기
- [ ] 모바일 360px 뷰포트에서 레이아웃 깨짐 없음
- [ ] Enter 키 전송, Shift+Enter 줄바꿈

---

## 10. Coding Convention Reference

### 10.1 Naming Conventions (TypeScript/React)

| Target | Rule | Example |
|--------|------|---------|
| Component | PascalCase | `ChatBubble`, `RedAlertOverlay` |
| Function | camelCase | `handleSendMessage`, `sendMessage` |
| Constant | UPPER_SNAKE_CASE | `QUICK_QUESTIONS`, `CRISIS_CONTACTS` |
| Type/Interface | PascalCase | `ChatRequest`, `Message` |
| File (component) | PascalCase.tsx | `ChatBubble.tsx`, `RedAlertOverlay.tsx` |
| File (utility) | camelCase.ts | `chatApi.ts`, `chat.ts` |
| CSS class | Tailwind utility | `bg-teal-500 rounded-2xl` |

### 10.2 Import Order

```typescript
// 1. React
import { useState, useEffect, useRef } from "react";

// 2. Third-party (none expected)

// 3. Local — types
import type { Message, ChatResponse } from "../types/chat";

// 4. Local — components
import { ChatBubble } from "../components/ChatBubble";

// 5. Local — utilities
import { sendMessage } from "../api/chatApi";
```

### 10.3 Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `VITE_API_BASE_URL` | 백엔드 API 주소 | `http://localhost:8001` |

---

## 11. Implementation Guide

### 11.1 File Structure

```
frontend/
├── src/
│   ├── api/
│   │   └── chatApi.ts              ← API 호출 함수
│   ├── components/
│   │   ├── ChatBubble.tsx          ← 말풍선 (사용자/AI)
│   │   ├── ChatInput.tsx           ← 입력창 + 전송 버튼
│   │   ├── ChipMenu.tsx            ← 퀵 메뉴 칩
│   │   ├── Header.tsx              ← 상단 헤더
│   │   ├── HamburgerMenu.tsx       ← 좌측 슬라이드 메뉴
│   │   ├── RedAlertOverlay.tsx     ← 위기 경고 오버레이
│   │   └── TypingIndicator.tsx     ← AI 응답 대기 표시
│   ├── context/
│   │   └── ChatContext.tsx         ← React Context + useReducer
│   ├── pages/
│   │   └── ChatPage.tsx            ← 메인 채팅 페이지 (조합)
│   ├── types/
│   │   └── chat.ts                 ← TypeScript 타입 정의
│   ├── App.tsx                     ← 루트 컴포넌트
│   ├── main.tsx                    ← 엔트리 포인트
│   └── index.css                   ← Tailwind directives
├── public/
│   └── favicon.svg
├── index.html
├── package.json
├── tailwind.config.js
├── tsconfig.json
├── vite.config.ts
└── .env.local                      ← VITE_API_BASE_URL
```

### 11.2 Implementation Order

1. [ ] Vite + React + TypeScript + Tailwind 프로젝트 초기화
2. [ ] TypeScript 타입 정의 (`src/types/chat.ts`)
3. [ ] API 클라이언트 (`src/api/chatApi.ts`)
4. [ ] ChatContext + chatReducer (`src/context/ChatContext.tsx`)
5. [ ] ChatBubble 컴포넌트 (역할별 스타일, Caution 테두리)
6. [ ] ChatInput 컴포넌트 (Enter 전송, Shift+Enter 줄바꿈)
7. [ ] TypingIndicator 컴포넌트
8. [ ] Header 컴포넌트
9. [ ] ChipMenu 컴포넌트
10. [ ] HamburgerMenu 컴포넌트 (슬라이드 + 오버레이)
11. [ ] RedAlertOverlay 컴포넌트 (Portal + 애니메이션 + tel: 링크)
12. [ ] ChatPage 페이지 조합 (자동 스크롤 포함)
13. [ ] App.tsx 통합 + 반응형 테스트
14. [ ] Vite proxy 설정 (개발 환경 CORS 우회)

### 11.3 프로젝트 초기화 명령어

```bash
# 1. Vite 프로젝트 생성
npm create vite@latest frontend -- --template react-ts
cd frontend

# 2. Tailwind CSS 설치
npm install -D tailwindcss @tailwindcss/vite

# 3. 개발 서버 시작
npm run dev
```

### 11.4 Vite Proxy 설정 (개발 환경)

```typescript
// vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target: "http://localhost:8001",
        changeOrigin: true,
      },
    },
  },
});
```

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-03-09 | Initial draft | Team AI-HealthCare |
