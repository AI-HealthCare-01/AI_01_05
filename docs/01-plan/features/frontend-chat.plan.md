# frontend-chat Planning Document

> **Summary**: DodakTalk 챗봇 프론트엔드 — 채팅 UI, Red Alert 위기 경고, 퀵 메뉴 및 햄버거 메뉴 구현
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
| **Problem** | 백엔드 챗봇 API(`/api/v1/chat/ask`)는 완성되었지만, 사용자가 실제로 상호작용할 채팅 UI가 없어 서비스 이용이 불가능함 |
| **Solution** | React 기반 채팅 인터페이스 + Red Alert 위기 경고 오버레이 + 칩 기반 퀵 메뉴 + 좌측 슬라이드 햄버거 메뉴 구현 |
| **Function/UX Effect** | 말풍선 기반 대화, 위기 상황 시 화면 전체 붉은 경고 레이어 즉시 노출, 자주 묻는 질문 원터치 접근 |
| **Core Value** | 정신건강 약물 상담의 접근성 극대화 + 위기 상황 시각적 즉시 인지로 생명 보호 |

---

## 1. Overview

### 1.1 Purpose

DodakTalk 백엔드 API와 연동되는 채팅 프론트엔드를 구현한다. 일반 상담 대화와 위기 상황 경고를 시각적으로 명확히 구분하여, 사용자가 안전하게 약물 상담을 받을 수 있는 환경을 만든다.

### 1.2 Background

- 백엔드 API 완성: `POST /api/v1/chat/ask` (ChatRequest → ChatResponse)
- 응답에 `red_alert`, `alert_type`, `warning_level` 포함
- 프론트엔드 없이는 curl/Swagger로만 테스트 가능한 상태
- 요구사항: 채팅 말풍선, Red Alert 팝업, 칩 퀵 메뉴, 햄버거 메뉴

### 1.3 Related Documents

- `docs/01-plan/features/chat-core.plan.md` — 백엔드 핵심 기능 Plan
- `docs/01-plan/features/crisis-filter.plan.md` — 위기 감지 필터 Plan
- Backend API: `app/apis/v1/chatbot.py`
- DTO: `app/dtos/chat.py`

---

## 2. Scope

### 2.1 In Scope

- [ ] 채팅 메인 화면 (말풍선 컴포넌트, 스크롤, 입력창)
- [ ] Red Alert 오버레이 (위기 감지 시 화면 전체 경고 레이어)
- [ ] 칩(Chip) 기반 퀵 메뉴 (자주 묻는 질문 원터치)
- [ ] 좌측 슬라이드 햄버거 메뉴 (설정, 대화 기록, 약물 관리)
- [ ] `POST /api/v1/chat/ask` API 연동
- [ ] 로딩 상태 표시 (AI 답변 대기 중 타이핑 인디케이터)
- [ ] 반응형 레이아웃 (모바일 우선)

### 2.2 Out of Scope

- 카카오 로그인 UI (별도 feature로 분리)
- 리포트/차트 화면
- 실시간 WebSocket 스트리밍 (Phase 2)
- PWA / 네이티브 앱 변환
- 다크 모드

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-01 | 말풍선 채팅 UI — 사용자(우측)/AI(좌측) 구분 | High | Pending |
| FR-02 | 메시지 입력창 + 전송 버튼 (Enter 키 전송 지원) | High | Pending |
| FR-03 | API 호출 중 타이핑 인디케이터 표시 | High | Pending |
| FR-04 | `red_alert=true` 응답 시 Red Alert 오버레이 활성화 | High | Pending |
| FR-05 | Red Alert: 화면 테두리 붉은 깜빡임 + 상담 번호 카드 오버레이 | High | Pending |
| FR-06 | `warning_level="Caution"` 시 답변 말풍선 테두리 주황색 강조 | Medium | Pending |
| FR-07 | 칩(Chip) 퀵 메뉴 — 입력창 상단에 자주 묻는 질문 버튼 | Medium | Pending |
| FR-08 | 햄버거 메뉴 (좌측 슬라이드) — 대화 기록, 약물 관리, 설정 | Medium | Pending |
| FR-09 | 메시지 자동 스크롤 (새 메시지 시 하단으로) | Medium | Pending |
| FR-10 | 모바일 반응형 (최소 360px 지원) | Medium | Pending |

### 3.2 Non-Functional Requirements

| Category | Criteria | Measurement Method |
|----------|----------|-------------------|
| Performance | 메시지 전송 후 UI 반응 < 100ms | 체감 테스트 |
| Accessibility | 키보드 네비게이션 지원 | 수동 테스트 |
| UX | Red Alert 노출 시 1초 이내 인지 가능 | 사용자 테스트 |
| Compatibility | Chrome, Safari, 모바일 브라우저 | 크로스 브라우저 테스트 |

---

## 4. UI Components

### 4.1 화면 구성

```
┌─────────────────────────────────────────┐
│ ☰  DodakTalk                    [약물]  │  ← 헤더 (햄버거 + 타이틀 + 약물 관리)
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────────────┐                   │
│  │ 안녕하세요! 도닥톡│                   │  ← AI 말풍선 (좌측)
│  │ 입니다. 무엇이든  │                   │
│  │ 물어보세요.       │                   │
│  └──────────────────┘                   │
│                                         │
│                   ┌──────────────────┐   │
│                   │ 혈압약과 감기약   │   │  ← 사용자 말풍선 (우측)
│                   │ 같이 먹어도 돼요? │   │
│                   └──────────────────┘   │
│                                         │
│  ┌──────────────────┐                   │
│  │ 아모디핀과 타이레 │                   │  ← AI 답변 말풍선
│  │ 놀은 일반적으로...│                   │
│  └──────────────────┘                   │
│                                         │
├─────────────────────────────────────────┤
│ [부작용이 걱정돼요] [약 먹는 시간] [상호작용] │  ← 칩 퀵 메뉴
├─────────────────────────────────────────┤
│ 💬 메시지를 입력하세요...          [전송] │  ← 입력창
└─────────────────────────────────────────┘
```

### 4.2 Red Alert 오버레이

```
┌─────────────────────────────────────────┐
│░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
│░┌─────────────────────────────────────┐░│
│░│                                     │░│
│░│     지금 많이 힘드시군요.            │░│
│░│     전문가가 도와드릴 수 있습니다.    │░│
│░│                                     │░│
│░│  ┌───────────────────────────────┐  │░│
│░│  │  자살예방상담전화 1393 (24시간) │  │░│  ← 터치 시 전화 연결
│░│  └───────────────────────────────┘  │░│
│░│  ┌───────────────────────────────┐  │░│
│░│  │  정신건강위기상담 1577-0199    │  │░│
│░│  └───────────────────────────────┘  │░│
│░│  ┌───────────────────────────────┐  │░│
│░│  │  생명의전화 1588-9191         │  │░│
│░│  └───────────────────────────────┘  │░│
│░│                                     │░│
│░│          [ 대화로 돌아가기 ]         │░│
│░│                                     │░│
│░└─────────────────────────────────────┘░│
│░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│  ← 붉은 배경 + 깜빡임
└─────────────────────────────────────────┘
```

### 4.3 햄버거 메뉴 (좌측 슬라이드)

```
┌──────────────────┬──────────────────────┐
│                  │                      │
│  도닥톡           │  (채팅 화면 어둡게)   │
│                  │                      │
│  ─────────────── │                      │
│  💊 약물 관리     │                      │
│  📋 대화 기록     │                      │
│  ⚙️ 설정          │                      │
│  ❓ 도움말        │                      │
│                  │                      │
│                  │                      │
│  ─────────────── │                      │
│  v1.0.0          │                      │
└──────────────────┴──────────────────────┘
```

---

## 5. API Integration

### 5.1 Request/Response 스펙

```typescript
// Request
interface ChatRequest {
  message: string;
  medication_list: string[];
  user_note?: string;
}

// Response
interface ChatResponse {
  answer: string;
  warning_level: "Normal" | "Caution" | "Critical";
  red_alert: boolean;
  alert_type: "Direct" | "Indirect" | "Substance" | null;
}
```

### 5.2 API 호출 흐름

```
사용자 입력 → POST /api/v1/chat/ask → 응답 수신
                                          ├─ red_alert=false → 일반 말풍선
                                          ├─ warning_level="Caution" → 주황 말풍선
                                          └─ red_alert=true → Red Alert 오버레이
```

---

## 6. Success Criteria

### 6.1 Definition of Done

- [ ] 채팅 말풍선 UI 렌더링 (사용자/AI 구분)
- [ ] API 호출 및 응답 표시 동작
- [ ] Red Alert 오버레이 정상 노출 (red_alert=true 시)
- [ ] 칩 퀵 메뉴 터치 → 메시지 전송 동작
- [ ] 햄버거 메뉴 열기/닫기 동작
- [ ] 모바일 반응형 확인 (360px~)

### 6.2 Quality Criteria

- [ ] Lighthouse Performance > 90
- [ ] 크로스 브라우저 테스트 (Chrome, Safari)
- [ ] 키보드 접근성 (Tab, Enter)

---

## 7. Risks and Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| API 응답 지연 (OpenAI 10s+) | Medium | High | 타이핑 인디케이터 + 타임아웃 안내 메시지 |
| Red Alert 과도한 시각 자극 | Medium | Low | 깜빡임 3회 후 정지, 닫기 버튼 명확 배치 |
| CORS 이슈 | High | Medium | FastAPI CORS 미들웨어 이미 설정 완료 |
| 모바일 키보드로 인한 레이아웃 깨짐 | Medium | High | viewport 설정 + 입력창 고정 배치 |

---

## 8. Architecture Considerations

### 8.1 Project Level Selection

| Level | Characteristics | Recommended For | Selected |
|-------|-----------------|-----------------|:--------:|
| **Starter** | Simple structure | Static sites | ☐ |
| **Dynamic** | Feature-based modules | Web apps, SaaS MVPs | ☑ |
| **Enterprise** | Strict layer separation | High-traffic systems | ☐ |

### 8.2 Key Architectural Decisions

| Decision | Options | Selected | Rationale |
|----------|---------|----------|-----------|
| Framework | React / Vue / Svelte / Vanilla | React | 팀 숙련도, 생태계, 컴포넌트 재사용 |
| Build Tool | Vite / CRA / Next.js | Vite | 빠른 개발 서버, 경량, SPA 적합 |
| Styling | Tailwind / CSS Modules / styled-components | Tailwind CSS | 빠른 프로토타이핑, 유틸리티 우선 |
| State | Context / Zustand / Redux | React Context | 단순한 상태 (메시지 리스트, 메뉴 토글) |
| HTTP Client | fetch / axios | fetch | 추가 의존성 없음, 충분한 기능 |
| TypeScript | Yes / No | Yes | 타입 안전성, API 스펙 일치 보장 |

### 8.3 프로젝트 구조

```
frontend/
├── src/
│   ├── components/
│   │   ├── ChatBubble.tsx          ← 말풍선 (사용자/AI)
│   │   ├── ChatInput.tsx           ← 입력창 + 전송 버튼
│   │   ├── ChipMenu.tsx            ← 퀵 메뉴 칩
│   │   ├── RedAlertOverlay.tsx     ← 위기 경고 오버레이
│   │   ├── HamburgerMenu.tsx       ← 좌측 슬라이드 메뉴
│   │   ├── TypingIndicator.tsx     ← AI 응답 대기 표시
│   │   └── Header.tsx              ← 상단 헤더
│   ├── pages/
│   │   └── ChatPage.tsx            ← 메인 채팅 페이지
│   ├── api/
│   │   └── chatApi.ts              ← API 호출 함수
│   ├── types/
│   │   └── chat.ts                 ← ChatRequest, ChatResponse 타입
│   ├── App.tsx
│   └── main.tsx
├── index.html
├── package.json
├── tailwind.config.js
├── tsconfig.json
└── vite.config.ts
```

---

## 9. Convention Prerequisites

### 9.1 Environment Variables Needed

| Variable | Purpose | Scope | Status |
|----------|---------|-------|:------:|
| `VITE_API_BASE_URL` | 백엔드 API 주소 | Client | ☐ Needed |

---

## 10. Next Steps

1. [ ] Design 문서 작성 (`frontend-chat.design.md`)
2. [ ] 팀 리뷰 및 승인 (특히 UI/UX 레이아웃)
3. [ ] React + Vite 프로젝트 초기화
4. [ ] 컴포넌트 구현 시작

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-03-09 | Initial draft | Team AI-HealthCare |
