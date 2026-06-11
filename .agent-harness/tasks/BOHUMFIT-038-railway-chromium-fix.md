# BOHUMFIT-038 Railway Chromium 설치 미반영 수정

## Owner
Codex

## 배경
운영 로그 기준으로 BOHUMFIT-030 리포트 PDF 장애 원인이 확정됐다.

- 빌드 로그에는 `pip install playwright==1.52.0`만 있고 `python -m playwright install --with-deps chromium` 실행 흔적이 없다.
- `fonts-noto-cjk` 설치 흔적도 없다.
- 런타임 로그는 `report pdf 렌더러 사용 불가: Chromium 미설치`이다.

즉 BOHUMFIT-037의 `nixpacks.toml` 설치 단계가 Railway 빌드에 반영되지 않았다.

## 작업
- `PLAYWRIGHT_BROWSERS_PATH=0`을 Nixpacks variables와 시작 스크립트에 반영해 브라우저를 Python 패키지 경로 내부에 고정한다.
- 시스템 의존성과 CJK 폰트는 `[phases.setup].aptPkgs`로 분리한다.
- 빌드 install phase에서는 `python -m playwright install chromium`만 실행한다.
- 빌드 단계가 계속 무시될 경우를 대비해 backend start script에서 서버 시작 직전 `python -m playwright install chromium`을 재실행한다.
- 레포 루트 배포와 `backend/` Root Directory 배포를 모두 지원한다.

## 트레이드오프
- 시작 시점 fallback은 첫 부팅을 느리게 만들 수 있다.
- 그러나 Chromium 설치 미반영 상태에서도 런타임 PDF 생성 가능성을 회복하는 안전장치다.
- 그래도 실패하면 Dockerfile 또는 Playwright 공식 Python 베이스 이미지 전환을 검토한다.

## 검증
- TOML 파싱
- `cd backend && python -m pytest -q`
- 프런트 영향 없음이지만 표준 `npm run build` 확인
- `npm run lint`
- `npm test`

## 운영 확인
- Codex 세션은 Railway 미인증 상태라 대시보드 Variables 직접 반영과 빌드 로그 확인은 수행할 수 없다.
- Human이 Railway Variables에 `PLAYWRIGHT_BROWSERS_PATH=0`을 추가하고, 재배포 로그에서 시작 스크립트 또는 install phase의 Chromium 설치 로그를 확인해야 한다.
