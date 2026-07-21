# BOHUMFIT-236 — 보장분석 표시 개선 + 수동 담보 입력 (Human 결정 확정본)

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: Codex (1차 검증 완료 — 2차 검증·커밋 대기)
Risk tier: 중위험 — 풀 하네스. git 쓰기 금지(커밋 Codex). 실 PDF 로컬 참조만·stage 금지.
Date: 2026-07-21

※ PII: 고객명 마스킹(케이스 A=임*효, B=이*숙, C=이*연, D=지*주). 실 PDF는 `보장분석/비교분석표/` 로컬 전용.

## S0 — 실측 (완료)

- 납입완료 판별: 234 ⑧ 실측 재사용 — A 케이스 KB 원본 헤더 월납합 2,282,564 = 전체 2,835,744 − 완료 4계약 553,180(KB 산식). 판별식 = 일시납 즉시 완료 / 월납·연납은 `contract_date + pay_months` 경과.
- 정렬 버그 위치: `aggregator._company_sort_key`(보험사 가나다 + **str(idx) 사전식**), `compare._sort_contracts`, 프런트 `sortCompanies` — 3곳 동일 계열. B 케이스(15계약, 보험사 미검출 시 "1,10,11,…,2" 노출)가 사례.
- 헤더 혼입 원인: excel `_sheet_before` `f"{insurer} {idx}"`(export_excel.py:291-구), pdf ⑤ 헤더 동일 패턴 — "라이나생명 15" 사례의 정확한 위치.
- F 재검증(우선): 234 수정 후 A c4 = 계약 행 존재·보험사 "라이나(에이스)손보"·월납 37,200원 ✓. 단 담보가 종수술비 1라벨만 — 원문 상세 4건 중 "일반상해 80％이상 후유장해"(1,000만)·"상해중환자실입원일당"(20만)이 기준담보·EXTRA 어디에도 없어 미분류 확인 → 같은 범위 내 패턴 추가로 해소(아래).

## 구현 (A~F)

- **A 납입완료 병기**: aggregator에 `_is_paid_up`·`_pay_end_date` 신설, 계약별 `paid_up` 필드 + `premium.monthly_total_active`(부값). 화면 ② 헤더 병기("월납 합계 N원 / 납입완료 제외 시 M원" — 같으면 부값 생략)·카드 "납입완료" 배지, PDF ② premium-note+배지 칩, 엑셀 ② A2 병기+비고 "납입완료" 병기. 원 금액 표기는 유지. 총납입 현행 유지.
- **B 정렬·헤더**: 계약 번호 숫자 오름차순으로 3곳 통일(aggregator·compare `_sort_contracts`·프런트 `sortCompanies` — 신규제안 P* 등 비숫자 idx는 뒤로). 매트릭스 헤더 "계약 N" 통일(excel·pdf·화면 ⑤ — 회사명 혼입 제거). PDF th nowrap+셀 세로중앙, 화면 헤더 whitespace-nowrap.
- **C 방향 토글**: 화면 ⑤에 계약=열(기본)/계약=행 토글. 행 모드는 계약별 블록(계약 N·보험사·월보험료·납만기·계피 + 가입 담보 세로 목록) — 15계약 세로 대응. PDF는 기본 방향 고정, 엑셀 시트 구조 무변경(스펙 준수).
- **D 계피·납만기**: ② 카드에 계피 표기(상이 amber 강조), ⑤ 열 모드 헤더 3행째(N년납·만기·계피), 행 모드 블록 헤더 포함. 엑셀·PDF ② 표는 기존 납입기간·만기·비고(계피) 컬럼으로 충족.
- **E 수동 담보**: `src/lib/coverageManualRiders.ts` 신설(순수 병합 함수 — 원본 불변·"(수동[·계약 N])" 구분 표시명·manual 필드). ④ 하단 입력 UI(담보명·13분류 select=GROUP_ORDER·가입금액·소속 계약 select·추가/삭제). 화면 표·대분류 합계·엑셀/PDF payload 모두 병합본(`displayComparison`) 사용 — 백엔드 `ensure_comparison`은 제공된 comparison 통과(compare.py:411 실측). 세션 상태만(서버 저장 0). constants에 `2대주요치료` 패턴 등록(라벨 "2대주요치료비(뇌·심)"·N대 선순위 — 자동 분류).
- **F 보강**: `중환자실\S*일당`→"중환자실 입원일당"(그룹 입원(간병 포함)), `80[%％]이상\S*후유장해`→"80%이상 후유장해"(그룹 후유장해) 패턴 추가 — A c4 담보 4건 전부 가시화(80%이상 후유장해 1,000만·종수술비 2,000만(2건 합산)·중환자실 입원일당 20만). 234 로직 재변경 없음(additive 패턴만).

### 스펙 밖 인접 수정 1건 (사유 기록)

- compare.py·consulting.py의 **after 경로 premium 재구성에 234의 일시납 제외가 빠져 있던 잠재 결함**을 함께 보정(+`monthly_total_active` 병기). 사유: 병기 값의 전/후 일관성과 parity(211) 유지에 필수 — 방치 시 after 월납에 일시납 혼입. 프런트 캐시(buildAfterResult)도 동일 규칙으로 동시 수정(display-cache 헌장 준수: 백엔드·parity 동시 갱신).

### 기존 테스트 갱신(전부 Human 결정 B·A 파급 — 사유 주석화)

- 179 `test_companies_sorted_by_insurer_name` → `..._by_contract_number`(숫자 정렬), 184 2건(행 위치·회사명), 186 1건은 코드 보정(consulting premium)으로 자연 해소, parity 픽스처 순서 1줄(양측 동일 규칙).

## 실 PDF 4건 재실행 (병기 부값 = KB 헤더 대조)

| 케이스 | monthly_total(주값) | monthly_total_active(부값) | KB 헤더 대조 | paid_up | 정렬 |
| --- | --- | --- | --- | --- | --- |
| A | 2,835,744 | **2,282,564** | **정확 일치** | 2·6·8·9 | 1~9 숫자순 ✓ |
| B | 681,312 | 681,312(완료 월납 없음 — 부값 생략 표시) | 주값 정확 일치(234) | 4·5(일시납 배지) | 1~15 숫자순 ✓ |
| C | 183,621 | 183,621(동일 — 생략) | (헤더 대조 항목 Codex 2차) | 없음 | 1~3 ✓ |
| D | 763,089 | 495,389(완료 5·6 제외) | (헤더 대조 항목 Codex 2차) | 5·6 | 1~10 ✓ |

- **F 결과 명시**: A c4 = 라이나(에이스)손보·37,200원·담보 4건 전부 반영(80%이상 후유장해 1,000만 / 종수술비 2,000만 / 중환자실 입원일당 20만) — 누락 해소.

## 검증 체크리스트 (1차 — Code, 2026-07-21 결과)

- [x] backend pytest — **650 passed, 8 skipped** (기준선 643 + 신규 7. 정렬·premium 파급 4건은 위 사유로 갱신)
- [x] tsc app/node · lint · npm test **77 passed**(73+4) · build 통과(청크 343.22 kB — 기록만)
- [x] 실 PDF 4건 재실행 — 위 표. A 부값 = KB 헤더 정확 일치, F 결과 명시
- [x] PII grep 0(4인 실명 — 코드·테스트·문서), diff 범위 = coverage(aggregator·constants·compare·consulting·export 2종)·CoverageRemodel·lib 2파일·테스트(신규 2·갱신 4) + harness만

## Stage 목록 (Codex용)

backend/coverage/{aggregator,constants,compare,consulting,export_excel,export_pdf}.py,
backend/tests/{test_coverage_display_236.py(신규), test_coverage_parser_179.py, test_coverage_contract_list_184.py},
src/pages/CoverageRemodel.tsx, src/lib/{coverageAfterDisplayCache.ts, coverageAfterDisplayCache.test.ts,
coverageManualRiders.ts(신규), coverageManualRiders.test.ts(신규)},
tasks/BOHUMFIT-236-*.md, handoff.md, locks.md — 실 PDF·보장분석/ 절대 제외

## 커밋 메시지 (Codex용)

feat(BOHUMFIT-236): 보장분석 표시 개선 — 납입완료 병기·정렬·방향토글·계피/납만기·수동담보
