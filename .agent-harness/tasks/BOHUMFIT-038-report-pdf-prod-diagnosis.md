# BOHUMFIT-038 BOHUMFIT-030 운영 PDF 장애 진단

## Owner
Codex

## Mode
진단 전용. 코드 수정 금지.

## 증상
운영 `/insurance`에서 PDF 저장 시 백엔드 `/api/report/pdf`가 503을 반환하고 프런트에 다음 메시지가 표시된다.

`리포트 생성 기능을 준비 중입니다. 잠시 후 다시 시도해 주세요. BOHUMFIT 리포트 PDF 생성 환경을 확인해 주세요.`

## 조사 항목
- handoff의 BOHUMFIT-030~037 시도 내역 요약.
- `report_pdf.py` / `main.py`에서 해당 문구가 어느 예외 분기에서 발생하는지 확인.
- Railway CLI/대시보드 접근 가능 여부 확인.
- 운영 로그·빌드 로그·컨테이너 상태 확인 가능 시 실제 예외 원문 확보.

## 결과
- Railway CLI는 `npx --yes @railway/cli`로 실행 가능.
- 현재 Codex 세션은 Railway 미인증 상태라 `railway status`, `railway whoami`가 `Unauthorized. Please login with railway login`으로 실패.
- 운영 로그/빌드 로그/컨테이너 쉘은 이번 세션에서 직접 확인 불가.

## 필요 후속
- Human이 Railway 로그인/대시보드에서 `/api/report/pdf` 호출 시점 로그와 최신 빌드 로그를 확인해야 원인 확정 가능.
