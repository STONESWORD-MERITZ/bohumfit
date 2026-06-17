# BOHUMFIT-053 PDF 비번 8/6자리 자동 해제 + 업로드 개수 점검 + 10파일 자체 분석
## Owner
- Cowork (STEP1/2 구현 + STEP3 진단) → Codex (Windows 검증·커밋) → Human (자동차 포함·개수 상향 승인)

## STEP 1 — 비번 8/6자리 자동 해제 (구현)
- **현황**: `pipeline/pdf_parser.py _open_pdf` 에 8/6자리 후보 로직이 **이미 존재**(빈값·입력값·숫자만·8→6(YYMMDD)·6→8). 즉 핵심은 구현돼 있었음.
- **053 변경**: 후보 생성을 테스트 가능한 `_pw_candidates()` 로 추출 + `import logging`·logger 추가 + 해제 성공 시 **자리수만 로깅**(`pw_len=N`, PII 값 미기록). 동작 동일·견고화.
- **실증(STEP3 실 파일)**: bd="19950222"(8자리) 입력 1개로 10파일 전부 해제 — 5~10년 공단 파일(16-17·17-18)은 **pw_len=6 자동 재시도로 해제**, 그 외 pw_len=8 또는 0(비번 불요). 8자리만 입력해도 6자리 PDF 자동 해제 확인.
- 회귀: `tests/test_pdf_pw_candidates.py`(6) — 8→6포함·6→8보강·하이픈정규화·빈값·중복제거·순서.

## STEP 2 — 업로드 개수 (구현)
- `backend/main.py` `MAX_FILE_COUNT` 6→**10**. `src/pages/Disclosure.tsx` `MAX_FILE_COUNT` 6→**10**.
- `MAX_FILE_SIZE` 15MB·`MAX_TOTAL_SIZE` 40MB 유지(10개×소형 PDF 충분 — 실 10파일 합 ~1.4MB).
- ⚠ **경고**: 순차 파싱(OOM 핫픽스)으로 메모리 피크는 1파일분 유지되나, 대용량(다페이지) PDF가 10개면 총 파싱시간이 `ANALYZE_TIMEOUT_SECONDS=300s` 에 근접 가능. 실 10파일은 합 ~30s로 여유. 운영서 초대용량 다수 업로드 시 모니터링 필요.

## STEP 3 — 10파일 자체 분석 (읽기 전용, ref=2026-06-17, bd=19950222)
- **파일별 파싱(전부 성공)**: 16-17(nhis 15)·17-18(nhis 11)·18-19(nhis 2)·19-20(nhis 22)·20-21(nhis 6)·기본진료(basic 38)·기본진료_자동차(basic 2)·세부진료(detail 171)·세부진료_자동차(detail 57)·처방진료(pharma 129). 총 453행, 질병그룹 110.
- **건강체/표준체 고지대상**:
  · Q3(5년 입원·수술·통원7·투약30): **K21**(수술·통원1·투약5), **L90**(수술·통원1·투약7).
  · Q4(5~10년 입원·수술): **M51 입원**(추간판전위), **K60 입원**(항문루), **K01 수술의심**(매복 제3대구치), **K63 수술의심**(결장 폴립).
  · Q2·Q5: 해당 없음.
- **간편심사(3-10-5) 고지대상**:
  · 2번(10년 입원·수술): **K21 수술·L90 수술·M51 입원·K60 입원**.
  · 1번(3개월)·3번(5년 6대질환): 해당 없음.
- **자동차 파일 방침(Human 확정=포함)**: `_자동차` 2파일 ftype 정상(기본=basic 2·세부=detail 57). 일반 진료와 동일 집계 대상.
- **중복 점검**: 공단(nhis) 입원일자 vs 심평원(basic) 입원일자 **중복 0**. 집계 키(KCD3 그룹·inpatient_admissions((일자,기관))·_pharma_seen) 정상 — 자동차/공단/심평원 중복 집계 징후 없음.

## 검증
- /tmp pytest **305 passed**(신규 6 포함, 회귀 0; `test_main_launch_guardrails`만 sandbox app-import 제외 → Codex). 기준선 051 후 +6.
- ⚠ 프런트(`Disclosure.tsx`) tsc/build 는 sandbox 불가 → Codex. pdf_parser/filters 마운트 view 절단은 tail 재구성으로 검증.
- 자체 점검: ☑8자리→8자리 PDF 해제 ☑8자리→6자리 PDF 자동 재시도 해제 ☑6자리 직접 입력 동작 ☑비번 불요 PDF 안깨짐 ☑개수 6→10 ☑10파일 분석 정리 ☑자동차 방침 명시 ☑분석 로직 무변경 ☑회귀0.

## 작업 범위
- `pipeline/pdf_parser.py`(_pw_candidates 추출·로깅)·`main.py`(MAX_FILE_COUNT 10)·`Disclosure.tsx`(MAX_FILE_COUNT 10)·신규 `tests/test_pdf_pw_candidates.py`. 분석 로직(filters/aggregator/result_builder) 무변경.

## Next
- **Codex(Windows)**: 전체 pytest·tsc/lint/test/build → 범위 파일 커밋·푸시. 커밋: `BOHUMFIT-053: PDF 비번 8/6 자동해제 로깅·테스트 + 업로드 개수 6→10`.
- **Human**: ① 자동차 진료 고지 포함(확정됨, 재확인) ② 업로드 개수 10 상향·타임아웃/메모리 영향 승인.
