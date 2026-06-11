# BOHUMFIT-037 Railway 리포트 PDF 런타임 보강 + 버튼 줄바꿈 방지

## Owner
Codex

## 배경
배포 환경에서 `/insurance`의 `PDF로 저장`을 누르면 `리포트 생성 기능을 준비 중입니다... BOHUMFIT 리포트 PDF 생성 환경을 확인해 주세요`가 표시된다. 이는 백엔드 `/api/report/pdf`가 `ReportUnavailableError`를 반환하는 상황이며, BOHUMFIT-030 Playwright/Chromium PDF 렌더링 환경이 Railway 런타임에 설치되지 않은 것으로 판단된다.

또한 버튼 로딩 문구 `PDF 생성 중...`이 좁은 버튼에서 줄바꿈된다.

## 작업
- Railway/Nixpacks 빌드에서 backend requirements 설치 후 `python -m playwright install --with-deps chromium`을 실행하도록 설정한다.
- Railway Root Directory가 레포 루트 또는 `backend/` 어느 쪽이어도 동작하도록 루트/백엔드 Nixpacks 설정을 함께 둔다.
- Playwright 렌더러가 channel 지정 없이 설치된 Chromium을 사용하도록 조정한다.
- `PDF 생성 중...` 버튼 문구가 줄바꿈되지 않도록 버튼에 `whitespace-nowrap` 및 최소 폭을 적용한다.

## 검증
- `npx tsc -p tsconfig.app.json --noEmit`
- `npx tsc -p tsconfig.node.json --noEmit`
- `npm run lint`
- `npm test`
- `npm run build`
- `cd backend && python -m pytest -q tests/test_report_pdf.py`
- `cd backend && python -m pytest -q`
