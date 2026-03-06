# 카카오 로그인 무한 루프 — 분석 및 수정 계획

> **AGENTS.md 준수**: 이 파일이 작업 지시서입니다. "go" 명령 시 아래 미완료 항목을 순서대로 실행합니다.
> **SYSTEM_DESIGN.md 준수**: 모든 Python 코드는 built-in 타입만 사용하고, `typing` 모듈 import 금지.
> TDD 사이클(Red → Green → Refactor)을 엄격히 따릅니다.

---

## 1️⃣ 문제 현상 요약

- 로그인 페이지(`/`)에서 "카카오로 시작하기" 클릭
- 카카오 OAuth 인증 후 `/auth/kakao/callback?code=...` 리다이렉트
- `KakaoCallbackPage`가 `POST /api/v1/auth/kakao` 호출
- 기존 회원·신규 회원 모두 `/main` 또는 `/signup` 대신 `/`(로그인 페이지)로 재이동
- 결과: 로그인 페이지 → 카카오 인증 → 콜백 → 로그인 페이지 무한 반복

---

## 2️⃣ 정상 카카오 로그인 흐름

```
[사용자] 로그인 버튼 클릭
    ↓
[Frontend] https://kauth.kakao.com/oauth/authorize?response_type=code
           &client_id={VITE_KAKAO_REST_API_KEY}
           &redirect_uri=http://localhost:5173/auth/kakao/callback
    ↓
[카카오] 인가 코드 발급 → http://localhost:5173/auth/kakao/callback?code=...
    ↓
[KakaoCallbackPage] URL에서 code 추출
    ↓
[Frontend → Backend] POST /api/v1/auth/kakao { code }
    ↓
[AuthService.process_kakao_login]
    1. 인가 코드 → 카카오 Access Token 교환
    2. 카카오 유저 정보 조회 (kakao_id, nickname)
    3. DB에서 kakao_id로 기존 회원 여부 확인
    ↓
분기 A (기존 회원)
    응답: { is_new_user: false, access_token, refresh_token }
    Set-Cookie: refresh_token (HttpOnly)
    → Frontend: accessToken → Zustand store → navigate('/main')

분기 B (신규 회원)
    응답: { is_new_user: true, temp_token, kakao_info }
    → Frontend: temp_token → sessionStorage → navigate('/signup')
    → 회원가입 완료 후 POST /api/v1/auth/kakao/signup
    → accessToken → Zustand store → navigate('/main')
```

---

## 3️⃣ 원인 가설 목록

### Frontend

| # | 가설 | 근거 | 가능성 |
|---|------|------|--------|
| F-1 | `KakaoCallbackPage` `.catch()` 블록이 모든 에러에서 `navigate('/')` 호출 | 백엔드 4xx/5xx 시 catch → `/` 이동 | 높음 |
| F-2 | `data.access_token` 또는 `data.temp_token`이 null → 분기 조건 모두 false → navigate 미호출 후 이전 상태 유지 | 응답 파싱 실패 또는 백엔드 필드 누락 | 중간 |
| F-3 | `authApi.ts` `request()` 내부에서 401 + `withAuth=true` 조건 시 `window.location.href = '/'` 강제 이동 | `kakaoLogin()`은 `withAuth=false`이므로 이 경로는 타지 않음 | 낮음 |

### Backend

| # | 가설 | 근거 | 가능성 |
|---|------|------|--------|
| B-1 | `KAKAO_REDIRECT_URI`가 카카오 콘솔 등록값과 불일치 → 토큰 발급 실패 (`KOE006`) | `envs/.local.env`의 URI가 콘솔 미등록 시 즉시 실패 | **최고** |
| B-2 | **`TokenRefreshResponse`가 `LoginResponse` 상속** → `refresh_token` 필드 누락으로 Pydantic `ValidationError` → 500 | `TokenRefreshResponse(access_token=...).model_dump()` 호출 시 `refresh_token: str` 필드 없어 검증 실패 | 높음 (확인된 버그) |
| B-3 | `set_cookie(domain="localhost")` → Chrome이 `domain=localhost` 쿠키 거부 | RFC 6265 및 Chrome 동작: `domain=localhost`는 퍼블릭 서픽스 목록 외 도메인으로 처리 불안정 | 중간 |
| B-4 | `samesite` 파라미터 미명시 → FastAPI 기본값 `lax` 적용, Vite proxy 경유 시 문제없으나 직접 호출 시 쿠키 미전달 | `set_cookie()` 호출에 `samesite` 없음 | 중간 |
| B-5 | DB 연결 실패 또는 `kakao_id` 타입 불일치 → 500 에러 | `kakao_id = str(kakao_user_data.get("id"))` — None 가능성 | 낮음 |

### OAuth / 설정

| # | 가설 | 근거 | 가능성 |
|---|------|------|--------|
| O-1 | 카카오 개발자 콘솔 Redirect URI 미등록 | 가장 흔한 초기 설정 오류 | **최고** |
| O-2 | React StrictMode에서 `useEffect` 2회 실행 → 인가 코드 재사용 → `KOE320` 에러 | `called.current` ref로 방어 중이나 StrictMode mount/unmount/remount 시 ref 초기화 여부 불확실 | 중간 |
| O-3 | `VITE_KAKAO_REST_API_KEY`에 JavaScript 키 사용 (REST API 키 아님) | 키 타입 혼동 | 낮음 |

### Infrastructure

| # | 가설 | 근거 | 가능성 |
|---|------|------|--------|
| I-1 | `app/main.py`에 CORS 미들웨어 없음 → `http://localhost:5173` origin 차단 | `app/main.py` 확인 결과 `CORSMiddleware` 미설정 | **높음 (확인된 누락)** |
| I-2 | Vite proxy 미작동 → `/api` 요청이 백엔드에 미도달 | `vite.config.ts` proxy 설정 있으나 백엔드 미실행 시 502 | 중간 |

---

## 4️⃣ 원인 검증 방법

### Step A: 카카오 콘솔 확인 (코드 없이 즉시 확인 가능)
1. [카카오 개발자 콘솔](https://developers.kakao.com) → 내 애플리케이션 → 카카오 로그인 → Redirect URI
2. `http://localhost:5173/auth/kakao/callback` 등록 여부 확인
3. REST API 키 = `VITE_KAKAO_REST_API_KEY` = `KAKAO_REST_API_KEY` 일치 여부 확인

### Step B: 브라우저 Network 탭
```
POST /api/v1/auth/kakao
  → 200: 응답 body의 is_new_user, access_token, temp_token 값 확인
  → 401: 카카오 인증 실패 (redirect_uri 불일치 또는 코드 만료)
  → 500: 백엔드 내부 오류 (TokenRefreshResponse 버그 또는 DB 오류)
  → CORS 에러: CORSMiddleware 미설정
```

### Step C: 백엔드 로그
```bash
docker compose logs -f app
# 또는
uv run uvicorn app.main:app --reload
```
- `[Kakao Token API Error]` → redirect_uri 불일치 (KOE006)
- `ValidationError` → TokenRefreshResponse 모델 버그
- `DB connection` 에러 → DB 미실행

### Step D: 브라우저 Application 탭
- Cookies → `localhost` → `refresh_token` 존재 여부 및 속성 확인
- sessionStorage → `temp_token` 저장 여부 확인

---

## 5️⃣ 디버깅 체크리스트

- [x] **Step 1**: 카카오 콘솔 Redirect URI 등록 확인 (사용자 확인 완료)
- [x] **Step 2**: `POST /api/v1/auth/kakao` 응답 상태코드 확인
- [x] **Step 3**: 응답 body `is_new_user` / `access_token` / `temp_token` 값 확인
- [x] **Step 4**: `Set-Cookie: refresh_token` 헤더 존재 여부 확인
- [x] **Step 5**: `app/main.py`에 `CORSMiddleware` 추가 여부 확인 → 추가 완료
- [x] **Step 6**: `TokenRefreshResponse` 모델 `refresh_token` 필드 누락 확인 → 수정 완료
- [x] **Step 7**: `set_cookie(domain="localhost")` → Chrome 거부 여부 확인 → 수정 완료
- [ ] **Step 8**: `KakaoCallbackPage` `.catch()` 블록 진입 여부 console.error로 확인

---

## 6️⃣ 예상 원인 TOP 3

### 🥇 1위: 카카오 콘솔 Redirect URI 미등록 + CORS 미설정 (O-1, I-1)

- `app/main.py`에 `CORSMiddleware`가 없음 → `http://localhost:5173`에서의 API 호출이 브라우저에서 차단됨
- 카카오 콘솔 Redirect URI 미등록 시 카카오 토큰 발급 단계에서 즉시 `KOE006` 에러
- 두 조건 중 하나만 해당해도 콜백 처리 실패 → `.catch()` → `navigate('/')` → 무한 루프

### 🥈 2위: `TokenRefreshResponse` 모델 버그 (B-2)

- `class TokenRefreshResponse(LoginResponse): pass`
- `LoginResponse`는 `access_token: str`과 `refresh_token: str` 두 필드를 가짐
- `/token/refresh` 엔드포인트에서 `TokenRefreshResponse(access_token=str(access_token)).model_dump()` 호출 시 `refresh_token` 필드 누락 → Pydantic v2 `ValidationError` → 500
- 초기 로그인 무한 루프의 직접 원인은 아니지만, 로그인 후 토큰 갱신 시 동일한 무한 루프 재발

### 🥉 3위: `set_cookie(domain="localhost")` 쿠키 거부 (B-3)

- RFC 6265bis 및 Chrome 동작: `domain=localhost`는 명시적으로 설정 시 일부 브라우저에서 거부
- `refresh_token` 쿠키 미저장 → `/token/refresh` 호출 시 401 → `window.location.href = '/'`
- 로그인 직후가 아닌 재방문 시 무한 루프 유발

---

## 7️⃣ 코드 수정 작업 목록 (TDD 순서)

> **AGENTS.md 규칙**: 각 항목은 Red(실패 테스트 작성) → Green(최소 구현) → Refactor 순서로 진행.
> **SYSTEM_DESIGN.md 규칙**: Python 코드에서 `typing` 모듈 사용 금지, built-in 타입만 사용.
> 구조적 변경(Tidy First)과 동작 변경을 반드시 분리하여 커밋.

---

### 🔴 [TASK-1] `TokenRefreshResponse` 모델 버그 수정 — 확인된 버그, 최우선

**영향 범위**: `app/dtos/auth.py`, `app/apis/v1/auth_routers.py`, `app/tests/auth_apis/test_token_api.py`

**하위호환성**: `/token/refresh` 응답 스키마 변경 → 프론트엔드 `authApi.ts`의 `refreshToken()` 함수가 `data.access_token`만 사용하므로 영향 없음.

**Red (실패 테스트 먼저)**:
```python
# app/tests/auth_apis/test_token_api.py 에 추가
async def test_token_refresh_response_has_no_refresh_token_field(self):
    """토큰 갱신 응답에 refresh_token 필드가 없어야 한다."""
    # ... refresh_token 쿠키 설정 후
    response = await client.get("/api/v1/auth/token/refresh")
    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()
    assert "refresh_token" not in response.json()  # 현재 이 assertion이 실패함
```

**Green (최소 수정)**:
- `app/dtos/auth.py`: `TokenRefreshResponse`를 `LoginResponse` 상속에서 독립 모델로 분리
  ```python
  class TokenRefreshResponse(BaseModel):
      access_token: str
  ```

**테스트 업데이트 필요**:
- `test_token_api.py`의 `test_token_refresh_success`: 현재 `signup` → `login` 흐름을 사용하는데, 이 엔드포인트들(`/api/v1/auth/signup`, `/api/v1/auth/login`)이 현재 코드에 존재하지 않음 → **테스트 자체가 깨진 상태**
- 카카오 기반 프로젝트에 맞게 테스트를 mock 기반으로 재작성 필요 (아래 TASK-5 참조)

---

### 🔴 [TASK-2] `CORSMiddleware` 추가 — 확인된 누락

**영향 범위**: `app/main.py`

**하위호환성**: 신규 미들웨어 추가이므로 기존 동작에 영향 없음. 단, `allow_origins` 범위를 환경별로 제한해야 보안 유지.

**Red (실패 테스트 먼저)**:
```python
# app/tests/auth_apis/ 에 test_cors.py 추가
async def test_cors_allows_frontend_origin(self):
    """프론트엔드 origin에서의 preflight 요청이 허용되어야 한다."""
    async with AsyncClient(...) as client:
        response = await client.options(
            "/api/v1/auth/kakao",
            headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
        )
    assert response.status_code == status.HTTP_200_OK
    assert "access-control-allow-origin" in response.headers
```

**Green (최소 수정)**:
- `app/main.py`에 `CORSMiddleware` 추가
- `allow_origins`: 로컬 `["http://localhost:5173"]`, 프로덕션은 실제 도메인
- `allow_credentials=True` (쿠키 전달 필수)

**2025/2026 Best Practice** (OWASP CORS 가이드라인):
- `allow_origins=["*"]` 절대 금지 (특히 `allow_credentials=True`와 함께 사용 불가)
- 환경 변수 `ALLOWED_ORIGINS`로 관리

---

### 🔴 [TASK-3] `refresh_token` 쿠키 설정 개선

**영향 범위**: `app/apis/v1/auth_routers.py`, `app/core/config.py`

**하위호환성**: 쿠키 속성 변경 → 기존 저장된 쿠키는 만료 후 재발급 시 새 설정 적용. 즉각적 영향 없음.

**Red (실패 테스트 먼저)**:
```python
async def test_kakao_login_existing_user_sets_cookie_without_domain_localhost(self):
    """refresh_token 쿠키에 domain=localhost가 설정되지 않아야 한다."""
    # mock으로 기존 회원 카카오 로그인 처리 후
    set_cookie_header = response.headers.get("set-cookie", "")
    assert "domain=localhost" not in set_cookie_header.lower()
    assert "samesite=lax" in set_cookie_header.lower()
```

**Green (최소 수정)**:
- `auth_routers.py`의 `set_cookie()` 호출에서:
  - 로컬 환경: `domain=None` (domain 파라미터 제거)
  - `samesite="lax"` 명시적 추가
- `config.py`: `COOKIE_DOMAIN` 기본값을 빈 문자열 대신 `None`으로 변경 고려

**2025/2026 Best Practice** (MDN Web Docs, RFC 6265bis):
- `domain=localhost` 설정은 RFC 6265bis에서 명시적으로 문제가 있는 패턴으로 언급
- 로컬 개발 시 `domain` 속성 생략이 올바른 방법
- `SameSite=Lax` + `Secure=False` (로컬) 조합이 표준

---

### 🔴 [TASK-4] `KakaoCallbackPage` 에러 처리 개선

**영향 범위**: `frontend/src/pages/KakaoCallbackPage.tsx`

**하위호환성**: 프론트엔드 단독 변경, 백엔드 API 계약 변경 없음.

**수정 내용**:
- `.catch()` 블록에 `console.error` 추가 (디버깅용)
- `navigate('/')` 전 에러 상태를 state로 전달하는 현재 구조는 유지 (이미 올바름)
- `data.is_new_user`가 true/false 모두 아닌 경우(undefined 등) 방어 처리 추가

**2025/2026 Best Practice** (React Router v6 공식 문서):
- `navigate('/', { state: { error: msg } })` 패턴은 올바름
- `replace: true` 옵션으로 콜백 페이지를 히스토리에서 제거하는 현재 구조 유지

---

### 🔴 [TASK-5] 기존 테스트 코드 정합성 수정 — 중요

**현재 문제**: 기존 테스트들이 존재하지 않는 엔드포인트를 참조하고 있음

| 테스트 파일 | 참조 엔드포인트 | 실제 존재 여부 |
|------------|----------------|---------------|
| `test_login_api.py` | `POST /api/v1/auth/signup`, `POST /api/v1/auth/login` | ❌ 없음 |
| `test_signup_api.py` | `POST /api/v1/auth/signup` | ❌ 없음 |
| `test_token_api.py` | `POST /api/v1/auth/signup`, `POST /api/v1/auth/login` | ❌ 없음 |
| `test_user_me_apis.py` | `POST /api/v1/auth/signup`, `POST /api/v1/auth/login` | ❌ 없음 |

**User 모델 불일치**: 테스트에서 `name`, `password`, `birth_date` 필드를 사용하지만, 실제 `User` 모델에는 이 필드들이 없음 (`nickname`, `kakao_id` 기반 구조).

**수정 방향**:
- 카카오 OAuth 기반 인증 흐름에 맞게 테스트를 `unittest.mock.patch`로 외부 카카오 API를 mock 처리하여 재작성
- `test_login_api.py`, `test_signup_api.py`: 카카오 로그인/회원가입 흐름으로 교체
- `test_token_api.py`: `test_token_refresh_success`를 카카오 로그인 mock 후 쿠키 기반으로 재작성
- `test_user_me_apis.py`: 카카오 로그인 mock 후 JWT 발급 → `/users/me` 호출로 재작성

**과하거나 중복된 테스트 제거**:
- `test_signup_invalid_email`: Pydantic 자체 검증 테스트 → 자명한 프레임워크 동작, 제거 대상
- `test_login_invalid_credentials`: 현재 카카오 전용 구조에서 이메일/비밀번호 로그인 자체가 없으므로 제거 대상

**새로 추가할 테스트**:
```python
# app/tests/auth_apis/test_kakao_auth.py (신규)
# - test_kakao_login_existing_user_returns_access_token
# - test_kakao_login_new_user_returns_temp_token
# - test_kakao_login_invalid_code_returns_401
# - test_kakao_signup_success_with_valid_temp_token
# - test_kakao_signup_invalid_temp_token_returns_401
# - test_kakao_signup_duplicate_kakao_id_returns_409
```

---

### 🔴 [TASK-6] Protected Route 구현 (Medium Priority)

**영향 범위**: `frontend/src/App.tsx`, 신규 `frontend/src/components/ProtectedRoute.tsx`

**하위호환성**: 라우팅 구조 변경 → 기존 직접 URL 접근 차단. 의도된 동작 변경.

**수정 내용**:
- `/main`: `accessToken` 없으면 `/`로 리다이렉트
- `/signup`: `sessionStorage`의 `temp_token` 없으면 `/`로 리다이렉트
- 현재 `MainPage`와 `SignupPage`에 가드 없음 → 직접 URL 접근 시 빈 화면 또는 오류

**2025/2026 Best Practice** (React Router v6.4+ 공식 문서):
```tsx
// ProtectedRoute 패턴 (React Router v6 권장)
function ProtectedRoute({ children }: { children: ReactNode }) {
  const accessToken = useAuthStore((s) => s.accessToken)
  return accessToken ? children : <Navigate to="/" replace />
}
```

---

### 🔴 [TASK-7] `authStore` 새로고침 후 토큰 복구 (Medium Priority)

**영향 범위**: `frontend/src/store/authStore.ts`, `frontend/src/App.tsx`

**현재 문제**: Zustand store는 메모리 저장 → 페이지 새로고침 시 `accessToken` 소실 → Protected Route가 `/`로 리다이렉트

**수정 방향**:
- 앱 초기화 시 `GET /api/v1/auth/token/refresh` 자동 호출로 `refresh_token` 쿠키 기반 복구
- `zustand/middleware`의 `persist` 사용은 XSS 취약점 우려로 **비권장** (access token을 localStorage에 저장하지 않는 것이 2025년 보안 표준)
- HttpOnly 쿠키의 `refresh_token`으로 silent refresh 패턴 사용

**2025/2026 Best Practice** (Auth0, OWASP 2025):
- Access token: 메모리(Zustand)에만 저장 ✅ (현재 올바름)
- Refresh token: HttpOnly 쿠키 ✅ (현재 올바름)
- 페이지 로드 시 silent refresh로 access token 복구

---

## 8️⃣ 수정 우선순위 요약

| 순위 | TASK | 유형 | 무한 루프 직접 원인 |
|------|------|------|-------------------|
| 1 | TASK-2: CORS 미들웨어 추가 | 동작 변경 | ✅ 직접 원인 |
| 2 | TASK-1: TokenRefreshResponse 버그 | 동작 변경 | ⚠️ 토큰 갱신 시 원인 |
| 3 | TASK-3: 쿠키 domain/samesite 수정 | 동작 변경 | ⚠️ 재방문 시 원인 |
| 4 | TASK-5: 기존 테스트 정합성 수정 | 구조 변경 (Tidy First) | - |
| 5 | TASK-4: KakaoCallbackPage 에러 처리 | 동작 변경 | - |
| 6 | TASK-6: Protected Route | 동작 변경 | - |
| 7 | TASK-7: Silent refresh | 동작 변경 | - |

> **커밋 규칙 (AGENTS.md)**: 구조적 변경(TASK-5)은 동작 변경(TASK-1~4)과 반드시 분리하여 커밋.
