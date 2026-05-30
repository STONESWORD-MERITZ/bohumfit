# SURIT-016: 백엔드 의존성 버전 고정

## Owner
- Codex

## Status
- Completed

## Context
- `backend/requirements.txt`의 직접 의존성이 미고정이면 신규 릴리스 하나로 Railway 빌드 재현성이 깨질 수 있다.
- 목표는 임의 최신 버전이 아니라 현재 로컬 테스트가 통과하는 설치 버전으로 직접 의존성만 `==` 고정하는 것이다.

## Scope
- `backend/requirements.txt`
- `.agent-harness/tasks/SURIT-016-pin-deps.md`
- `.agent-harness/handoff.md`
- `.agent-harness/locks.md`

## Work
- 기준선 `cd backend && python -m pytest -q` 통과 여부 확인.
- `requirements.txt` 직접 의존성 목록 파악.
- 현재 설치 버전 확인.
- 이미 명시된 직접 의존성만 현재 설치 버전으로 `==` 고정.
- 가능한 경우 임시 새 venv에서 `pip install -r requirements.txt` 후 pytest 재실행.

## Constraints
- 새 패키지 추가 금지.
- 전이 의존성 전체 freeze 금지.
- 버전 업그레이드 금지.
- `requirements.txt` 외 런타임 파일 변경 금지.

## Verification
- `cd backend && python -m pytest -q` (고정 전)
- `cd backend && python -m pytest -q` (고정 후)
- 가능하면 새 venv에서 `pip install -r requirements.txt` 및 `python -m pytest -q`

## Expected Result
- 직접 의존성이 현재 통과 버전으로 고정된다.
- 기존 테스트 통과 상태가 유지된다.
- 다음 Railway 배포에서 재현 가능한 설치 기준이 생긴다.
