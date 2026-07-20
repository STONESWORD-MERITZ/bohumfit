# BOHUMFIT-229 — pillow·python-multipart 보안 상향 (228 pip-audit 후속)

Owner flow: Claude Chat -> Claude Code -> Codex
Current owner: Codex (1차 검증 완료 — 2차 검증·커밋 대기)
Risk tier: 중위험 — 풀 하네스. git 쓰기(add/commit/push) 전면 금지, 커밋은 Codex 담당.
Date: 2026-07-20

## 목적

228 pip-audit에서 확인된 backend 취약점 11건 해소:
pillow 12.2.0 → 12.3.0 (PYSEC 8건), python-multipart 0.0.29 → 0.0.31 (PYSEC 3건, 업로드 직접 경로).

## 수정 범위

backend/requirements.txt (두 패키지 버전 핀 변경만)

## 수정 금지

- 다른 패키지 버전 이동 0 — pip 의존성 해석으로 부수 이동이 강제되면 중단·보고
- backend/ 코드(.py) 수정 금지. requirements-dev.txt 무접촉(228 리포트상 0건)
- backend/pipeline/, backend/coverage/, supabase/, src/, .env* 무접촉
- 인코딩 주의: requirements.txt 한국어 주석 보존 — 파일 인코딩·개행 변경 금지
  (버전 문자열 두 줄만 치환, 실행 시 PYTHONUTF8=1)

## STEP 0 실측 (2026-07-20)

- 설치본 = requirements 핀 일치: pillow 12.2.0, python-multipart 0.0.29 (드리프트 0).
- pillow: backend .py에서 `PIL` 직접 import **0건** — pdfplumber 경유 전이 의존성(140 주석 명시와 일치).
  실사용 경로 = PDF 파싱(pdfplumber) + 리포트 렌더 체인.
- python-multipart: FastAPI `File/UploadFile` 경유 간접 사용. 업로드 엔드포인트 실측 4곳
  (main.py:1659 보장분석서/제안서, :1697 KB 신정원 제안서, :1736 신규 제안서 목록, :1884 심평원 진료 PDF).
- requirements.txt = UTF-8(BOM 없음)·CRLF — 치환 후 `file` 재확인으로 보존 검증.

## 진행 결과

- 핀 변경 diff 정확히 2줄(pillow==12.3.0, python-multipart==0.0.31), 한국어 주석·인코딩·개행 무변경.
- `pip install -r requirements.txt`: 두 패키지만 이동("Installing collected packages: python-multipart, pillow"),
  다른 패키지 부수 이동 **0**. `pip show` 12.3.0/0.0.31 확인.
- `pip check`: 충돌 0 ("No broken requirements found").
- `PYTHONUTF8=1 pip-audit -r requirements.txt --no-deps`: **11건 → 0건** ("No known vulnerabilities found").

## 검증 체크리스트 (1차 — Code 직접 실행, 2026-07-20 결과)

- [x] backend pytest — **618 passed, 8 skipped** 불변, 신버전(12.3.0/0.0.31) 설치 후 실행 (PDF 파싱·이미지·업로드 검증 경로 = 회귀망)
- [x] pip check 충돌 0
- [x] PYTHONUTF8=1 pip-audit 재실행 — **11건 → 0건** ("No known vulnerabilities found")
- [x] git diff = backend/requirements.txt 2줄 + harness 문서만. 인코딩(UTF-8)·CRLF·한국어 주석 보존 확인
- [x] 프런트 미실행 사유: src/·프런트 의존성 무접촉(diff 0)이라 tsc/lint/build/npm test 비대상

## Stage 목록 (Codex용 — Code는 실행 금지)

backend/requirements.txt, tasks/BOHUMFIT-229-*.md, handoff.md, locks.md (.env* 제외)

## 커밋 메시지 (Codex용)

chore(BOHUMFIT-229): pillow 12.3.0·python-multipart 0.0.31 보안 상향 — pip-audit 11건 해소
