# 개발환경 전화번호 인증 자동 우회 계획

## 문제 상황

- 백엔드: `ENV != PROD` + `TEST_VERIFICATION_TOKEN` 일치 시 `validate_verified_token` 우회 처리됨
- 프론트엔드: `phoneVerified` 상태가 `false`이면 `validate()`에서 에러 반환 → 실제 SMS 인증 없이는 가입 불가
- 결과: 개발환경에서도 실제 SMS 인증을 강제로 거쳐야 하는 불편함 발생

---

## 해결 방향

개발환경(`import.meta.env.DEV === true`)일 때, `SignupPage`의 `set()` 함수에서 전화번호 입력 시 자동으로 `VITE_TEST_VERIFICATION_TOKEN`을 세팅하고 `phoneVerified`를 `true`로 설정한다.

---

## 변경 파일

### 1. `frontend/.env`

`VITE_TEST_VERIFICATION_TOKEN` 환경변수 추가. 이 파일은 `*.env` 패턴으로 gitignore 대상이므로 커밋되지 않는다.

```
VITE_TEST_VERIFICATION_TOKEN=test-token-1234
```

값은 백엔드 `envs/.local.env`의 `TEST_VERIFICATION_TOKEN`과 동일해야 함.

### 2. `frontend/example.env`

팀원 온보딩을 위해 키만 추가 (값은 비워둠).

```
VITE_TEST_VERIFICATION_TOKEN=
```

### 3. `frontend/src/pages/SignupPage.tsx`

`set()` 함수 내 `key === 'phone'` 분기 추가.

```ts
const set = (key: string, value: string) => {
  setForm((f) => ({ ...f, [key]: value }))
  setErrors((e) => ({ ...e, [key]: '' }))

  if (key === 'phone' && import.meta.env.DEV) {
    const testToken = import.meta.env.VITE_TEST_VERIFICATION_TOKEN
    if (testToken && value) {
      setVerificationToken(testToken)
      setPhoneVerified(true)
    } else {
      setVerificationToken('')
      setPhoneVerified(false)
    }
  }
}
```

---

## 동작 흐름 (개발환경)

1. 사용자가 전화번호 입력
2. `set('phone', value)` → `import.meta.env.DEV` 분기 진입
3. `verificationToken` ← `VITE_TEST_VERIFICATION_TOKEN`
4. `phoneVerified` ← `true`
5. `validate()` 통과 → `kakaoSignup` 요청 시 test token 전송
6. 백엔드 `validate_verified_token`에서 test token 일치 확인 후 우회

---

## 테스트 계획

### 백엔드 (기존 테스트 영향 없음)

`app/tests/auth_apis/test_signup_api.py`의 기존 3개 테스트는 모두 `validate_verified_token`을 `AsyncMock`으로 patch하므로 이번 변경에 영향받지 않는다. 추가 테스트 불필요.

### 프론트엔드

현재 프로젝트에 `vitest` 등 프론트엔드 테스트 도구가 설치되어 있지 않다(`package.json` 확인). 프론트엔드 테스트 인프라 없이 테스트 파일만 추가하는 것은 실행 불가능하므로 추가하지 않는다.

> 향후 `vitest` 도입 시 아래 케이스를 추가할 것:
> - DEV 환경에서 전화번호 입력 시 `phoneVerified`가 `true`로 세팅되는지
> - 전화번호를 지웠을 때 `phoneVerified`가 `false`로 리셋되는지
> - PROD 환경(`import.meta.env.DEV = false`)에서는 자동 세팅이 발생하지 않는지

---

## 보안 및 하위호환성 검토

- `VITE_TEST_VERIFICATION_TOKEN`은 `frontend/.env`에만 존재하며 `*.env` 패턴으로 gitignore 대상 → 프로덕션 빌드 시 값이 없어 `testToken`이 `undefined`가 됨
- `import.meta.env.DEV`는 Vite 프로덕션 빌드 시 `false`로 치환되어 분기 자체가 dead code로 트리쉐이킹됨 → 이중 방어
- `set()` 함수 시그니처 변경 없음 → 기존 호출부 영향 없음
- 전화번호를 지우면 `phoneVerified`가 `false`로 리셋되어 빈 전화번호로 가입하는 케이스 방지

---

## 체크리스트

- [x] `frontend/.env`에 `VITE_TEST_VERIFICATION_TOKEN` 추가
- [x] `frontend/example.env`에 `VITE_TEST_VERIFICATION_TOKEN=` 키 추가
- [x] `frontend/src/pages/SignupPage.tsx`의 `set()` 함수에 DEV 분기 추가
