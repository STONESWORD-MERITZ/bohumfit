# BOHUMFIT-251 — 고지의무 출력 정확성: 코드 원문 유지·수술 건별 전개·동일일자 복수코드

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: Codex (2차 검증·커밋)
Risk tier: ★고위험 — 풀 하네스. git 쓰기 금지(커밋 Codex). backend/pipeline/ 수정 이 태스크 한정
명시 허용. 실 PDF 로컬 참조만·stage 금지. ★PII 엄격(실명 정*규 마스킹·주민/전화/주소 미기재).
Date: 2026-07-27

## 제1원칙
★고지 정확성: 심평원 원문(코드·병명·수술명·날짜·기관명)을 가공 없이 그대로 출력.

## 진행 기록 (Claude Code · 2026-07-27)

### S1 — 진단 (실측)

**① 코드 절삭 = 061 설계된 그룹 키(버그 아님)**: `disclosure_group_code`가 KCD 3자리로
그룹핑(L050→L05)하고 출력 `display_code`가 그 그룹 키를 그대로 노출 — **그룹 키(내부)와
출력 문안 분리가 미비**했던 것. 원문 코드는 어디에도 보존되지 않았음.

**② 수술 붕괴 = 집계 구조**: 수술이 그룹 단위 `surgeries`(이름 set)·`surgery_dates`(날짜
set)로만 평탄화 — 건별(날짜×코드×수술명) 연결이 소실. 문안 생성(disclosureMemo)은 그룹당
1줄 + 수술명 나열이라 기간 묶음처럼 보임.

**③ 동일 일자 복수코드**: 2023-02-05 원문 = **AL050 모소낭 입원 4일 + AK610 항문농양 외래**
두 행 공존(실측). K61 그룹은 생성되나 그 수술·병기가 문안에 연결되지 않았음.

**원문 표기 실측(문안 정본 확정)**:
- 주상병코드 칸 원문 = `AL050`·`AL0292`·`AL0221`·`AK610` — **양방(A)/한방(B) 구분 접두 포함**
  (병명 칸에 "(양방)" 별도 병기 — 접두는 KCD 아님).
- ★배경의 기대 `L02211`은 원문과 다름 — **2022-11-08 원문 = AL0221 "몸통의종기"**(옮김 편차로
  판정·원문이 정본. Human 재확인 항목).
- 병명·병원명·수술명에 PDF 셀 개행 아티팩트 공백: "농 양이있는 모소낭"·"대구파티마병 원"·
  "1시 간초과" — 심평원 화면 원문은 연속 표기.
- 세부진료 행에는 상병코드 칸이 없음(코드명=행위·수술명) — 건별 코드는 동일 일자 기본진료
  행에서 병기.

**205/208 접점**: 투약 배지·집계는 무접촉(표시 필드 추가만 — 판정 수치·창 계산 불변,
smoke에서 med_days 등 전 판정 필드 동일 확인).

### S2 — 수정 (표시 계층 전용 · 판정 로직 불변)

- **A 원문 코드 보존**: `s["raw_codes"]`(원문 수집·절삭 0)·`_raw_code_by_date`·
  `_diag_name_by_date`(날짜별 원문 병명) 신설. 출력 `display_code` = 원문 코드 나열
  (예: `K210·K219`), 내부 `code`(그룹 키)는 061 설계 유지 — 표시·판정 분리.
  표시 시 양·한방 구분 접두만 제거(`display_raw_code` — 병명의 "(양방)" 병기와 중복 정보,
  그 외 문자 무변형). 아티팩트 공백은 한글-한글 사이만 접합(`display_clean_text` — 영문·
  숫자 경계 보존)해 `display_name`·수술 기록 텍스트에 적용(내부 name 필드는 호환 유지).
- **B 수술 건별 전개**: 세부진료 수술 행을 행 단위로 수집(`detail_surgery_rows`) →
  수술 확정일마다 `surgery_records` = {date, code(원문), context(입원N일/통원N회),
  name(그 날짜 원문 병명 — 그룹 대표명 아님), surgery_name(원문), hospital} 목록.
  result_builder가 문항 창으로 필터해 항목에 첨부.
- **C 동일 일자 복수 진단 병기**: 날짜별 전 그룹 (원문코드, 병명) 인덱스에서 자기 코드 외
  진단을 `co_diagnoses`로 병기(예: "K610 항문농양").
- **문안 생성(disclosureMemo.ts — src 최소 정합·사유 기록)**: 수술 항목에 surgery_records가
  있으면 `날짜 / 원문코드 / 맥락 / 병명 / 수술명 / 병원 / 동일일자 진단: …` 건별 줄로 전개,
  없으면 기존 형식 폴백(하위호환). 입원·통원 줄 병명은 display_name 우선.

### S3 — 검증

**정*규 4문서 재실행 대조표(기대 6건 — 마스킹)**:
| 날짜 | 출력(신) | 기대(배경) | 판정 |
| --- | --- | --- | --- |
| 2024-01-07 | L050 / 입원7일 / 농양이있는모소낭 / 모소동수술(절제술)+수술팩(Ⅱ) | L050 모소동수술(절제술) | ✅ (수술팩 병기는 원문 추가 정보) |
| 2023-11-27 | L050 / 통원1회 / 절개술(1cm이상~2cm 미만) | L050 절개술(1cm이상~2cm미만) | ✅ |
| 2023-07-21 | L0292 / 통원1회 / 상세불명의큰종기 / 절개술(1cm미만) | L0292 절개술(1cm미만) | ✅ |
| 2023-03-22 | L050 / 입원6일 / 모소동수술(절제술)+수술팩(Ⅱ) | L050 모소동수술(절제술) | ✅ |
| 2023-02-05 | L050 / 입원4일 / 절개술 / **동일일자 진단: K610 항문농양** | L050 절개술+동일일자 항문농양 | ✅ (③ 해소) |
| 2022-11-08 | **L0221** / 통원1회 / **몸통의종기** / 절개술(1cm미만) | L02211 절개술(1cm미만) | ✅ 원문=AL0221·몸통의종기(기대 표기가 원문과 상이 — 원문 정본, Human 재확인) |
- display_code: L05→**L050**, L02→**L0221·L0292** (절삭 해소 ✅). 병명 "농양이있는모소낭"
  원문 복원 ✅. ※`최근 3개월.pdf`는 비밀번호 파일 — 생년월일 미제공 검증 환경에서 잠금
  (경고 정직 보고·운영에선 생년월일 입력으로 해제. 나머지 3문서로 6건 전부 재현됨).

**기존 심평원 스모크(이*숙 3문서) — HEAD vs 신 코드 항목별 diff**:
- ★판정 필드(visit·med_days·inpatient·surgery_count) 상이 **0** — 판정 로직 불변 증명.
- 문안 변화는 전부 원문 복원(정당·사유 명시): J38→J3848, K21→K210·K219, K29→K291·K297,
  K31→K317, K35→K358, K63→K635, K64→K642, L02→L0281, M25→M2555, N31→N310·N311,
  N71→N710, R10→R100·R1049, R20→R202, I10→I109, K60→K602 + surgery_records 신규 첨부
  (K29 1·K31 3·K35 9·K63 1·K64 2·L02 1건).

## 검증 체크리스트 (1차 — 완료)
- [x] backend pytest — **717 passed, 8 skipped**(712 + 신규 5: test_disclosure_accuracy_251 —
      접두 제거·공백 정리·원문 보존·건별 전개·복수코드 병기. 기존 무손실)
- [x] ★정*규 대조표: 수술 6건 건별 전개·코드 원문·2023-02-05 복수코드 병기 — 위 표(전 건 ✅)
- [x] 기존 스모크 diff 항목별 기록 — 판정 필드 0·원문 복원 변화만(위 목록)
- [x] tsc·lint·npm test **89**(disclosureMemo 최소 정합 포함 — 하위호환 폴백)
- [x] PII grep 0(실명·주민·전화·주소 — 코드·테스트·문서) · pipeline 외 diff = disclosureMemo(사유 기록)만

## Stage 목록 (Codex용 · 3차 갱신)
backend/analyzer.py, backend/main.py,
backend/pipeline/helpers.py·disease_aggregator.py·result_builder.py,
backend/tests/test_disclosure_accuracy_251.py·test_bug012_q2_q3.py,
backend/tests/fixtures/disclosure_memo_parity_251.json,
src/lib/disclosureMemo.ts·disclosureMemo.test.ts·disclosureWindow.ts,
src/pages/Disclosure.tsx,
tasks/BOHUMFIT-251-*.md, handoff.md, locks.md — 실 PDF 제외

## 커밋 메시지 (Codex용)
fix(BOHUMFIT-251): 고지 문안 원문 충실화 — 이벤트 단위 연결·건별 전개·4경로 골든 동등성

---

## 회송 보정 (2026-07-27 · Codex 반려 → Claude Code)

### 반려 원인
수술 기록 연결이 날짜 단일 키 — 동일 날짜 타 병원·타 그룹의 수술이 교차 오염(Codex 합성 실증).

### 연결 규칙 (명문화)
1. **건별 수술 이벤트 = 판정과 동일한 연결**: 파이프라인 판정이 쓰는 detail→basic
   **(날짜 + 병원 정규화)** 링크(`linked_basic`·`basic_by_day_provider`)로 귀속된 그룹의
   `_surgery_row_events`에 행 루프에서 직접 적재 — 날짜 전역 재조인 전면 제거.
2. **동일 (날짜, 병원)에 복수 기본행 공존**(형태 상이 — 입원/외래): 기존 링크 규칙
   (첫 기본행 귀속 — 판정과 동일)을 따르고, 타 진단은 co_diagnoses 병기로 사실성 보존.
3. **링크 불성립 수술행**: 오귀속 대신 `unassigned_surgeries`(그룹 미특정) — analyzer
   페이로드 + 카카오 문안 "[수술 내역(그룹 미특정)]" 블록으로 원문 그대로 출력.
4. **co_diagnoses = 행 단위 (날짜, 병원) 이벤트 인덱스**: 그룹 날짜맵(setdefault 첫 행
   승자)은 같은 그룹의 같은 날 복수 병원 진료 시 (코드,병원) 짝이 어긋남(실측) —
   기본행 자체에서 (날짜,병원)→(원문코드,병명) 인덱스를 직접 적재.
5. 문안 이원화 정합: 백엔드 카카오(_kakao_item — 건별 전개·동일일자 병기·미특정 블록)와
   프런트 disclosureMemo 동일 형식. build_disease_stats는 6-튜플(미특정 추가).

### ★실측 반전 — 2023-02-05 "동일일자 항문농양" 병기의 진실
원문 재실측: 항문농양(AK610) 행의 병원 = **의료법인삼백의료재단상주성모병원** —
대구파티마(모소낭 수술)가 아닌 **타 병원의 별개 진료 이벤트**였다. 1차본의 "동일일자:
K610 병기"가 바로 반려된 날짜-전역 오염의 실사례. **보정 후 미병기가 원문 사실에 부합**
(항문농양은 K61 그룹 항목으로 Q5에 별도 고지 — 누락 0). Human 기대 편차 2건째로 기록
(①L02211 vs 원문 AL0221 ②2023-02-05 병기 기대 vs 원문 타 병원).

### 재현 방법 (Codex 재검증용)
- 실 PDF: `보장분석\` 4문서 중 **최근 3개월 1건만 비밀번호 잠금**(생년월일 — Human 제공
  필요·문서 기재 금지). 나머지 3문서(기본진료·세부진료·약)로 6건 전개 전부 재현 가능.
- 커맨드: `analyzer.run_analysis([기본, 세부, 약], "건강체/표준체 (일반심사)",
  date(2026,7,27), "", "")` → summary_reports에서 L02·L05·K61 항목의
  display_code/raw_codes/surgery_records/co_diagnoses 확인(스크래치 스크립트 1차와 동일 조건).

### 검증 (1차 재실행)
- [x] backend pytest — **720 passed, 8 skipped**(717 + 교차 회귀 3: 교차 병원 오염 0·
      동일 병원 형태 상이 링크·미특정 블록)
- [x] 정*규 대조표 갱신: 6건 건별 유지 · **K61 그룹 records 0(오염 0 명시 단언)** ·
      2023-02-05 co=[](★원문 사실 — 타 병원 이벤트) · 미특정 0(전 건 링크 성립)
- [x] 기존 스모크(이*숙) 판정 필드 상이 **0** 재확인
- [x] tsc·lint·npm test **89** · PII 0 · diff 범위 = 기존 251 선언 + analyzer·main(문안 생성부
      — 이원화 정합 사유)·bug012 테스트 언팩 2건(6-튜플 근거 주석)

### ★추가 검증 — 간편심사(유병자 3-10-5) 문안 경로 (Codex 실측 · 2026-07-27)
- 경로 특정: 결과 기간 **10년**(기본값)은 서버 `easy_kakao` =
  `_build_kakao_message(..., easy_reports)`→`_kakao_item`; 10년 미만 선택은 프런트
  `buildFilteredDisclosureMemo(easy_reports)`→`memoItem`. 별도 레거시 데이터가 아니라 두 경로
  모두 analyzer의 `easy_reports[].surgery_records`를 소비한다.
- 정*규 실 PDF 3문서 재현: 간편 Q2 L02 payload는 `display_code=L0221·L0292`,
  `visit=4`, surgery_records는 `2022-11-08/L0221/통원1회`와
  `2023-07-21/L0292/통원1회` 두 건이다. 서버 간편 문안 `[수술]`에도 두 원문 코드 건별 줄이
  모두 출력돼 251 필드 전달 자체는 통과했다.
- ★잔여 결함: 건별 두 줄 위에 구 그룹 요약
  `통원4회 / L0221·L0292`가 그대로 출력된다. 프런트 `memoItem`도 record 분기 전에 공통
  `line1`을 만들므로 동일 잔여가 정적으로 확인된다. 즉 “L02 통원4회 합산 해소”는 미완이다.
- Code 보정 계약: `surgery_count>0 && surgery_records.length>0 && inpatient==0`인 수술 섹션은
  그룹 합산 line1을 중복 출력하지 않고 건별 record 줄만 출력하도록 서버 `_kakao_item`과
  프런트 `memoItem`을 함께 정합한다. records 없는 구 데이터 폴백과 입원 정보 표시는 보존한다.
  서버 간편 문안 + 프런트 필터형 문안 양쪽 회귀에 “L0221·L0292 각 1줄, 통원4회 합산 줄 0”을
  고정한다.

## 3차 회송 보정 (2026-07-27 · Codex 재반려 3결함 → Claude Code 완료)

### 결함 1 — 같은 그룹·같은 날짜·다른 병원 2수술: 이벤트 값 치환 → 해소
- 원인: 조립부가 record의 code/name/context를 그룹 **날짜 단일 키** 맵
  (`_raw_code_by_date`/`_diag_name_by_date`/`_inpatient_days_map`, setdefault 첫 행 승자)에서
  조회 — 같은 날 타 병원 이벤트가 첫 이벤트 값으로 치환.
- 보정: 행 루프에서 그룹 내 `_evt_by_date_hosp[(날짜, 병원 정규화)]`에 코드·병명·입원일수·
  방문행수를 이벤트 단위로 수집(첫 행 승자는 동일 (날짜,병원) 내로 한정), 조립 시 이벤트 맵
  우선·그룹 날짜맵은 폴백만. record dedup 키도 `(수술명, 병원)`으로 확장.
- 회귀: `test_same_group_same_day_two_hospitals_no_substitution` — X101/통원1회/가나병원과
  X102/입원3일/다라의원이 각자 보존, 교차 co 병기 0.

### 결함 2 — 미특정만 존재 시 카카오 조기 종료 → 해소
- `_build_kakao_message`의 `if not summary_reports: return`을
  `if not summary_reports and not unassigned_surgeries:`로 — 미특정 블록이 조기 return 뒤에
  있어 소실되던 결함. 둘 다 없을 때만 "고지 대상 없음".
- 프런트 `buildFilteredDisclosureMemo`도 동일 규칙: `unassignedSurgeries` 파라미터 신설,
  미특정 블록 출력(창 필터 동일 기준 `dateInWindow`) + "고지 대상 없음"은 양쪽 0일 때만.
  배선: 서버 페이로드에 `unassigned_surgeries` 추가 → `AnalyzeResult` →
  `DisclosureSection` prop → `buildFilteredDisclosureMemo`.
- 회귀: `test_kakao_message_unassigned_only_still_outputs_block` /
  `..._no_target_only_when_both_empty` + vitest 동형 2건.

### 결함 3 — 합산 줄 잔존(건별과 중복) → 해소 (패킷 계약: 진단 요약 줄은 유지)
- 서버 `_kakao_item`·프런트 `memoItem` 동일 규칙: 건별 전개 그룹(records 존재)의 line1에서
  **"통원N회" 방문 합산 제거**, 진단 요약(기간/원문코드/병명)은 유지 —
  `날짜범위 / L0221·L0292 / (양방)병명` 형식. 입원 회차별 줄(periods)은 합산이 아니라 회차
  근거이므로 보존(records와 공존).
- 필터 경로 원인 보강: `filterDisclosureItemEvidenceByWindow`가 `surgery_records`를
  **통과시키지 않아** 창 필터 후 옛 합산 폴백으로 떨어지던 문제 → records를 창 필터하여 통과.
- 정*규 실측(3문서): L02 `[수술]` = 진단 요약 1줄(통원4회 없음) + 건별 2줄(L0221·L0292 각 1건).
  L05 `[입원]` = 회차 3줄 + 건별 6줄, 2023-02-05 co 병기 0(타 병원 — 원문 사실).

### 4경로 전수 정합 + 단일 소스화 실측
- ①서버 std/easy kakao(`_kakao_item`) ②프런트 필터형(`memoItem`) — 동일 규칙 적용 완료.
  ③analyzer 페이로드 — `_serialize_reports`가 `**item` 스프레드로 `surgery_records` 원형 전달
  (실측 확인). ④`disclosureMemo`/`disclosureWindow` — records 창 필터 통과 + 미특정 블록 동형.
- 단일 소스화 판단: 서버(Python)·프런트(TS)는 물리적 단일 소스 불가 → **동일 규칙 + 골든
  동등성 테스트** 채택(211 패리티 원칙). 골든:
  `backend/tests/fixtures/disclosure_memo_parity_251.json` — 서버
  `test_kakao_item_parity_golden`과 프런트 `disclosureMemo.test.ts` "matches the server
  _kakao_item golden"이 **같은 골든**과 문자 단위 대조(형식 변경 시 골든·양쪽 동시 갱신).
- 부수 정합 1건: 서버 line1(입원 회차·폴백)이 `name`을 쓰고 프런트는 `display_name||name`을
  쓰던 1차 잔존 불일치 실측("농 양이있는 모소낭" 공백 아티팩트) → 서버도 display_name 우선.

### 검증 (3차)
- backend `python -m pytest -q`: **726 passed, 8 skipped** (251 테스트 8→14: 3결함 회귀
  5건 + 골든 1건 추가)
- 프런트: `npm test` **95 passed**(89+6: 골든 동등성·합산 중복 0·미특정 블록 2·records 창
  필터 2), `tsc` app/node 통과, `eslint` 클린
- 정*규 3문서 재실행: 판정 필드 불변, L02/L05 건별·이벤트 값 정상(위 실측), 미특정 0건
- 이*숙 3문서 HEAD 대조 스모크: **판정 필드 상이 0** (display_code 원문 복원·records 신규
  필드만 — 전부 정당 변화)
- PII: 산출물·테스트 픽스처 전부 익명 합성(실명 0), 비밀번호 값 기재 0("Human 제공 필요"만)

## Next
① Codex — 3차 재검증(★3결함 중점: 이벤트 치환 0·미특정-only 문안·합산 중복 0 + 4경로
   골든 동등성·정*규 대조·이*숙 스모크·전체 게이트) → 통과 시 커밋·push
② Human — 프로덕션에서 정*규 재분석 → 건강체·간편 문안 육안 검수(이한빈TL 재확인 권장) +
   **재확인 1건**: 2022-11-08 코드 — 심평원 원문 AL0221(몸통의종기) vs 배경 기대 L02211
③ Chat — 205 투약 배지 등 잔여 미결 통합 검토
