# BOHUMFIT-067 로그인 로고 한 줄 + PDF 고객명 직접 입력·리포트 표시

## Owner
- Cowork (구현+회귀) → Codex (Windows tsc/lint/build·전체 pytest·실 PDF/로그인 육안·커밋·푸시)
- ※ 066 커밋(6622589) 완료 후 시작(충돌 방지). 066과 같은 파일(Disclosure.tsx·report_pdf·template) 위에 추가 작업.

## 구현
### (A) 로그인 로고 줄바꿈 제거
- `src/components/Logo.tsx`: 외곽 inline-flex span에 `whiteSpace:"nowrap"`·`wordBreak:"keep-all"`·`flexShrink:0` 추가 → 좁은 폭에서도 "BohumFit 보험핏"·"보험/핏" 줄바꿈 방지(한 줄 유지). 로그인(Login.tsx)·전역 로고 공통 적용.
### (B) 고객명 직접 입력 UI + 우선순위 (Disclosure.tsx ResultView)
- 신규 state `customerName`(선택 입력) + PDF 저장 영역에 입력 필드(placeholder=자동추출값 또는 "선택 입력", maxLength 20).
- `effectiveCustomerName = customerName.trim() || result.customer_name || ""` — **우선순위 입력 > 공단 자동추출(065) > ""**.
- report 요청 payload `customer_name`·다운로드 파일명 `safeName` 모두 effectiveCustomerName 사용.
### (C) 리포트 본문 고객명 표시 (report_pdf + template)
- `report_pdf.render_disclosure_html` ctx에 `"customer_name": (payload.get("customer_name") or "").strip()` 추가(공백만이면 "" → 생략).
- `templates/report_disclosure.html` 헤더 `.head-meta`(문서번호·생성일시 옆)에 `{% if customer_name %}고객명 <b>{{ customer_name }}</b><br>{% endif %}` — 있으면 표시, 없으면 줄 생략. PII: 화면·PDF 표시만, 서버 영구 저장 안 함(휘발 설계 유지).
### (D) 파일명 (067 입력값 반영)
- `보험핏-고지내역-{고객명}-{기준일}.pdf` — 고객명=effectiveCustomerName(입력>자동>날짜만). sanitize(`[^가-힣A-Za-z0-9]` 제거·20자)·백엔드 RFC5987(`filename*`)+ASCII 병기는 065 유지(main.py report endpoint·payload 그대로).

## 검증
- 신규 `tests/test_report_customer_name_067.py`(4): ④ 고객명 표시(고객명·홍길동 노출)·미입력 생략·공백만 생략(report_pdf strip)·헤더(문서번호/생성일시/점검 기준일) 유지.
- /tmp(마운트 복구: template tail 재구성·report_pdf tail splice) → **067 4/4 + test_report_pdf_q1q5 6/6 = 10 passed·회귀 0**. 실 템플릿 standalone Jinja 렌더로 `{% if customer_name %}` 조건(설정→고객명 표시·""→생략·헤더 유지) 확인.
- ⚠ report_pdf/template 마운트 truncation(L538·L260 — 067 무관 환경결함) → /tmp 복구로 검증. 프런트 tsc/lint/build·로그인 한 줄 육안·실 PDF 본문 고객명은 Codex/Windows. ①②③ 파일명 우선순위는 프런트 로직(effectiveCustomerName) — 065 filename 회귀(test_report_filename_065)가 payload→파일명 경로 커버, 우선순위는 Codex tsc/build.

## 자체 점검
- ☑ 로그인 로고 한 줄(nowrap/keep-all) ☑ 고객명 입력 UI·우선순위(입력>자동>날짜) ☑ 리포트 본문 고객명 표시/생략 ☑ 파일명 effectiveCustomerName 반영 ☑ report-only 변경(분석/판정 무관)·가용 pytest 회귀0 ☐ npm build/tsc/lint·육안(Codex).

## Notes
- 분석/판정·056~066 로직 무변경(로고·고객명 표시/입력만). 고객명 PII는 출력(화면·PDF·파일명)만, 서버 미저장. 실 PDF/PII 미커밋·작업파일 정리·마운트 git 미실행.

## Next
- **Codex(Windows)**: `npm run build`·tsc(app/node)·lint·실 PDF 본문 "고객명" 표시·로그인 "보험핏" 한 줄 육안·전체 pytest(기준선 375 + 신규 4) → 범위 파일 stage→commit→push. 커밋: `BOHUMFIT-067: 로그인 로고 한 줄 + PDF 고객명 직접 입력·리포트 본문 표시`.
