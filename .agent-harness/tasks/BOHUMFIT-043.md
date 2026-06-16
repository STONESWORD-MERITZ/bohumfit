# BOHUMFIT-043 040 롤백 + 약국 기관명 기반 통원 제외
## Owner
- Cowork (구현+회귀) → Codex (Windows 검증·git)

## 확정 사양
- BOHUMFIT-040(`_keep_basic_general_row → return False`)의 진단과='일반의' 행 전체 skip을 **전면 롤백**.
- 일반의 제외 로직 삭제 — 일반의 행도 통원·입원·수술·투약·detail 링크 모두 정상 작동.
- 통원(visit_dates) 제외는 **요양기관명에 '약국' 포함 시에만** 적용(행 자체는 보존).

## 구현 (완료)
- `backend/pipeline/helpers.py`: `_keep_basic_general_row` 함수 **전체 제거**(040의 `return False` 폐지).
- `backend/pipeline/disease_aggregator.py`:
  - import에서 `_keep_basic_general_row` 제거.
  - Loop1(L226, basic_by_day_provider 인덱스): 040 일반의 게이트 제거 → detail-link 인덱스 보존.
  - Loop2(L272, 메인 집계): 040 일반의 게이트(+`dept` 미사용 변수) 제거 → 행 보존(입원·수술·투약·detail 정상).
  - 통원 분기(L338, `else:` visit_dates.add 직전): `if "약국" not in _norm_provider_name(hospital):` 가드로 약국 기관명만 통원 제외. inpatient(L330)·med_dates_basic(L344)·detail-link·pharma cross-ref 경로는 가드 밖이라 불변.
  - Loop3(L622, 2차 패스)의 `if dept=="일반의": continue`는 **pre-040 베이스라인**(040 무관·`_keep` 비참조)이라 범위 외 — 유지.
- tests:
  - `test_history_filter_fix.py`: 040 `test_general_dept_excluded`(미집계) → `test_general_dept_kept`(통원 정상 집계)로 롤백.
  - `test_general_dept_exclude.py`: 040 통원 제외 테스트를 043 동작으로 **전면 재작성**(8건).

## 검증
- /tmp pytest **244 passed**(신규 8 포함, 회귀 0). 신규 8 + test_history 6 단독 = **14 passed**.
- 신규 회귀 6+건: ①일반의+유효코드→통원 집계 ②일반의+입원→inpatient ③일반의+detail수술→surgery ④일반의+pharma→투약 부착 ⑤기관명='약국약국'→visit 미집계 ⑥기관명='내과의원'→visit 집계 +⑦약국기관명 입원 보존 ⑧결정성.
- ⚠ 마운트 view 손상으로 /tmp 제외(Windows 정상→Codex): `test_filters.py`(NUL), `test_report_pdf.py`·`test_report_pdf_q1q5.py`(파싱 손상·Chromium), `test_main_launch_guardrails.py`(sentry env), `test_analyzer_integration.py`(analyzer.py 마운트 스크램블 — `compute_prescription_end_dates` None 언팩, 본 변경 무관).
- helpers.py·disease_aggregator.py는 마운트 손상을 Edit 쓰기백 갱신·/tmp 재구성으로 복구해 검증.
- Codex(Windows): 전체 pytest(손상 파일 포함, 기준선 279)·tsc/lint/test/build.

## 작업 범위
- helpers.py·disease_aggregator.py·tests(history_filter_fix·general_dept_exclude). filters/result_builder/간편/투약/입원 판정 로직·프런트 불변. 040 외 030~042 불변.
