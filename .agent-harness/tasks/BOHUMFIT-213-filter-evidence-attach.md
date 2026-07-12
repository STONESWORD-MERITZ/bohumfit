# BOHUMFIT-213 고지 필터 결과에 원본 근거(진료일·병원·상병) 부착 — 설계사 추적성

Owner flow: Claude Chat -> Cowork(구현·/tmp 검증) -> Codex(Windows 권위 검증·커밋·푸시)
Current owner: Human

## Intent

필터 결과가 "입원 (4일)"처럼 일수만 표기해 설계사가 원본 PDF를 다시 뒤지는 병목 제거.
모든 결과 항목에 "언제·어디서"(진료시작일·병의원명, 상병은 카드 자체) 근거를 부착한다.
★판정 로직·임계·5년/10년 창 계산은 무변경 — 표시 근거만 추가.

## S0 결론

- 요약 문자열("N년이내 입원 (M일)")은 `filters.py` 각 룰의 `reason=` → result_builder `detail` 필드.
- 원본 근거는 이미 disease_stats에 보존됨(유실 아님): `inpatient_periods`(205), `hospital_dates`(날짜→병의원),
  `visit_events`, `med_dates_pharma_episode`(날짜→병원→일수), `surgery_dates`. 다만 **병의원이 회차·근거 단위로
  결과 item에 실리지 않았고**, 205의 회차 표기는 복사문·카드 입원기간 줄에만 반영(요약 detail 라인·통원/투약/수술 근거는 미반영)이었다.

## Changed (구현)

- `backend/pipeline/disease_aggregator.py`: inpatient_periods 항목에 `hospital` 추가(기본진료·NHIS 2개 지점, 표시용).
- `backend/pipeline/helpers.py`: `_inpatient_periods_in_range` 회차 dedup 시 병원 보존(빈값↔비어있지 않은 값 병합).
- `backend/pipeline/result_builder.py`: 표시용 근거 3종 신설(각 지표와 동일 원천·동일 창, 상한 100건) —
  `visit_records[{date,hospital,count}]`, `med_records[{date,days,hospital}]`, `surgery_events[{date,hospital}]`.
- `backend/main.py`: `_kakao_item` 입원 회차 줄 끝에 ` / 병의원명`(없으면 기존 형식), 폴백 한 줄에 `병원 외 N곳` 요약.
- `backend/templates/report_disclosure.html`: 항목 카드에 입원/수술/통원/투약 근거 블록(`.evid`, 유형별 6~8건+외 N건,
  기존 브랜드 변수만 사용).
- `src/pages/Disclosure.tsx`: 입원기간 줄에 병원명, 칩 아래 "근거 상세 보기(N건)" 접이식 섹션(수술/통원/투약,
  그룹별 max-h 스크롤, 기본 접힘 — 과밀 방지), SummaryItem 타입 확장.
- `backend/tests/test_evidence_213.py` 신규(8): 회차 병원 보존·dedup 백필, 간편 Q2 회차 근거+판정 불변(23일/3회/detail),
  병원 무정보 시 판정 동일, Q3 통원(중복 행 count)·투약 근거=판정 정합, 복사문 병원 표기/무병원 하위호환/통원 요약.
- `backend/tests/test_analyzer_snapshot.py`: periods 완전일치 어서션에 hospital:"" 반영(날짜 계약 불변) — 1건 정합.

## 하지 않은 것 (범위 밖)

- 판정 로직·임계·창 계산 변경 없음(filters.py 무접촉). coverage·DB·auth 무접촉.
- 병의원명 내부 공백 정규화(원본 PDF 셀 줄바꿈 유래, 예: "충북대학교병 원") — 기존 hospitals 필드와 동일 특성, 후속 검토.

## Verification (Cowork /tmp — Windows 권위는 Codex)

- 신규: `pytest tests/test_evidence_213.py -vv` → 8 passed.
- 전체(87파일 4청크): **604 passed, 12 skipped, 0 failed** (기준선 600+신규 8=608 예상 대비 4건은 샌드박스 환경 skip
  → Windows 기대 `608 passed, 8 skipped`).
- 실 PDF 스모크(이미숙님 2종, 메모리): 간편 Q2 입원 4건 전부 회차별 날짜·일수·병의원 표기
  (충북대학교병원/인화재단한국병원/창문연합의원), E78 투약 210일의 근거 3건(30/90/90일·병원) 정합,
  복사문 입원 줄 병원 표기, **판정 대상 코드 집합 변경 전후 동일**(간편 G44·G45·K35·K64·L02).
  ※ 석지원님 실 PDF는 Windows 로컬 — Codex 스모크: 입원 4일=2025-08-03·9일=2024-10-07·10일=2022-12-19가
  각 병원명과 함께 표기되는지 확인(합성 동형 케이스는 test_evidence_213이 고정).
- 마운트 truncation 다수 실측(전부 Windows 원본 정상, /tmp는 Read 재조립): helpers/result_builder/disease_aggregator/
  main/report_disclosure.html/export_excel.py/test_usage_middleware/test_drug_change_205/test_coverage_report_191/
  test_analyzer_snapshot — **py_compile 통과형·mid-token(NameError 'w'·'wit') 절단 포함**. Codex는 Windows 원본 기준 검증.

## Codex 게이트

- `git status --short -uall` → 범위 파일만 stage(실 PDF·PII 제외).
- tsc app/node, `npm run lint`, `npm test`, `npm run build`, backend `pytest -q`(608/8 예상), 213 -vv.
- 리포트 PDF 렌더 스모크(합성): 근거 블록 표기·과밀·페이지 넘침 확인.
- 석지원님 실 PDF 스모크(위). 통과 시 커밋:
  `feat(BOHUMFIT-213): 고지 필터 결과에 원본 근거(진료일·병원·상병) 부착 — 설계사 추적성` → push.
- verify.md·CLAUDE.md 기준선 600→608 갱신.

## Codex Windows Result

- Windows 원본 기준 절단 검증 완료:
  - `python -m py_compile backend\main.py backend\pipeline\helpers.py backend\pipeline\result_builder.py backend\pipeline\disease_aggregator.py backend\tests\test_usage_middleware.py backend\tests\test_analyzer_snapshot.py backend\tests\test_evidence_213.py` 통과.
  - tsc app/node 통과. 마운트 중간 절단 잔재·중복으로 인한 Windows 원본 오류 없음.
- 실 PDF 스모크 중 보강:
  - 석지원 3종(기본·세부·처방)에서는 `disease_stats`가 `S83|YYYY-MM-DD` 분할키로 보존되고 결과 item은 대표 코드 `S83`로 병합되어, 최초 구현만으로는 회차 근거가 결과 item/PDF까지 올라오지 않았다.
  - `backend/pipeline/result_builder.py`에 대표 코드 기준 표시용 병합 helper를 추가했다. 판정 룰·임계·창은 그대로 두고, 결과 표시 근거만 같은 대표 코드의 분할 통계에서 합친다.
  - `test_evidence_213.py` 기존 8개 테스트 수를 유지하면서 분할키 동형 회귀를 포함했다.
- 석지원 실 PDF 스모크(실 PDF 미저장·미스테이지):
  - 3종 파싱: `{'basic': 68, 'pharma': 181, 'detail': 770}`, parse_errors 0.
  - 회차 근거: `2022-12-19~2022-12-28 10일 충남대학교병 원`, `2024-10-07~2024-10-15 9일 가톨릭병원`, `2025-08-03~2025-08-06 4일 가톨릭병원`.
  - 결과 item, 복사문, 리포트 HTML, 임시 렌더 PDF 모두 해당 날짜·병원 근거 포함 확인. 임시 PDF 삭제 완료.
  - Human note: 사용자 지시의 `2023-06-16~2023-06-19 · 인화재단한국병원`은 현재 Windows 로컬 석지원 3종 실측값과 다름. 해당 값은 다른 실 PDF(예: 이미숙류) 실측값으로 보이며, 현재 석지원 파일 기준 4일 입원은 `2025-08-03~2025-08-06 · 가톨릭병원`.

## Codex Windows Verified

- `npx tsc -p tsconfig.app.json --noEmit` — passed.
- `npx tsc -p tsconfig.node.json --noEmit` — passed.
- `npm run lint` — passed.
- `npm test` — `7` files, `25 passed`.
- `npm run build` — passed, 기존 Vite 500kB chunk warning만 발생.
- `cd backend && python -m pytest tests/test_evidence_213.py -vv` — `8 passed`.
- `cd backend && python -m pytest tests/test_kakao_inpatient_205.py tests/test_drug_change_205.py tests/test_evidence_213.py -vv` — `28 passed`.
- `cd backend && python -m pytest -q` — `608 passed, 8 skipped`.
