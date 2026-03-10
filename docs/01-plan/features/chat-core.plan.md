# chat-core Planning Document

> **Summary**: AI 헬스케어 챗봇 핵심 기능 — 위기 감지, LLM 상담, RAG 검색, 대화 저장의 전체 파이프라인 구현
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
| **Problem** | 정신건강 약물 복용자가 약물 상호작용, 부작용, 오프라벨 처방에 대해 신뢰할 수 있는 정보를 즉시 얻기 어려우며, 위기 상황 시 적시 개입이 부재함 |
| **Solution** | Rule-based 위기 필터 + RAG(식약처 API + Vector DB) + LLM(GPT-4o-mini)이 결합된 하이브리드 챗봇으로 실시간 약물 상담 및 위기 대응 제공 |
| **Function/UX Effect** | 위기 키워드 입력 시 1초 이내 1393 안내 반환, 일반 질문 시 약물 DB 기반 근거 있는 답변 생성, Red Alert UI로 즉각 인지 가능 |
| **Core Value** | 복약 안전성 향상 + 위기 상황 즉시 개입으로 사용자 생명 보호 |

---

## 1. Overview

### 1.1 Purpose

정신건강 약물 복용자를 위한 AI 상담 챗봇의 핵심 백엔드 파이프라인을 완성한다. 사용자 질문 입력부터 위기 감지, 약물 정보 검색, LLM 추론, 응답 저장까지의 6단계 전체 흐름을 구현한다.

### 1.2 Background

- 정신과 약물 복용자는 '오프라벨 처방'에 대한 불안, 부작용 걱정, 약물 상호작용 우려가 높음
- 기존 검색 엔진은 공포감을 유발하는 정보 위주로 노출
- 위기 상황(자살/자해 충동) 시 즉각적인 전문 상담 연결이 필요
- 현재 기본 LLM 호출과 키워드 필터만 구현된 상태, RAG와 페르소나 고도화 필요

### 1.3 Related Documents

- Architecture Flow: 6단계 서비스 아키텍처 (입력 → 필터링 → 컨텍스트 → RAG → LLM → 출력)
- CLAUDE.md: 프로젝트 컨벤션 및 구조 정의

---

## 2. Scope

### 2.1 In Scope

- [x] 위기 키워드 필터링 (Direct/Indirect/Substance) — **구현 완료**
- [x] OpenAI GPT-4o-mini 비동기 호출 — **구현 완료**
- [x] ChatLog DB 저장 (is_flagged 포함) — **구현 완료**
- [x] `/api/v1/chat/ask` 엔드포인트 — **구현 완료**
- [ ] 시스템 페르소나 고도화 ("다정한 약사" + 면책 조항)
- [ ] LLM 출력 안전 검사 (답변 내 위험 키워드 → red_alert)
- [ ] 식약처 e약은요 API 연동
- [ ] Vector DB (ChromaDB/FAISS) RAG 파이프라인
- [ ] 실제 user_id 연동 (카카오 로그인 인증)
- [ ] 오프라벨 설명 로직

### 2.2 Out of Scope

- 프론트엔드 UI/UX (React/Vue 채팅 화면, Red Alert 팝업)
- 리포트 생성 및 시각적 차트 (순응도 분석)
- 음성 입력/출력 기능
- 다국어 지원

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-01 | 위기 키워드(30개) 감지 시 LLM 생략, 1393 안내 즉시 반환 | High | **Done** |
| FR-02 | OpenAI GPT-4o-mini 비동기 호출로 약물 상담 답변 생성 | High | **Done** |
| FR-03 | 모든 대화를 chat_logs 테이블에 저장 (is_flagged 포함) | High | **Done** |
| FR-04 | "다정한 약사" 페르소나 시스템 프롬프트 적용 | High | Pending |
| FR-05 | 모든 답변 끝에 면책 조항 자동 추가 | High | Pending |
| FR-06 | LLM 답변 내 위험 키워드(금기, 위험, 부작용 심각) 감지 → red_alert 시그널 | Medium | Pending |
| FR-07 | 식약처 e약은요 API 연동 — 약물 정보 실시간 조회 | Medium | Pending |
| FR-08 | Vector DB에 의학 가이드라인 임베딩 → RAG 검색 | Medium | Pending |
| FR-09 | 오프라벨 처방 감지 시 "부드러운 납득" 설명 로직 | Medium | Pending |
| FR-10 | 카카오 로그인 user_id와 ChatLog 연동 | Low | Pending |

### 3.2 Non-Functional Requirements

| Category | Criteria | Measurement Method |
|----------|----------|-------------------|
| Performance | 위기 감지 응답 < 500ms (LLM 미호출) | 서버 로그 타임스탬프 |
| Performance | 일반 질문 응답 < 10s (OpenAI 호출 포함) | API 응답 시간 측정 |
| Security | API 키 환경변수 관리 (하드코딩 금지) | 코드 리뷰 |
| Security | 의료법 준수 — 직접 진단/처방 변경 금지 | 시스템 프롬프트 검증 |
| Reliability | OpenAI 장애 시 graceful 에러 메시지 반환 | 에러 핸들링 테스트 |

---

## 4. Success Criteria

### 4.1 Definition of Done

- [x] 위기 키워드 필터 동작 (Direct/Indirect/Substance 각 카테고리 테스트 통과)
- [x] ChatLog DB 저장 검증
- [ ] 시스템 페르소나 프롬프트 적용 확인
- [ ] 면책 조항이 모든 일반 답변에 포함됨
- [ ] LLM 출력 안전 검사 동작 확인
- [ ] 식약처 API 연동 및 약물 정보 프롬프트 주입 확인
- [ ] RAG 검색 결과가 LLM 컨텍스트에 포함됨

### 4.2 Quality Criteria

- [ ] check_safety 단위 테스트 (pytest)
- [ ] /ask 엔드포인트 통합 테스트
- [ ] ruff lint 에러 0건
- [ ] 비동기 호출 검증 (AsyncOpenAI 사용)

---

## 5. Risks and Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| OpenAI API 키 비용 폭증 | High | Medium | Rate Limiting (slowapi), 응답 캐싱 (Redis) |
| 위기 키워드 우회 (은유적 표현) | High | Medium | 키워드 목록 지속 확장, 향후 NLP 분류 모델 검토 |
| 식약처 API 장애/응답 지연 | Medium | Low | 캐싱 + 폴백 (로컬 DB 약물 정보) |
| LLM 할루시네이션 (잘못된 의학 정보) | High | Medium | RAG로 근거 기반 답변 유도, 면책 조항 필수 |
| 의료법 위반 가능성 | High | Low | "진단/처방 불가" 시스템 프롬프트 강제 |

---

## 6. Architecture Considerations

### 6.1 Project Level Selection

| Level | Characteristics | Recommended For | Selected |
|-------|-----------------|-----------------|:--------:|
| **Starter** | Simple structure | Static sites, portfolios | ☐ |
| **Dynamic** | Feature-based modules, BaaS integration | Web apps, SaaS MVPs | ☑ |
| **Enterprise** | Strict layer separation, DI, microservices | High-traffic systems | ☐ |

### 6.2 Key Architectural Decisions

| Decision | Options | Selected | Rationale |
|----------|---------|----------|-----------|
| Framework | FastAPI / Flask / Django | FastAPI | 기존 프로젝트 스택, 비동기 네이티브 |
| ORM | Tortoise / SQLAlchemy / Django ORM | Tortoise ORM | 기존 프로젝트 스택, async 지원 |
| LLM Client | openai / langchain / litellm | openai (AsyncOpenAI) | 직접 제어, 의존성 최소화 |
| Vector DB | ChromaDB / FAISS / Pinecone | ChromaDB | 로컬 실행, Python 네이티브, 임베딩 통합 |
| 약물 정보 | 식약처 API / 자체 DB | 식약처 API + 캐싱 | 실시간 최신 정보, 캐싱으로 성능 보완 |
| Embedding | sentence-transformers / OpenAI Ada | sentence-transformers | 이미 의존성 존재 (pyproject.toml) |
| Testing | pytest / unittest | pytest-asyncio | 기존 프로젝트 설정 |

### 6.3 Clean Architecture Approach

```
Selected Level: Dynamic (Python FastAPI)

Folder Structure:
┌─────────────────────────────────────────────────────┐
│ app/                                                 │
│   apis/v1/         ← API 라우터 (Presentation)      │
│   dtos/            ← 요청/응답 DTO (Pydantic)       │
│   models/          ← DB 모델 (Tortoise ORM)         │
│   services/        ← 비즈니스 로직                   │
│   dependencies/    ← 의존성 주입 (인증 등)           │
│   db/              ← DB 설정 및 마이그레이션          │
├─────────────────────────────────────────────────────┤
│ ai_worker/                                           │
│   tasks/           ← AI 엔진 (chatbot_engine.py)    │
│   core/            ← AI 설정                         │
│   schemas/         ← AI 데이터 스키마                │
├─────────────────────────────────────────────────────┤
│ data/                                                │
│   guidelines/      ← 의학 가이드라인 PDF (RAG 소스)  │
│   embeddings/      ← ChromaDB 벡터 저장소            │
└─────────────────────────────────────────────────────┘
```

---

## 7. Convention Prerequisites

### 7.1 Existing Project Conventions

- [x] `CLAUDE.md` has coding conventions section
- [ ] `docs/01-plan/conventions.md` exists
- [ ] `CONVENTIONS.md` exists at project root
- [x] Ruff configuration (`pyproject.toml [tool.ruff]`)
- [x] pytest-asyncio configuration (`pyproject.toml`)

### 7.2 Conventions to Define/Verify

| Category | Current State | To Define | Priority |
|----------|---------------|-----------|:--------:|
| **Naming** | exists (ruff N rules) | snake_case 함수/변수, PascalCase 클래스 | High |
| **Folder structure** | exists | ai_worker/tasks 하위 모듈 분리 규칙 | High |
| **Import order** | exists (ruff I rules) | stdlib → third-party → local | Medium |
| **Environment variables** | exists | .local.env 키 목록 문서화 | Medium |
| **Error handling** | partial | AI 호출 에러 표준 패턴 정의 | Medium |

### 7.3 Environment Variables Needed

| Variable | Purpose | Scope | Status |
|----------|---------|-------|:------:|
| `OPENAI_API_KEY` | OpenAI API 인증 | Server | ☑ Done |
| `OPENAI_MODEL` | LLM 모델명 | Server | ☑ Done |
| `KFDA_API_KEY` | 식약처 e약은요 API 키 | Server | ☐ Needed |
| `CHROMA_PERSIST_DIR` | ChromaDB 저장 경로 | Server | ☐ Needed |

---

## 8. Implementation Roadmap

### Phase 1: 프롬프트 고도화 (FR-04, FR-05, FR-06)
- 시스템 페르소나 재설계 ("다정한 약사")
- 면책 조항 자동 추가
- LLM 출력 안전 검사

### Phase 2: 식약처 API 연동 (FR-07)
- e약은요 API 클라이언트 구현
- 약물 정보 → LLM 컨텍스트 주입

### Phase 3: RAG 파이프라인 (FR-08)
- 의학 가이드라인 PDF 임베딩
- ChromaDB 벡터 검색
- 검색 결과 → LLM 프롬프트 주입

### Phase 4: 통합 및 인증 연동 (FR-09, FR-10)
- 오프라벨 설명 로직
- 카카오 user_id 연동

---

## 9. Next Steps

1. [ ] Design 문서 작성 (`chat-core.design.md`)
2. [ ] 팀 리뷰 및 승인
3. [ ] Phase 1 구현 시작

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-03-09 | Initial draft | Team AI-HealthCare |
