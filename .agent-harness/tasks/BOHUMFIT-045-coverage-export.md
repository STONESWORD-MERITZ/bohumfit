# BOHUMFIT-045 보장분석 결과 엑셀(.xlsx) 내보내기

## Owner
Cowork(Claude) — 구현 1차. 검증·커밋·푸시는 Codex(Windows), 엑셀 실제 열람은 Human.

## 전제
- 041~044로 전 비분표·후 비분표·최종비교분석표 데이터 구조 확정(머지 a1f4098).
- xlsx(SheetJS) 0.18.5는 042에서 dynamic import로 이미 도입 — 의존성 추가 불필요.
- **산식·집계 재계산 금지** — 화면의 041 집계값(전/후 columns·totals, 최종표 매핑)을 직렬화만.

## 범위 (In)
- `src/lib/coverageExport.ts`(신규) — 워크북 빌더 + 다운로드. FINAL_ROWS/KEY_DISEASES/numOf/flagOf/dir 중앙화(044 표시 로직 단일 소스).
- `src/components/coverage/FinalComparison.tsx`(편집) — FINAL_ROWS 등은 coverageExport에서 import, memo prop화, 045 예고 자리를 '엑셀 다운로드' Button으로 교체.
- `src/components/coverage/CoverageAfterSection.tsx`(편집) — beforeColumns prop 추가, memo lift, export 호출 핸들러.
- `src/pages/CoverageAnalysis.tsx`(소형 편집) — beforeColumns={displayColumns} 전달.

## 시트 구성 (3시트)
- 시트1 `비교분석표`(전): 계약 열(회사/상품/가입일/납만기) + 표준 36행 + 합계 열. CoverageTableView 레이아웃 기준(표준 양식 xlsx는 repo 부재 → 042가 양식에서 도출한 화면 레이아웃을 기준으로 사용. handoff 명시).
- 시트2 `비교분석표(후)`: 후 비분표(유지+신규), 동일 36행. (전/후 좌우 한 시트 양식 파일이 repo에 없어 시트 분리.)
- 시트3 `최종비교분석표`: 전|주요보장|후 37행 + 핵심질병 전→후 6행 + 특이사항(memo).

## 양식 정합 / 044 표시 로직 동일
- 상해사망 = injury_death + disaster_death 합산(재해 손실 방지) — FINAL_ROWS 그대로.
- 암입원·일반입원 = 표시 전용 행(값 없음, 주석). 질병입원에 "암입원 포함".
- 숫자 셀은 number 타입(문자열 금지), 금액 단위 만원(보험료만 원). flag는 "Y"/"".

## 내보내기 방식
- xlsx dynamic import(`await import("xlsx")`, 042 패턴). 브라우저 내 생성·다운로드(서버 미전송·비저장).
- 파일명 `보험핏_보장분석_YYYYMMDD.xlsx`(한글). 핸들러는 세션 내 데이터만 직렬화.

## UI
- 최종표 하단 Mercury Button '엑셀 다운로드 (.xlsx)'(045 예고 자리 대체). 후 비분표 데이터 있을 때만 노출(hasAfterData).
- 비저장 안내 유지.

## 범위 밖 (Out)
- 041 lib 카테고리 확장(암입원 신설). 표준 양식 픽셀 정합(셀 병합·서식)은 최소(값·행순서 우선). 다른 페이지/실손/고지.

## ENV
- 신규 lib 우선, 컴포넌트는 소형 편집. 마운트 git 금지, 검증 /tmp, 실데이터 금지(익명 합성).

## 검증
- /tmp: strict tsc(신규 lib + 의존) + buildSheets 단위테스트(시트 수·헤더·합계 셀·number 타입) + 실제 .xlsx 1건 생성 후 재읽기 검증.
- Codex(Windows): tsc(app/node)·lint·test·build + /coverage 다운로드 스모크.

## 산출 기록
- handoff: 시트 구성·파일명·dynamic import·양식 정합(표준 xlsx 부재 가정). Next: Codex → Human(엑셀 열람) → (백로그) lib 암입원 카테고리.
