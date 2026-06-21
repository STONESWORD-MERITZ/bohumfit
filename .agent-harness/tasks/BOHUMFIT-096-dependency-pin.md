# BOHUMFIT-096 백엔드 의존성 버전 고정
## Goal
backend/requirements.txt의 미고정 패키지를
현재 설치 버전으로 == 고정하여 Railway 빌드 재현성 확보.
## Scope
- backend/requirements.txt
## Out of Scope
- 버전 업그레이드 금지 (현재 설치 버전 그대로 고정)
## 방법
- `pip freeze`로 현재 설치 버전 확인 → requirements.txt 미고정(`==` 없는) 항목만 설치 버전으로 고정.
- 이미 고정된 항목은 그대로. 다운/업그레이드 금지.
- `pip install -r requirements.txt --dry-run`으로 충돌 없음 확인.
