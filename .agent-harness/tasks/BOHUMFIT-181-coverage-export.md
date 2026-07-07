# BOHUMFIT-181 — 보장분석 리모델링표 엑셀/PDF 내보내기 (160 마지막)

Owner flow: Claude Chat -> Claude Cowork -> Codex
Current owner: Cowork(구현 완료) -> Codex(Windows tsc/build/pytest·openpyxl 설치·playwright PDF 실렌더·커밋/푸시)

## 배경
179/179b 파서([전]/[최종] 생성)·180 화면(CoverageRemodel) 완료(Codex 752d512 커밋, 구 114비교·엑셀도구 은퇴).
이 태스크는 [전]/[최종] 데이터를 설계사가 고객에게 전달할 엑셀+PDF로 내보내기(백엔드 생성).

## Step 0 — 진단 (완료)
- 179 스키마: `{before:{customer,premium{monthly_total,paid_total},companies[월납desc·remark],coverages[summary,by_company]}, final:{premium,coverages[value,recommended,gap,status],rollup_by_group12}}`.
- 엑셀 라이브러리: openpyxl 3.1.5(샌드박스 존재, requirements 미등재 → **추가함**). xlsxwriter도 있으나 openpyxl 채택(서식/병합).
- PDF: `pipeline/report_pdf.html_to_pdf_bytes(html, doc_no)`(헤드리스 Chromium/playwright) + `build_doc_no`·`_now_kst` **재사용(무수정 import)**. 폰트=시스템 Noto(Railway fonts-noto-cjk). 템플릿(157)과 별개 HTML.
- 파일명: 157 패턴(sanitize + Content-Disposition filename*=UTF-8'').

## Step 1~2 — 생성기 (완료, 신규 격리 모듈)
- `backend/coverage/export_excel.py` — `build_workbook_bytes(analysis)→xlsx bytes`. 시트 2개: "최종 보장진단"(상단 월납합계·총납입 + 담보별 권장/가입/과부족/준비상태 색상), "전 회사별세부"(회사 월납 내림차순 열×담보 + 합산/대표 요약열 + 하단 계약 비고). 13대분류 순서·기타 포함. (Excel 시트명 `[]` 금지 → 대괄호 제거)
- `backend/coverage/export_pdf.py` — `build_coverage_html(analysis)→str`(FIT v1.1: 에메랄드 #084734·잉크 워드마크·ㅍ 심볼·과부족 색상·면책, 구브랜드색 0) + `async generate_coverage_pdf(analysis)→bytes`(html_to_pdf_bytes 재사용). 파싱 재실행 X(데이터 렌더만).

## Step 3 — API (완료)
- `POST /coverage/export/excel`·`POST /coverage/export/pdf` — Body=분석 JSON(before/final), verify_jwt, `_require_analysis` 검증, asyncio.to_thread/wait_for, Content-Disposition 파일명 `BohumFit_보장분석_{별칭}_{YYYYMMDD}.{ext}`(별칭 없으면 "고객", 금지문자 제거), Cache-Control no-store. PII: 프런트가 분석JSON 전달 → 서버 재파싱/저장 없음.

## Step 4 — 프런트 (완료)
- `src/pages/CoverageRemodel.tsx`(180 커밋본) [최종] 헤더에 "엑셀 저장"·"PDF 저장" 세컨더리 버튼 + `exportFile(kind)` 핸들러(result JSON POST→blob 다운로드, Content-Disposition 파일명 파싱). 렌더 로직 무변경(버튼만).

## Step 5 — 테스트 (완료)
- `backend/tests/test_coverage_export_181.py` 4케이스: 엑셀 셀값(573,227·181,984,128·상해사망 5.5억·기타 N대수술비·계피 비고)·PDF HTML(에메랄드·구브랜드0·값·상태)·_fmt_krw·파일명 sanitize(금지문자·기본값). 익명 픽스처.

## 수정 금지 (준수)
- 고지의무 파이프라인 / 157 report_pdf(재사용만) / 179 파서 로직 / CoverageRemodel 렌더 로직(버튼만) / 총납입·집계 산식.

## 검증 체크리스트
- [x] Step 0 진단(스키마·openpyxl·PDF 방식) handoff 기록
- [x] 엑셀 [전]/[최종] 2시트 생성·값 검증(왕복 load_workbook)
- [x] PDF FIT v1.1 브랜드·구브랜드색 0 (HTML 문자열)
- [x] 파일명 규칙·PII 미저장(프런트 JSON 전달·no-store)
- [x] raw gray 0(프런트 버튼) / 전체 pytest는 Codex 권위(기준선 514→ +4 = **518 예상**, npm 15 유지)
- [ ] 실 PDF 기반 엑셀/PDF 실렌더는 Codex 로컬(playwright chromium·보장분석\ 자료)

## Stage 예정 (Codex)
- backend/coverage/export_excel.py·export_pdf.py + backend/main.py(라우터 2종·import) + backend/requirements.txt(openpyxl)
- backend/tests/test_coverage_export_181.py
- src/pages/CoverageRemodel.tsx(다운로드 버튼)
- .agent-harness/tasks/BOHUMFIT-181-coverage-export.md, handoff.md, locks.md
- ★실 PDF·엑셀·PII stage 금지(보장분석/ ignore 유지)

## 커밋 메시지 (Codex)
feat(BOHUMFIT-181): 보장분석 리모델링표 엑셀/PDF 내보내기
