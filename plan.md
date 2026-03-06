# 도닥톡 (DodakTalk) 개발 계획서

> **검토 기준**: AGENTS.md (TDD, Tidy First) · SYSTEM_DESIGN.md (Python 3.13+, 빌트인 타입, OOP, 실용적 레이어드 아키텍처) 1순위 준수

---

## 1. 프로젝트 개요 및 목표

### 서비스 소개

**도닥톡(DodakTalk)** 은 정신건강 자기관리를 돕는 모바일 반응형 웹 서비스입니다.
사용자가 일상의 감정과 생각을 일기로 기록하고, AI 챗봇 캐릭터와 대화하며 심리적 안정을 찾을 수 있도록 돕습니다.

### 핵심 목표

| 목표 | 설명 |
|------|------|
| 온보딩 경험 개선 | 회원가입 직후 챗봇 캐릭터 선택 화면으로 자연스럽게 연결 |
| 감정 기록 | 일기 작성(직접입력 / OCR / AI 챗봇 요약) 3가지 방식 지원 |
| 복약 관리 | 처방 정보(Master)와 일일 복약 기록(Log) 분리 관리 |
| 기분 추적 | 날짜별 기분 점수 기록 및 달력 시각화 |
| 진료 일정 | 병원 예약 일정 등록 및 알림 |
| AI 리포트 | 주간/월간 일기 분석 리포트 생성 |

### 기술 스택

| 구분 | 기술 |
|------|------|
| Backend | FastAPI, Tortoise ORM, MySQL, Redis |
| Frontend | React + TypeScript + Vite |
| AI Worker | Python (별도 프로세스) |
| Infra | Docker Compose, Nginx, AWS EC2 |

### 현재 구현 완료 상태

- [x] 카카오 소셜 로그인 / 회원가입 (휴대폰 인증 포함)
- [x] JWT 발급 및 갱신 (Access Token + HttpOnly Refresh Token Cookie)
- [x] 사용자 정보 조회 및 수정 (`GET/PATCH /api/v1/users/me`)
- [x] 일기 CRUD + OCR + AI 챗봇 요약 저장 (인메모리 임시 구현)
- [x] 리포트 생성/조회/수정 (인메모리 임시 구현)
- [x] 기분(Mood), 진료 일정(Appointment) 라우터 뼈대 (인메모리 임시 구현)
- [ ] **챗봇 캐릭터 선택 (온보딩) — 미구현, 다음 우선 구현 대상**
- [ ] 복약 관리 도메인 — 미구현
- [ ] 인메모리 → 실제 DB 연동 전환 (Mood, Appointment, Diary)
- [ ] 기존 테스트 코드 정비 (하위호환성 붕괴 상태 — 섹션 6 참고)

---

## 2. 데이터베이스 스키마 설계 (DB Modeling)

### 2-1. 전체 테이블 목록

| 테이블명 | 도메인 | 상태 |
|----------|--------|------|
| `users` | 회원 | 구현 완료 (컬럼 추가 필요) |
| `chatbot_characters` | 챗봇 캐릭터 | **신규 설계 필요** |
| `user_characters` | 유저-캐릭터 선택 | **신규 설계 필요** |
| `diaries` | 일기 | 구현 완료 |
| `reports` | AI 리포트 | 구현 완료 |
| `moods` | 기분 기록 | 구현 완료 (DB 연동 필요) |
| `appointments` | 진료 일정 | 구현 완료 (DB 연동 필요) |
| `medication_prescriptions` | 복약 처방 (Master) | **신규 설계 필요** |
| `medication_logs` | 일일 복약 기록 (Log) | **신규 설계 필요** |

---

### 2-2. 테이블 상세 설계

#### `users` (기존 — 컬럼 추가 필요)

```sql
users
├── user_id          BIGINT PK AUTO_INCREMENT
├── nickname         VARCHAR(10)
├── email            VARCHAR(40) NULL
├── gender           ENUM('MALE','FEMALE','UNKNOWN')
├── birthday         DATE NULL
├── phone_number     VARCHAR(11) UNIQUE
├── kakao_id         VARCHAR(255) UNIQUE INDEX
├── is_active        BOOLEAN DEFAULT TRUE
├── is_admin         BOOLEAN DEFAULT FALSE
├── terms_agreed     BOOLEAN DEFAULT FALSE
├── privacy_agreed   BOOLEAN DEFAULT FALSE
├── sensitive_agreed BOOLEAN DEFAULT FALSE
├── marketing_agreed BOOLEAN DEFAULT FALSE
├── onboarding_completed  BOOLEAN DEFAULT FALSE   ← 신규 추가
├── last_login       DATETIME NULL
├── created_at       DATETIME AUTO
└── updated_at       DATETIME AUTO
```

> `onboarding_completed`: 캐릭터 선택 완료 여부. 프론트엔드가 이 값으로 온보딩 리다이렉트를 결정합니다.
> `GET /users/me` 응답 DTO(`UserInfoResponse`)에도 이 필드를 추가해야 프론트엔드가 읽을 수 있습니다.

---

#### `chatbot_characters` (신규)

```sql
chatbot_characters
├── character_id   BIGINT PK AUTO_INCREMENT
├── name           VARCHAR(50)
├── description    TEXT
├── image_url      VARCHAR(500)
├── personality    VARCHAR(100) NULL
├── is_active      BOOLEAN DEFAULT TRUE
├── created_at     DATETIME AUTO
└── updated_at     DATETIME AUTO
```

---

#### `user_characters` (신규)

```sql
user_characters
├── id             BIGINT PK AUTO_INCREMENT
├── user_id        BIGINT FK → users.user_id  UNIQUE
├── character_id   BIGINT FK → chatbot_characters.character_id
├── selected_at    DATETIME AUTO_NOW_ADD
└── updated_at     DATETIME AUTO
```

> `user_id UNIQUE` 제약으로 연타 중복 선택을 DB 레벨에서 차단합니다.
> `users` 테이블에 `character_id`를 직접 넣지 않고 분리한 이유: 향후 캐릭터 변경 이력 추적 시 이 테이블에만 컬럼을 추가하면 됩니다.

---

#### `diaries` (기존)

```sql
diaries
├── diary_id      BIGINT PK AUTO_INCREMENT
├── user_id       BIGINT FK → users.user_id
├── diary_date    DATE
├── title         VARCHAR(255) NULL
├── content       TEXT
├── write_method  VARCHAR(20) NULL   -- 'direct' | 'ocr' | 'chatbot'
├── created_at    DATETIME AUTO
├── updated_at    DATETIME AUTO
└── deleted_at    DATETIME NULL      -- Soft Delete
```

---

#### `moods` (기존 — DB 연동 필요)

```sql
moods
├── mood_id     BIGINT PK AUTO_INCREMENT
├── user_id     BIGINT FK → users.user_id
├── mood_score  INT NULL    -- 1~5 (서비스 레이어에서 범위 검증)
├── note        TEXT NULL
├── created_at  DATETIME AUTO
└── updated_at  DATETIME AUTO
```

---

#### `appointments` (기존 — DB 연동 필요)

```sql
appointments
├── appointment_id   BIGINT PK AUTO_INCREMENT
├── user_id          BIGINT FK → users.user_id
├── appointment_date DATE NULL
├── hospital_name    VARCHAR(255) NULL
├── notes            TEXT NULL
├── created_at       DATETIME AUTO
└── updated_at       DATETIME AUTO
```

---

#### `medication_prescriptions` (신규 — Master)

```sql
medication_prescriptions
├── prescription_id  BIGINT PK AUTO_INCREMENT
├── user_id          BIGINT FK → users.user_id
├── drug_name        VARCHAR(100)
├── dosage           VARCHAR(50)
├── frequency        VARCHAR(50)
├── start_date       DATE
├── end_date         DATE NULL        -- NULL = 장기 복용
├── hospital_name    VARCHAR(255) NULL
├── notes            TEXT NULL
├── is_active        BOOLEAN DEFAULT TRUE
├── created_at       DATETIME AUTO
└── updated_at       DATETIME AUTO
```

---

#### `medication_logs` (신규 — Log)

```sql
medication_logs
├── log_id           BIGINT PK AUTO_INCREMENT
├── prescription_id  BIGINT FK → medication_prescriptions.prescription_id
├── user_id          BIGINT FK → users.user_id   -- 조회 성능을 위한 역정규화
├── log_date         DATE
├── taken_at         DATETIME NULL
├── is_taken         BOOLEAN DEFAULT FALSE
├── created_at       DATETIME AUTO
└── updated_at       DATETIME AUTO
UNIQUE (prescription_id, log_date)
```

> `user_id` 역정규화: "오늘 내 복약 목록" 조회 시 JOIN 없이 `user_id`로 바로 필터링 가능.
> `UNIQUE (prescription_id, log_date)`: 버튼 연타 중복 방지를 DB 레벨에서 보장.

---

### 2-3. Master / Log 분리 전략

```
medication_prescriptions (Master)
    "어떤 약을, 언제부터 언제까지, 하루 몇 번 먹어야 하는가"
    → 처방 정보. 한 번 등록 후 재사용.

medication_logs (Log)
    "오늘 실제로 먹었는가?"
    → 매일 새 행 생성. 날짜별 복약 이행률 집계에 사용.
```

분리하지 않으면 30일치 이력이 JSON 컬럼에 쌓이거나 컬럼이 폭발합니다.
처방이 변경되어도 기존 Log 데이터는 보존됩니다.

---

### 2-4. 테이블 관계 요약

```
users (1)
  ├── (N) diaries
  ├── (N) moods
  ├── (N) appointments
  ├── (N) reports
  ├── (N) medication_prescriptions
  │     └── (N) medication_logs
  └── (1) user_characters → (N:1) chatbot_characters
```


---

## 3. API 엔드포인트 명세 (API Specification)

> 인증이 필요한 모든 API: `Authorization: Bearer <access_token>` 헤더 필수.
> Base URL: `/api/v1`

---

### 3-1. 인증 (Auth) — 구현 완료

| Method | URI | 설명 | 인증 |
|--------|-----|------|------|
| `POST` | `/auth/kakao` | 카카오 인가코드로 로그인/신규유저 판별 | ❌ |
| `POST` | `/auth/kakao/signup` | 카카오 회원가입 완료 | Temp Token |
| `GET` | `/auth/token/refresh` | Access Token 갱신 (Refresh Token Cookie) | ❌ |
| `POST` | `/auth/phone/send-code` | 휴대폰 인증번호 발송 | ❌ |
| `POST` | `/auth/phone/verify-code` | 휴대폰 인증번호 검증 | ❌ |

---

### 3-2. 사용자 (Users) — 구현 완료

| Method | URI | 설명 | 인증 |
|--------|-----|------|------|
| `GET` | `/users/me` | 내 정보 조회 (`onboarding_completed` 포함) | ✅ |
| `PATCH` | `/users/me` | 내 정보 수정 | ✅ |

---

### 3-3. 온보딩 / 챗봇 캐릭터 — **미구현 (최우선)**

| Method | URI | 설명 | 인증 |
|--------|-----|------|------|
| `GET` | `/characters` | 선택 가능한 캐릭터 목록 조회 | ✅ |
| `POST` | `/characters/me` | 캐릭터 최초 선택 (온보딩 완료 처리) | ✅ |
| `GET` | `/characters/me` | 내가 선택한 캐릭터 조회 | ✅ |
| `PATCH` | `/characters/me` | 캐릭터 변경 | ✅ |

> **수정 이유**: 이전 초안의 `POST /characters/select`는 동사를 URI에 포함한 RESTful 위반입니다.
> 리소스(`/characters/me`)에 대한 행위를 HTTP 메서드(POST/PATCH)로 표현하는 것이 올바릅니다.

**Request / Response 예시**

```
GET /api/v1/characters
Response 200:
{
  "characters": [
    {
      "character_id": 1,
      "name": "도닥이",
      "description": "따뜻하게 공감해주는 친구",
      "image_url": "/static/characters/dodaki.png",
      "personality": "따뜻함"
    }
  ]
}

POST /api/v1/characters/me
Request:  { "character_id": 1 }
Response 201:
{
  "character_id": 1,
  "name": "도닥이",
  "selected_at": "2025-07-10T10:00:00+09:00"
}
```

---

### 3-4. 일기 (Diary) — 인메모리 구현 완료, DB 연동 필요

| Method | URI | 설명 | 인증 |
|--------|-----|------|------|
| `GET` | `/diary/calendar?year=&month=` | 월별 일기 달력 조회 | ✅ |
| `GET` | `/diary/{entry_date}` | 날짜별 일기 조회 | ✅ |
| `POST` | `/diary/{entry_date}/text` | 직접 입력 일기 저장 | ✅ |
| `POST` | `/diary/{entry_date}/photo/ocr` | OCR 이미지 업로드 | ✅ |
| `POST` | `/diary/{entry_date}/photo/ocr/confirm` | OCR 결과 확정 저장 | ✅ |
| `GET` | `/diary/{entry_date}/chatbot/summary` | AI 챗봇 요약 조회 | ✅ |
| `POST` | `/diary/{entry_date}/chatbot/summary/save` | AI 챗봇 요약 저장 | ✅ |
| `PUT` | `/diary/{entry_date}/entry/{entry_id}` | 일기 수정 | ✅ |
| `DELETE` | `/diary/{entry_date}/entry/{entry_id}` | 일기 삭제 | ✅ |
| `GET` | `/diary/report` | 리포트 목록 조회 | ✅ |
| `POST` | `/diary/report` | 리포트 생성 | ✅ |
| `GET` | `/diary/report/{report_id}` | 리포트 상세 조회 | ✅ |
| `PUT` | `/diary/report/{report_id}` | 리포트 수정 | ✅ |

---

### 3-5. 기분 (Mood) — DB 연동 필요

| Method | URI | 설명 | 인증 |
|--------|-----|------|------|
| `POST` | `/moods` | 기분 기록 저장 | ✅ |
| `GET` | `/moods?date=` | 날짜별 기분 조회 | ✅ |
| `GET` | `/moods/calendar?year=&month=` | 월별 기분 달력 조회 | ✅ |
| `PATCH` | `/moods/{mood_id}` | 기분 수정 | ✅ |

---

### 3-6. 진료 일정 (Appointments) — DB 연동 필요

| Method | URI | 설명 | 인증 |
|--------|-----|------|------|
| `POST` | `/appointments` | 진료 일정 등록 | ✅ |
| `GET` | `/appointments` | 전체 일정 조회 | ✅ |
| `GET` | `/appointments/by-date?date=` | 날짜별 일정 조회 | ✅ |
| `PATCH` | `/appointments/{appointment_id}` | 일정 수정 | ✅ |
| `DELETE` | `/appointments/{appointment_id}` | 일정 삭제 | ✅ |

---

### 3-7. 복약 관리 (Medications) — 미구현

| Method | URI | 설명 | 인증 |
|--------|-----|------|------|
| `POST` | `/medications` | 처방 등록 (Master) | ✅ |
| `GET` | `/medications` | 내 처방 목록 조회 | ✅ |
| `PATCH` | `/medications/{prescription_id}` | 처방 수정 | ✅ |
| `DELETE` | `/medications/{prescription_id}` | 처방 비활성화 | ✅ |
| `POST` | `/medications/{prescription_id}/logs` | 복약 기록 (Log) | ✅ |
| `GET` | `/medications/logs?date=` | 날짜별 복약 기록 조회 | ✅ |
| `PATCH` | `/medications/logs/{log_id}` | 복약 기록 수정 | ✅ |

---

### 3-8. 메인 화면 통합 조회 API (BFF 패턴) — 미구현

모바일에서 메인 화면 진입 시 여러 도메인 데이터를 한 번에 반환합니다.
개별 API를 4~5번 호출하는 대신 단일 요청으로 해결합니다.

| Method | URI | 설명 | 인증 |
|--------|-----|------|------|
| `GET` | `/home/summary?date=` | 메인 화면 통합 데이터 조회 | ✅ |

```
GET /api/v1/home/summary?date=2025-07-10
Response 200:
{
  "user": {
    "nickname": "홍길동",
    "character": { "name": "도닥이", "image_url": "..." }
  },
  "today_mood": { "mood_score": 4, "note": "오늘은 괜찮았어요" },
  "today_diary": { "diary_id": 12, "title": "오늘의 일기", "diary_date": "2025-07-10" },
  "upcoming_appointment": { "appointment_date": "2025-07-15", "hospital_name": "서울정신건강의학과" },
  "today_medications": [
    { "log_id": 5, "drug_name": "세로토닌정", "is_taken": false }
  ]
}
```

> 구현 시 `app/apis/v1/home_routers.py`를 신규 생성하고, 각 서비스를 `Depends()`로 주입받아 `asyncio.gather()`로 병렬 조회합니다.


---

## 4. 개발 마일스톤 및 태스크 리스트

> AGENTS.md 원칙: **Red → Green → Refactor** 순서 엄수. 테스트 먼저 작성 후 구현.
> 실행 명령: `uv run pytest app/tests/`

---

### Phase 0: 기존 테스트 코드 정비 (즉시 처리 필요)

현재 테스트 전체가 실행 불가 상태입니다. 신규 기능 개발 전에 반드시 선행해야 합니다.

- [x] **[Fix]** `pyproject.toml` dev 그룹에 `pytest` 패키지 추가 (현재 누락)
- [x] **[Fix]** `app/tests/conftest.py`의 `from typing import Any` → 빌트인 `dict` 타입으로 교체, SQLite 인메모리 DB로 전환
- [x] **[Fix]** `test_signup_api.py`, `test_login_api.py`, `test_token_api.py`, `test_user_me_apis.py` — 카카오 OAuth 플로우 기반으로 전면 재작성, 외부 호출 mock 처리
- [x] **[Fix]** `test_diary_report_apis.py` — `"Bearer test-token"` 하드코딩 제거, 실제 JWT 토큰 + DB 유저 픽스처로 교체
- [x] **[Fix]** `pyproject.toml`의 `[tool.aerich]` — `tortoise_orm` 경로 수정 (`app.db.databases.TORTOISE_ORM`)

---

### Phase 1: 온보딩 — 챗봇 캐릭터 선택 (최우선)

- [x] **[Test]** `app/tests/character_apis/test_character_apis.py` 작성 (Red)
  - 캐릭터 목록 조회 성공
  - 캐릭터 선택 성공 (201)
  - 캐릭터 중복 선택 시 409
  - 미인증 요청 시 401
- [x] **[DB]** `app/models/character.py` — `UserCharacter` Tortoise 모델 작성 (캐릭터는 코드 상수 관리)
- [x] **[DB]** `app/models/users.py` — `onboarding_completed` 필드 추가
- [x] **[DB]** `app/models/__init__.py` — `UserCharacter` 등록
- [x] **[DTO]** `app/dtos/character_dto.py` — 캐릭터 목록/선택 Request/Response DTO 작성
- [x] **[DTO]** `app/dtos/users.py` — `UserInfoResponse`에 `onboarding_completed` 필드 추가, nickname→name 매핑 수정
- [x] **[Service]** `app/services/character_service.py` — `CharacterService` 클래스 작성
- [x] **[API]** `app/apis/v1/character_routers.py` — 4개 엔드포인트 구현 (Green)
- [x] **[API]** `app/apis/v1/__init__.py` — `character_router` 등록
- [x] **[FE]** `CharacterSelectPage.tsx` 구현 — plan.md Phase 1-FE 명세 적용
- [x] **[FE]** `SignupPage.tsx` — 회원가입 완료 후 `/character-select`로 리다이렉트
- [x] **[FE]** `KakaoCallbackPage.tsx` — 로그인 성공 후 `onboarding_completed` 확인 → 미완료 시 `/character-select`로 리다이렉트
- [x] **[FE]** `App.tsx` — `/character-select` 라우트 추가
- [x] **[FE]** `authStore.ts` — `selectedCharacter` 상태 추가

---

### Phase 1-FE: CharacterSelectPage UI/UX 상세 명세

#### 1. 레이아웃 구조

```
<div class="character-select-page">   ← 전체 화면, column flex, bg: var(--bg)
  <header class="cs-header">          ← 상단 텍스트 영역
  <main class="cs-grid">              ← 2×2 캐릭터 그리드
  <footer class="cs-footer">          ← 하단 고정 확인 버튼
</div>
```

모바일 우선 — 카드 컨테이너 없이 전체 화면 사용. `padding: 0 20px`.

---

#### 2. Header (`cs-header`)

```css
.cs-header {
  padding: 48px 0 32px;
  text-align: center;
}
```

| 요소 | 스타일 |
|------|--------|
| 메인 카피 | `font-size: 20px`, `font-weight: 700`, `color: var(--text)`, `line-height: 1.5` |
| 서브 카피 | `font-size: 14px`, `color: var(--placeholder)`, `margin-top: 8px`, `line-height: 1.6` |
| 현재 선택 배지 | `margin-top: 16px`, pill shape, `background: #f0f4ee`, `color: var(--btn-bg)`, `font-size: 13px`, `font-weight: 600`, `padding: 6px 14px`, `border-radius: 20px` |

텍스트:
- 메인: `"오늘부터 마음을 나눌\n다정한 친구를 골라주세요"`
- 서브: `"하루를 함께 기록하고 기분을\n다정하게 들어줄 단 한 명의 친구"`
- 배지: `"현재 함께하는 친구: {selectedName}"` (선택된 캐릭터가 있을 때만 렌더)

---

#### 3. Grid (`cs-grid`)

```css
.cs-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  padding-bottom: 120px; /* footer 높이 확보 */
}
```

**캐릭터 카드 (`.cs-card`)**

```css
.cs-card {
  background: #fff;
  border-radius: 20px;
  border: 2.5px solid transparent;
  padding: 24px 16px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s, transform 0.15s;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.cs-card:hover {
  border-color: rgba(153,169,136,0.4);
  box-shadow: 0 4px 16px rgba(153,169,136,0.2);
  transform: translateY(-2px);
}
.cs-card.selected {
  border-color: var(--btn-bg);
  box-shadow: 0 4px 20px rgba(153,169,136,0.3);
}
```

**카드 내부 구성:**

```
[이미지]   width: 96px, height: 96px, object-fit: contain  (removebg 버전 사용)
[이름]     font-size: 16px, font-weight: 700, color: var(--text)
[설명]     font-size: 12px, color: var(--placeholder), text-align: center, line-height: 1.5
[체크]     선택 시만 표시 — "✓ 선택됨", color: var(--btn-bg), font-size: 13px, font-weight: 600
```

**캐릭터 데이터 (컴포넌트 내 상수):**

```typescript
const CHARACTERS = [
  { id: 1, name: '참깨', description: '걱정을 먼저 알아채고\n한없이 보살펴주는 친구', image: chamkkaeImg },
  { id: 2, name: '들깨', description: '하나부터 열까지\n차근차근 알려주는 친구',  image: deulkkaeImg },
  { id: 3, name: '흑깨', description: '밝고 긍정적이면서\n웃음을 건네는 친구',     image: heukkkaeImg },
  { id: 4, name: '통깨', description: '귀엽고 공감 리액션으로\n기분을 밝혀주는 친구', image: tongkkaeImg },
]
// 이미지: src/assets/images/chatbots/{key}-removebg.png
```

---

#### 4. Footer (`cs-footer`)

```css
.cs-footer {
  position: fixed;
  bottom: 0; left: 0; right: 0;
  padding: 16px 20px 32px; /* iOS safe area 고려 */
  background: linear-gradient(to top, #F5F5F5 80%, transparent);
}
```

**확인 버튼:**

```css
/* 공통 */
width: 100%; max-width: 420px; margin: 0 auto; display: block;
height: 52px; border-radius: 14px;
font-size: 17px; font-weight: 700;
background: var(--btn-bg); color: var(--btn-text);

/* 미선택 시 */
opacity: 0.45; cursor: not-allowed;
```

버튼 텍스트: 선택 전 `"친구를 선택해주세요"` → 선택 후 `"{name}와 함께하기"`

---

#### 5. 상태 관리 & API 연동

```typescript
// 초기값: GET /characters/me 응답의 character_id (없으면 null)
const [selectedId, setSelectedId] = useState<number | null>(initialId)
const [loading, setLoading] = useState(false)
const [error, setError] = useState('')
```

- 카드 클릭 → `selectedId` 즉시 업데이트 (API 호출 없음)
- 확인 버튼 클릭:
  - 최초 선택: `POST /api/v1/characters/me`
  - 변경: `PATCH /api/v1/characters/me`
  - 성공 → `authStore.setSelectedCharacter(...)` → `navigate('/main', { replace: true })`
  - 실패 → 버튼 하단 인라인 에러 표시

---

#### 6. 진입 애니메이션 (CSS only, JS 라이브러리 불필요)

```css
@keyframes cardIn {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: translateY(0); }
}
.cs-card { animation: cardIn 0.35s ease both; }
.cs-card:nth-child(1) { animation-delay: 0.05s; }
.cs-card:nth-child(2) { animation-delay: 0.10s; }
.cs-card:nth-child(3) { animation-delay: 0.15s; }
.cs-card:nth-child(4) { animation-delay: 0.20s; }
```

---

#### 7. 접근성

- 각 카드: `role="radio"`, `aria-checked={selectedId === id}`, `tabIndex={0}`, `onKeyDown` Enter/Space 처리
- 확인 버튼: `aria-disabled={!selectedId}`
- 이미지: `alt="{name} 캐릭터"`

---

### Phase 2: 인메모리 → 실제 DB 연동 전환

- [x] **[Test]** Mood, Appointment 서비스 테스트 작성 (실제 DB 기반)
- [x] **[Mood]** `MoodService` 클래스 작성 + Tortoise ORM 연동
- [x] **[Mood]** `mood_routers.py` 리팩터 — `dict` 타입 제거, DTO + 인증 적용
- [x] **[Appointment]** `AppointmentService` 클래스 작성 + Tortoise ORM 연동
- [x] **[Appointment]** `appointment_routers.py` 리팩터 — 인증 적용, PATCH/DELETE 추가
- [ ] **[Diary]** `DiaryReportService` — `fake_ocr_pending`, `fake_chatbot_pending` 인메모리 의존성 제거, DB 또는 Redis 기반으로 교체

---

### Phase 3: 복약 관리 도메인 신규 구현

- [ ] **[Test]** 복약 처방 CRUD 테스트 작성 (Red)
- [ ] **[Test]** 복약 기록 중복 방지 테스트 작성 (Red)
- [ ] **[DB]** `app/models/medication.py` — `MedicationPrescription`, `MedicationLog` 모델 작성
- [ ] **[DB]** `MedicationLog.Meta.unique_together = (("prescription_id", "log_date"),)` 설정
- [ ] **[Service]** `MedicationService` 클래스 작성
- [ ] **[API]** `app/apis/v1/medication_routers.py` — 7개 엔드포인트 구현 (Green)

---

### Phase 4: 메인 화면 BFF API 및 고도화

- [ ] **[Test]** BFF API 통합 테스트 작성
- [ ] **[API]** `GET /api/v1/home/summary` — `asyncio.gather()` 병렬 조회 구현
- [ ] **[FE]** `MainPage.tsx` 실제 데이터 연동
- [ ] **[AI]** AI Worker와 챗봇 요약 기능 실제 연동
- [ ] **[Infra]** Aerich 마이그레이션 파일 정리 및 운영 DB 적용


---

## 5. 신입 개발자를 위한 기술적 주의사항 (Risk & Edge Cases)

---

### 5-1. N+1 쿼리 문제 방지

Tortoise ORM에서 관계 필드를 루프 안에서 접근하면 쿼리가 N번 추가 발생합니다.

```python
# 위험 — N+1 발생
diaries = await Diary.filter(user_id=user_id)
for diary in diaries:
    user = await diary.user  # 루프마다 SELECT 1번씩 추가!

# 안전 — prefetch_related (쿼리 2번)
diaries = await Diary.filter(user_id=user_id).prefetch_related("user")

# 단일 FK JOIN (쿼리 1번)
log = await MedicationLog.get(log_id=log_id).select_related("prescription")
```

BFF API에서는 `asyncio.gather()`로 병렬 조회하되, 각 쿼리 내부의 N+1도 함께 확인하세요.

```python
import asyncio

mood, diary, appointment = await asyncio.gather(
    Mood.filter(user_id=user_id, created_at__date=today).first(),
    Diary.filter(user_id=user_id, diary_date=today, deleted_at__isnull=True).first(),
    Appointment.filter(user_id=user_id, appointment_date__gte=today).first(),
)
```

---

### 5-2. 타임존(Timezone) 처리 및 자정 기준 날짜 계산

`app/db/databases.py`에 `"timezone": "Asia/Seoul"`이 설정되어 있습니다.
서버가 UTC로 실행되면 `date.today()`는 KST와 최대 9시간 차이가 납니다.

```python
# 위험 — UTC 기준 날짜 반환
from datetime import date
today = date.today()

# 올바른 방법 — KST 기준
from datetime import date, datetime
import zoneinfo

KST = zoneinfo.ZoneInfo("Asia/Seoul")

def get_today_kst() -> date:
    return datetime.now(tz=KST).date()
```

> `zoneinfo`는 Python 3.9+ 표준 라이브러리입니다. 이 프로젝트는 Python 3.13+이므로 별도 설치 불필요.

`diary_date`는 서버가 자동 설정하지 말고, 클라이언트가 명시적으로 전달한 날짜를 그대로 저장하세요.
사용자가 자정 이후에 "어제 일기"를 쓸 수 있기 때문입니다.

---

### 5-3. 동시성 문제 — 버튼 연타 시 중복 데이터 생성 방지

**복약 기록**: `UNIQUE (prescription_id, log_date)` DB 제약이 가장 확실합니다.

```python
from tortoise.exceptions import IntegrityError

try:
    log = await MedicationLog.create(...)
except IntegrityError:
    raise HTTPException(status_code=409, detail="이미 기록된 복약 정보입니다.")
```

또는 `get_or_create()` 패턴:

```python
log, created = await MedicationLog.get_or_create(
    prescription_id=prescription_id,
    log_date=get_today_kst(),
    defaults={"is_taken": True, "taken_at": datetime.now(tz=KST)},
)
if not created:
    raise HTTPException(status_code=409, detail="이미 기록된 복약 정보입니다.")
```

**캐릭터 선택**: `user_characters.user_id UNIQUE` 제약으로 동일하게 처리합니다.

---

### 5-4. 기타 실무 팁

**Soft Delete 필터 누락 방지**: `diaries`의 모든 조회 쿼리에 `deleted_at__isnull=True`를 반드시 포함하세요.

```python
active_diaries = Diary.filter(user_id=user_id, deleted_at__isnull=True)
```

**Aerich 마이그레이션 순서**:

```bash
uv run aerich migrate --name "add_character_tables"
uv run aerich upgrade
```

마이그레이션 파일을 직접 수정하지 마세요. 문제가 생기면 `downgrade` 후 재생성합니다.

**DTO와 모델 분리**: Tortoise 모델 객체를 API 응답에 직접 반환하지 마세요.
반드시 Pydantic DTO로 변환 후 반환해야 민감 정보 노출을 막을 수 있습니다.
기존 `UserInfoResponse.model_validate(user)` 패턴을 참고하세요.

**`typing` 모듈 사용 금지 (SYSTEM_DESIGN.md)**: `List`, `Dict`, `Optional`, `Any` 대신 빌트인 타입을 사용하세요.

```python
# 금지
from typing import List, Optional
def get_diaries(user_id: int) -> List[dict]: ...

# 올바름
def get_diaries(user_id: int) -> list[dict]: ...
```

---

## 6. 현재 코드베이스 검토 결과 — 즉시 수정 필요 항목

> 이 섹션은 plan.md 작성 시점의 코드 검토 결과입니다. Phase 0 태스크와 연동됩니다.

### 6-1. 테스트 하위호환성 붕괴 (Critical)

| 파일 | 문제 | 영향 |
|------|------|------|
| `test_signup_api.py` | `/api/v1/auth/signup` 엔드포인트 없음 (카카오 OAuth로 대체됨) | 테스트 실행 시 404 |
| `test_login_api.py` | `/api/v1/auth/login` 엔드포인트 없음 | 테스트 실행 시 404 |
| `test_token_api.py` | 위와 동일한 signup/login 의존 | 테스트 실행 시 실패 |
| `test_user_me_apis.py` | 위와 동일한 signup/login 의존 | 테스트 실행 시 실패 |
| `test_diary_report_apis.py` | `"Bearer test-token"` 하드코딩으로 JWT 검증 우회 | 실제 인증 로직 미검증 |

**수정 방향**: 카카오 OAuth 외부 호출은 `unittest.mock.patch`로 모킹하고, 테스트용 유저를 DB에 직접 생성하는 픽스처를 `conftest.py`에 추가합니다.

### 6-2. SYSTEM_DESIGN.md 위반

| 파일 | 위반 내용 |
|------|----------|
| `app/tests/conftest.py` | `from typing import Any` 사용 — `typing` 모듈 사용 금지 규칙 위반 |

수정: `get_test_db_config()` 반환 타입을 `dict[str, Any]` 대신 구체 타입으로 명시하거나, `Any` 없이 `dict` 로 선언합니다.

### 6-3. 설정 불일치

| 항목 | 현재 값 | 올바른 값 |
|------|---------|----------|
| `pyproject.toml` `[tool.aerich] tortoise_orm` | `"app.core.db.TORTOISE_ORM"` | `"app.db.databases.TORTOISE_ORM"` |
| `pyproject.toml` dev 그룹 | `pytest` 패키지 누락 | `pytest>=8.x` 추가 필요 |

### 6-4. 테스트 과잉/중복 여부 검토

현재 테스트는 실행 자체가 불가하므로 과잉/중복 판단보다 **복구**가 우선입니다.
복구 후 아래 기준으로 정리하세요.

- `test_signup_success` / `test_login_success` 처럼 **동일한 플로우를 반복 셋업**하는 테스트는 `conftest.py` 픽스처로 통합합니다.
- "이메일 형식이 잘못됐을 때 422 반환" 같이 **Pydantic이 자동 처리하는 검증**은 별도 테스트가 불필요합니다. FastAPI + Pydantic의 동작은 이미 검증된 라이브러리 동작이므로 자명합니다.
- 각 도메인당 테스트해야 할 핵심 케이스: **성공 경로 1개 + 인증 실패 1개 + 핵심 비즈니스 규칙 위반 1~2개**로 최소화합니다.

