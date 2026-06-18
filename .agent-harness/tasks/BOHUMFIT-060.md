# BOHUMFIT-060 백엔드 보안 강화 — 운영모드·문서비활성·헬스최소화·레이트리밋

## Owner
- Cowork (구현+회귀) → Codex (Windows 전체 검증·커밋·푸시) → Human (Supabase 가입정책·레이트리밋 수치 승인)

## 근거
- 레드팀 보안 보고서(2026-06-18) bohumfit 백엔드 이슈. 대상 backend/(Railway FastAPI). 분석 판정 로직 무변경(보안 표면만).

## STEP 0 진단 (구현 전)
- **ENV/debug**: `SERVICE_ENV` 기본값이 `"development"`(L36) — 미설정 시 디버그 취급(역안전). `FastAPI(title,version)`만(L154) — debug·docs 설정 없음 → **문서 기본 노출**.
- **/api/health**(L398~409): `status`+`env`(SERVICE_ENV)+`deps`(google_api_key·sentry bool)+`version`(RAILWAY_GIT_COMMIT_SHA[:7]) → env·커밋해시·의존성 노출. version은 env var에서 주입.
- **/docs·/redoc·/openapi**: 설정 없음 → 기본 노출.
- **slowapi**: limiter(L157, default 60/min)+핸들러(L159, slowapi 기본 영문). 적용됨 — `/api/analyze`(L406 `5/minute,30/hour`)·`/api/report/pdf`(L559 `10/minute,60/hour`). 즉 레이트리밋은 **이미 존재**, 갭=한국어 메시지·운영 안전 기본.
- 전역 예외 핸들러 **없음**.

## STEP 1~4 구현 (backend/main.py)
- **BF-01 운영모드**: `SERVICE_ENV` 기본값 `production`으로(미설정/오타→production·안전). `IS_DEVELOPMENT=(env=="development")`·`IS_PRODUCTION=not`. `FastAPI(debug=IS_DEVELOPMENT)`. 전역 `@app.exception_handler(Exception)` 추가 — 미처리 예외에 한국어 일반화 메시지(500), 상세는 `logger.exception`/Sentry로만(052·047 일관). HTTPException·RateLimitExceeded는 각 핸들러가 처리(미도달).
- **BF-02 문서**: `docs_url/redoc_url/openapi_url = None if IS_PRODUCTION else 기본`. 운영 비활성·개발 유지.
- **BF-05 헬스**: `/api/health` → `{"status":"ok"}`로 축소(env·deps·version 제거). Railway 헬스체크 200 유지. 상세 관측은 Sentry.
- **BF-03 레이트리밋**: slowapi 기본 핸들러(영문)를 `_rate_limit_handler`(한국어 429 "요청이 너무 잦습니다…")로 교체. 기존 한도(analyze 5/min·30/h, report 10/min·60/h)·업로드 제한(10개·15MB·40MB) **유지**. 미사용 `_rate_limit_exceeded_handler` import 제거.

## 회귀 테스트 (신규 tests/test_security_hardening_060.py, 9)
- 헬스 최소화({"status":"ok"}·env/version/deps 0) / 운영 docs·redoc·openapi 404 / 개발 docs·openapi 200 / 미설정·오타 env→production / 전역 예외 500 한국어·상세("boom"/"RuntimeError") 미노출 / 429 한국어 / analyze·report 라우트+limiter 등록 / 업로드 제한(10·15MB·40MB) 유지.
- `slowapi/fastapi` importorskip(미설치 환경 자동 skip→Codex). main 의존 → 마운트 복구 환경에서 실행.

## 검증
- /tmp(마운트 복구: main.py tail 재구성·pdf_parser splice·surgery_exclusions 059 동기·report_pdf import stub)에서 **slowapi/python-multipart 설치 후 TestClient로 실제 main.py 검증**: **060 9/9 passed**. 광범위(main_launch_guardrails·059·surgery·q3·q4q5 등 포함) **44 passed·회귀 0**. `test_main_launch_guardrails`는 production 기본에도 bohumfit.ai CORS 유지로 통과.
- ⚠ 마운트 view 손상 지속(main/pdf_parser/report_pdf truncation·analyzer L981 runtime·surgery_exclusions stale snapshot — 모두 060 무관 환경결함). 실파일(Read/Grep)로 편집 정합 확인. 전체 pytest는 Codex/Windows 권위.

## 자체 점검
- ☑ production debug=False·docs 비활성 ☑ development docs 유지(분기) ☑ /api/health env·해시·deps 0 ☑ analyze·report 레이트리밋·429 한국어 ☑ 정상 10파일 1회는 5/min 한참 아래(미차단) ☑ 전역 예외 상세 미노출 ☑ 분석/파싱/result_builder·052/055/058 무변경 ☑ 가용 pytest 회귀 0.

## Notes — Human 확인
- **레이트리밋 수치**: analyze 5/min·30/h, report 10/min·60/h(기존 유지·보수적). 정상 사용(파일 10개=analyze 1회)은 미차단. 일일 쿼터 추가는 미적용(필요 시 Human 승인 후 `/day` 추가). **수치 승인/조정 Human**.
- ⚠ **proxy-IP 주의**: 레이트리밋 key=`get_remote_address`(IP). Railway 프록시 뒤에서 모든 사용자가 프록시 IP로 보이면 **집단 throttle 위험**(기존부터 존재). 토큰(사용자) 단위 키 전환은 별도 검토 권장 — Human/Codex 판단.
- **Supabase 가입 개방(disable_signup)·이메일 인증**은 코드 밖(대시보드) → **Human: Supabase 가입/이메일인증 정책 확인** 필요.

## Next
- **Codex(Windows)**: 전체 pytest(기준선 344 + 신규 9)·tsc/lint/build → 범위 파일 stage→commit→push. 커밋: `BOHUMFIT-060: 백엔드 보안 강화 — 운영 debug·문서 비활성·헬스 최소화·레이트리밋 한국어 429`.
- **Human**: 레이트리밋 수치 승인(+proxy-IP/토큰키 판단), Supabase 가입·이메일인증 정책 확인.
