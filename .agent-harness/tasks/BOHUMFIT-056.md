# BOHUMFIT-056 공단 입원일수 파싱 수정 + 수술의심 기준(합산)·문구 + 진료기간 내림차순
## Owner
- Cowork (STEP0 진단 + STEP1~4 구현) → Codex (Windows 전체 검증·PDF 재현·커밋·푸시) → Human (수술의심 임계 확인)

## STEP -1 중단분 정리
- 직전 056 중단은 **코드 변경 없음**(locks.md 활성 잠금만 추가) — `git diff` 056 마커 검색 결과 코드 파일에 056 흔적 0. 055는 HEAD 커밋(e27888f, ec4926b).
- 워킹트리의 기타 더티(analyzer/filters/report_pdf 등)는 **055/이전 작업의 마운트-Windows 분기**(055/056 마커 없음) — Cowork 마운트 git 뮤테이션 금지 + 분기 위험으로 **git restore 미실행**(Codex/Windows 권위 정리).

## STEP 0 진단 (읽기)
- **0-A 입원일수**: `parse_nhis_text` 1줄 정규식이 입내원일수를 비캡처 `\d+`로 버리고, 2줄 "요양(투약)일수"를 `"요양일수"`로 저장 → 집계 `m_days`(get_val ["내원일수","투약일수","요양일수"])가 `"요양일수"` 정확매칭(Pass1) → **입원일수=2줄 요양일수(오류)**. M512 = 요양일수 10으로 표시(정답 입내원일수 2).
- **0-B 수술의심**: `disease_aggregator` nhis 분기 `grade_surgery_suspicion(in_out, cost_val, ...)`. cost_val=`"총진료비"`인데 `_extract_nhis_total_cost`가 **2줄만 스캔 → 본인부담금만**(공단부담금 1줄 누락; docstring "공단+본인"은 사실과 불일치). 임계 INPATIENT_STRONG_COST=50만(입원→강)/OUTPATIENT_WEAK_COST=10만(외래→약). 입원은 이미 후보지만 금액 과소로 누락 가능.
- **0-C 정렬**: 화면(Disclosure.tsx L559)·PDF(report_pdf `_prepare_section` L321)는 **이미 latest_date 내림차순(reverse=True)** 정렬됨. STEP4는 확인만.

## 구현 (STEP1~4)
- **STEP1+2 `pipeline/pdf_parser.py` `parse_nhis_text`**: 1줄 정규식에 입내원일수 캡처 추가 → 레코드 `"내원일수"=입내원일수(1줄)`(get_val Pass1 우선 → 입원일수로 사용), `"투약일수"=요양일수(2줄)`(별도). `"총진료비"=공단부담금(1줄)+본인부담금(2줄) 합산`(수술의심 기준).
- **STEP1 추가 — 페이지 경계 병합**: `parse_single_pdf` nhis 경로가 페이지별 파싱이라 2줄·순번·내역 3줄 세트가 페이지 경계에서 끊겨 **입원 행이 통째로 누락**됐다(M512/K605). 전체 페이지 텍스트를 모아 `parse_nhis_text` 1회 호출로 경계 보존(텍스트만 누적, 페이지 캐시 즉시 flush — 메모리 안전).
- **STEP3 `src/pages/Disclosure.tsx`**: 수술의심 문구 "…실제 수술 여부는 원자료로 확인이 필요합니다." → "**…고객님 확인이 필요합니다.**" (L448). Q2-AI 참고 문구의 "원자료로 확인하세요"도 "고객님 확인이 필요합니다"로 통일(L478, 고객 대면 일관). **PDF엔 수술의심 설명 문장 없음**(칩만) → 변경 불요.
- **STEP4**: 화면·PDF 모두 이미 진료기간(latest_date) 내림차순 — 변경 없음(확인 완료).

## 검증 (실 PDF: 병력 19-20)
- **end-to-end(parse_single_pdf → build_disease_stats)**: **M512 입원 2일**(요양 10 아님)·총진료비 561,190(공단399,690+본인161,500); **K605 입원 3일**·총진료비 1,035,220. M51/K60 `_inpatient_days_map`={2}/{3}, **수술의심 등급='강'**(입원 고액 포함).
- 신규 회귀 `tests/test_nhis_inpatient_days_cost.py`(6): 입원일수=입내원일수·일수/투약 분리·총진료비 합산·입원 고액 강·집계 입원일수2+의심등급·의심≠확정(surgery_dates 미설정). → /tmp **6/6 passed**.
- 기존 `test_nhis_history.py::test_parse_nhis_text_cost_and_period`: 비현실 레이아웃(전액 2줄)을 **실제 양식(공단 1줄+본인 2줄)으로 갱신**, 합산 총진료비(1,200,000/90,000)+내원/투약 분리 단언 추가 — 파서 출력과 일치 확인.
- 비-analyzer/report 회귀: /tmp **221 passed**(+신규 6).
- ⚠ **이번 세션 마운트 view 심각 손상**: analyzer.py·report_pdf.py(056 미접촉) bash-view stale/절단 → 해당 의존 테스트 /tmp 수집 불가(Codex/Windows 권위). pdf_parser.py는 tail/블록 재구성으로 end-to-end 검증.
- 자체 점검: ☑056 흔적0 시작 ☑M512 2일 ☑입원≠투약 ☑수술의심 합산 ☑입원 고액 의심 ☑문구 고객님 확인(화면; PDF 문장 없음) ☑정렬 내림차순(기구현) ☑확정 vs 의심 구분 ☑055/보존분 미접촉 ☑회귀0(가용 범위).

## Notes — Human 확인
- 수술의심 임계는 `nhis_history_constants.py`(범위 외)에 있어 미변경. **합산(=공단+본인, 더 큰 값)** 기준에서 입원 50만 임계는 대부분의 입원을 '강 의심'으로 잡을 수 있음 — 의도(입원 고액 안내)에 부합하나 과검출 여부 Human 확인 권장.

## Next
- **Codex(Windows)**: 전체 pytest(기준선 325 + 신규 6)·tsc/lint/build·실 PDF 재현(M512 2일·수술의심·문구·정렬) → 범위 파일 stage→commit→push. 커밋: `BOHUMFIT-056: 공단 입원일수(입내원일수) 파싱·총진료비 공단+본인 합산·페이지경계 병합 + 수술의심 문구 고객님 확인`.
- **Human**: 수술의심 합산 임계(50만) 과검출 여부 확인.
