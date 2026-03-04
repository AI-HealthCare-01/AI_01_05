# 기존 구현 vs 이번 작업 변경점

기준 명세: `API명세서_최종 - 일기&리포트 API.csv`

## 1) API 경로/구조

### 기존
- `diary_routers.py`가 `/diaries`, `/report` 중심으로 구성
- 명세의 `/api/v1/diary/...` 계층형 URL과 불일치
- `REPORT-004 (PUT /api/v1/diary/report/{reportId})` 미구현

### 이번 작업
- `app/apis/v1/diary_routers.py`를 명세 기준으로 재작성
- `/api/v1/diary/...` 경로 13개 구현
  - `DIARY-001 ~ DIARY-009`
  - `REPORT-001 ~ REPORT-004`

## 2) 인증/에러 응답

### 기존
- diary/report 계열에서 인증 체크가 사실상 없음
- 에러 포맷이 명세(`{"error": "..."}`)와 일관되지 않음

### 이번 작업
- `Authorization: Bearer ...` 헤더 최소 검증 적용
- 명세형 에러 코드 반영
  - `UNAUTHORIZED`
  - `INVALID_PARAM`
  - `INVALID_DATE_RANGE`
  - `DIARY_NOT_FOUND`
  - `ENTRY_NOT_FOUND`
  - `REPORT_NOT_FOUND`
  - `UNSUPPORTED_FORMAT`
  - `FILE_TOO_LARGE`

## 3) DTO(요청/응답 스키마)

### 기존
- `DiaryCreateDTO`, `ReportCreateRequest` 등 최소 필드만 존재
- OCR/챗봇요약/캘린더 스키마 미정의

### 이번 작업
- `app/dtos/diary_report_dto.py` 신규 추가
- 명세 기반 DTO 분리
  - 캘린더 응답
  - 날짜별 일기 조회 응답
  - 직접입력/OCR확정/챗봇요약 저장 요청
  - 리포트 목록/상세/수정 요청·응답

## 4) 저장소(인메모리) 구조

### 기존
- `fake_db`, `fake_report_db` 단순 리스트

### 이번 작업
- `app/core/memory_db.py` 확장
  - `fake_diary_entries`
  - `fake_report_db`
  - `fake_ocr_pending`
  - `fake_chatbot_pending`
  - `diary_entry_sequence`, `report_sequence`

## 5) 테스트

### 기존
- auth/user 중심 테스트만 존재
- diary/report 명세 API 검증 부재

### 이번 작업
- `app/tests/diary_apis/test_diary_report_apis.py` 추가
  - 권한 실패 케이스
  - 일기 생성/조회
  - OCR 업로드/확정
  - 리포트 생성/목록/상세/수정

## 6) 현재 한계(알아둘 점)

- 현재 구현은 **인메모리 기반 임시 로직**
- ERD 기반 실제 DB 모델/리포지토리 연동은 아직 미반영
- 테스트는 작성했지만, 현 환경에서 공통 테스트 설정이 MySQL 연결을 요구해 실행 실패 가능
