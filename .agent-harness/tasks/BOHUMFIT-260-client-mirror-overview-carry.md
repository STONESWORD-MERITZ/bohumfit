# BOHUMFIT-260 — 클라이언트 미러 overview 이월 동기화 (259 잔여)

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: Codex (2차 검증·커밋)
Risk tier: 저위험 — 풀 하네스. git 쓰기 금지(커밋 Codex). 실 PDF·엑셀 로컬 참조만·stage 금지.
Date: 2026-07-30 · 기준 HEAD `17c05ad`

## 배경
서버 `carry_coverage_row`는 259로 overview 귀속 행을 회사별 이월하나, 클라이언트 미러
`buildAfterResult`는 여전히 합계 이월. 화면 내보내기가 클라이언트 `afterResult`를 POST하므로
★화면에서 해지 후 다운로드 시 `[후]` 회사 열이 합계로 남음(254 `yn_flags`와 동종 결함).

## S0 실측 — 서버 대비 차이 ★2건
| 지점 | 서버(259) | 클라이언트(HEAD) | 영향 |
| --- | --- | --- | --- |
| 이월 분기 | `overview` **이면서 by_company가 빈 행만** 합계 이월, 귀속 행은 일반 경로(keep/cancel 필터 + `'?'` 이월 + 재집계) | `if (coverage.overview)` — **무조건** 합계 이월 | 화면 해지 시 `[후]` overview가 `[전]` 합계로 고정 |
| 해지 경고 | `overview_rows_need_cancel_warning()` — **미귀속 행이 있을 때만** | `coverages.some(c => c.overview)` — overview가 있으면 무조건 | 귀속 문서에서 **사실과 다른 경고** 노출 |
- 그 외(일반 행 필터·`'?'` 이월·제안 병합·재집계·null 셀 유지)는 이미 서버와 동일 — 이번 변경
  대상 아님.

## 구현 (프런트 동기화만 · 서버 무접촉)
- `isAttributedRow(coverage)` 헬퍼 신설 — `by_company`에 실제 값이 하나라도 있으면 귀속 행
  (서버 `carry_coverage_row`(249 정본·259 확장)와 동일 판정).
- 이월 분기: `if (coverage.overview)` → **`if (coverage.overview && !isAttributedRow(coverage))`**.
  귀속 행은 아래 일반 경로로 떨어져 해지가 회사 단위로 반영된다(`overview` 표식은 스프레드로 보존).
- 해지 경고: 조건을 `coverage.overview && !isAttributedRow(coverage)`로 좁힘(서버와 동일 조건·문구).

## ★서버·프런트 동등성 고정 (251 골든 픽스처 선례)
- 공유 골든 `backend/tests/fixtures/overview_carry_parity_260.json` 신설 — 귀속 overview·
  미귀속 overview·`'?'` 혼재 행·일반 행을 모두 포함하고 해지 **0/1/3(전부)** 시나리오의
  `by_company`·`summary`·`enrolled`·해지 경고 유무를 명시.
- 같은 골든을 **양쪽이 대조**한다: `backend/tests/test_overview_carry_parity_260.py`(서버
  `build_after_analysis`) · `src/lib/coverageAfterDisplayCache.test.ts`(클라이언트
  `buildAfterResult`). 규칙 변경 시 골든·양쪽 테스트를 함께 갱신한다.
- 골든이 판정 분기를 모두 덮는지 자체 검사하는 테스트도 포함(커버리지 누락 방지).

## 검증 체크리스트 (1차 — 완료 · 2026-07-30)
- [x] backend pytest **784 passed, 8 skipped**(782 + 260 골든 2) · npm test **99 passed**
      (95 + 260 클라이언트 4) · tsc app/node · lint 클린
- [x] ★**실데이터 서버↔클라이언트 동등성**(overview 정본 문서, 해지 **0/1/3건**):
      담보별 `by_company`·`summary`·`enrolled`·`cautions`가 **전 항목 완전 일치**.
      overview 합계도 서버와 동일 — 해지 0 **1,400,240,000** / 해지 1건 **1,290,640,000**
      (★감소분 **109,600,000** = 계약1의 실손 4종+3대비급여 — 259 서버 결과 재현) /
      해지 3건 **1,097,640,000**.
      ※실데이터 대조는 스크래치 임시 JSON + 임시 테스트로 수행하고 **검증 직후 삭제**(레포에 실데이터 0).
- [x] 표준 문서 무영향 — 서버 payload HEAD 대비 diff 0(담보·분류·회사합·월납·[후]·경고),
      overview 귀속 26/26·합계·총액 HEAD 동일(server gate 재현)
- [x] 서버 무접촉 확인 — `backend/coverage/*.py` diff 0(신규 픽스처·테스트 파일만 추가)
- [x] PII 0(골든 익명 합성·실데이터 산출물 미보존) · diff 범위 =
      `src/lib/coverageAfterDisplayCache.ts`·동 테스트 + 서버 골든 픽스처/테스트 + harness

## Stage 목록 (Codex용)
src/lib/coverageAfterDisplayCache.ts·coverageAfterDisplayCache.test.ts,
backend/tests/fixtures/overview_carry_parity_260.json·backend/tests/test_overview_carry_parity_260.py,
tasks/BOHUMFIT-260-*.md, handoff.md, locks.md — 실 PDF·엑셀 제외
※골든·서버 테스트는 `backend/`에 있으나 **서버 로직 변경은 0**이다(동등성 고정용 신규 파일).

## 커밋 메시지 (Codex용)
fix(BOHUMFIT-260): 클라이언트 미러 overview 회사별 이월 동기화 (259 잔여)

## Next
① Codex — 2차 검증(골든 양방향·화면 해지 시나리오·표준 무영향·배포 스모크) → 커밋·push
② ★Human — overview 문서 재다운로드 최종 검수(**해지 체크 포함** — 화면에서 계약을 해지한 뒤
  받은 엑셀의 `[후]` 회사 열이 그 계약만 빠지는지)
③ Chat — 잔여([후] 신규 계약·205 배지·간편 시트·사양 4건·카탈로그)
