# BOHUMFIT-223 - 개발 의존성 고정 + Windows 셋업 문서화

Owner flow: Human -> Codex Windows -> Human
Current owner: Human
Date: 2026-07-17

## Intent

- Windows 신규 개발 환경에서 백엔드 테스트와 Playwright Chromium 렌더 환경을 같은 버전과 순서로 재현할 수 있게 한다.
- 현재 Python 3.12.10 설치본의 개발 전용 패키지 버전을 별도 파일에 고정하고 필수 런타임 선행조건을 문서화한다.

## Scope

- 수정 허용: `backend/requirements-dev.txt`, `README.md`, 본 태스크와 harness handoff/locks.
- 수정 금지: `src/`, 백엔드 Python 코드, 기존 `backend/requirements.txt`, 배포 설정, DB/RLS, 인증, 결제.
- 보존: 애플리케이션 동작과 backend pytest 기준선 `618 passed, 8 skipped`.

## Work

- `backend/requirements-dev.txt`를 신설하고 현재 설치본 `pytest`, `playwright` 버전을 정확히 고정한다.
- README에 Windows 신규 환경 셋업 순서를 추가한다: 런타임 준비, 운영/개발 requirements 설치, Playwright Chromium 설치.
- Microsoft Visual C++ 2015-2022 Redistributable (x64)가 필요함을 명시한다.
- 코드와 기존 운영 의존성 파일은 변경하지 않는다.

## Verification

- 설치 버전 확인: Python 3.12.10 환경의 `python -m pip show pytest playwright`.
- `git diff --check` 및 설정·문서 내용 정적 확인.
- `cd backend && python -m pytest -q`: `618 passed, 8 skipped`.
- `git diff --name-only -- src backend/*.py backend/pipeline backend/coverage`: 코드 변경 0.

## Handoff Requirements

- Changed: 고정 버전과 문서화한 셋업 순서.
- Verified: 설치본 버전, pytest 기준선, 코드 변경 0.
- Notes: 사용자 소유 미추적 파일은 제외.
- Next: Human.

## Result

- `backend/requirements-dev.txt`에 Windows Python 3.12.10 설치본 기준 `pytest==9.1.1`, `playwright==1.52.0`을 고정했다.
- README에 Python 3.12.10과 Microsoft Visual C++ 2015-2022 Redistributable (x64) 선행 설치, 운영/개발 requirements 설치, Playwright Chromium 설치 순서를 추가했다.
- 애플리케이션 코드, 기존 `backend/requirements.txt`, 배포 설정은 변경하지 않았다.

## Verification Result

- `python -m pip show pytest playwright`: `pytest 9.1.1`, `playwright 1.52.0` 확인.
- `cd backend && python -m pytest -q`: **618 passed, 8 skipped**, 기존 Starlette/httpx deprecation warning 1건.
- 첫 권한 실행에서는 PATH에 npm이 없어 parity 테스트 1건이 추가 스킵됐고, Windows npm 경로를 포함한 최종 권위 실행에서 기준선을 확인했다.
- `git diff --check`: passed.
- `src/`, 백엔드 Python 코드, pipeline/coverage 변경 0.
- 사용자 소유 미추적 `.env.txt`는 조회·수정·스테이지하지 않았다.
