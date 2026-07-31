# BOHUMFIT-259 — overview 엑셀 회사 열 렌더 + [후] 회사별 이월 (255-B 완결)

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: Codex (2차 검증·커밋)
Risk tier: 중위험 — 풀 하네스. git 쓰기 금지(커밋 Codex). 실 PDF·엑셀 로컬 참조만·stage 금지.
Date: 2026-07-29 · 기준 HEAD `3748719`

## 배경
256~258로 overview 문서의 `by_company` 100% 귀속 완료. 그러나 ① `export_excel`의 overview
가드가 회사 열을 막아 엑셀은 여전히 합계만 ② `[후]`는 249 설계대로 합계만 이월해 by_company가
빔. 둘 다 남으면 Human 실물 검수 불가 · `[전]`만 회사 열인 비대칭.

## S0 실측 (3개 지점 확정)
1. **렌더 가드**: `export_excel._sheet_compare_form` —
   `b_companies = [] if overview else …` / `a_companies = [] if (after_before is None or overview)`.
   추가로 `new_slot`(신규 골격 열)·`b_unk`/`a_unk`(미확인 열)도 `not overview` 조건에 묶여 있었다.
   `_unknown_bucket_present`는 루프에서 `row.get("overview")` 행을 아예 건너뛰었다.
2. **이월**: `aggregator.carry_coverage_row`(249 정본)의 overview 분기가 `by_company`를 버리고
   `dict(extra_values)`로 덮어써 합계만 이월.
3. **해지 경고**: `consulting`·`compare` 두 경로가 "overview 행 존재 + 해지 요청"이면
   `OVERVIEW_CANCEL_WARNING`을 붙였다 → 귀속된 문서에서는 **사실과 다른 경고**가 된다.
   ★239 당시의 "해지 반영 불가" 제약은 256~258 귀속으로 **해소**됐음을 확인.

## 구현
### A. 렌더 가드 전환 — "overview 여부" → ★"by_company 유무"
- `_company_columns_available(before_like)` 신설: enrolled overview 행이 **전부** 귀속돼 있으면
  회사 열 전개, 하나라도 비면 합계만. overview 행이 없는 표준 문서는 항상 True(경로 무변경).
- ★**부분 귀속은 합계만** 유지 — 빈 회사 열이 "어느 회사에도 없음"으로 오독되는 252 반려 사유와
  동종 위험을 차단한다.
- `[전]`·`[후]`를 **각각 판정**(해지로 `[후]` 귀속 상태가 달라질 수 있다).
- `new_slot`·`b_unk`/`a_unk` 조건을 `not overview` → **회사 열 존재(n/m)** 기준으로 전환하고,
  `_unknown_bucket_present`의 overview 배제는 제거했다(미귀속 행은 by_company가 비어 자동
  미해당이고, 귀속 행에 `'?'`가 남으면 미확인 열을 정직하게 노출 — 252 가드 일관 적용).
- 죽은 코드 정리: 가드 전환으로 쓰이지 않게 된 `_is_overview()`와 지역변수 제거.

### B. [후] 회사별 이월 (249 정본 확장 — overview 분기만)
- `carry_coverage_row`: overview 행이 **귀속돼 있으면 일반 행과 동일 경로**(keep/cancel 필터 +
  `'?'` 이월 + 신규 제안 병합 + 재집계)를 타게 했다. 귀속이 없는 overview 행만 종전대로 합계
  수준 이월(해지 반영 불가). ★표준 문서 경로·일반 행 규칙은 한 글자도 바뀌지 않았다.
- 회사합=합계가 귀속 게이트로 보장되므로 **해지 0이면 재집계 결과가 `[전]`과 동일**(전=후 유지).

### C. 해지 경고 조건부화
- `overview_rows_need_cancel_warning(coverages)` 신설 — **귀속되지 않은 overview 행이 있을 때만**
  True. `consulting`·`compare` 두 경로가 이 함수를 공유(문구·조건 동기).

## 검증 체크리스트 (1차 — 완료 · 2026-07-29)
- [x] backend pytest **782 passed, 8 skipped**(771 + 신규 11: 이월 4·경고 1·렌더 4·해지 2)
- [x] ★overview 엑셀(사용자 동선 엔드포인트 경유) — 해지 **0/1/3건** 시나리오 전부:
      · 해지 0: `[전]` 15/15 · `[후]` 15/15 회사 열(2단 헤더 상품명 15/15) · 회사합=합계 상이
        **0**(양쪽) · 셀=payload 상이 **0** · **전=후 담보 상이 0** · overview 합계
        **1,400,240,000** · 전체 총액 **1,542,990,000** · 월납 **4,675,189** 불변 ·
        합계형 경고 **0건**(불필요 경고 제거 확인) · Y/N 회사별(254) 표기 유지
      · 해지 1건(계약1): `[후]` 14열 · 대사 0 · overview 합계 1,290,640,000
        (**감소분 109,600,000 = 계약1의 실손 4종+3대비급여** — 회사 단위 정확 반영)
      · 해지 3건: `[후]` 12열 · 대사 0 · 담보 15건 변화 · 월납도 재계산(4,544,899)
- [x] ★표준 문서 회귀 0 — **엑셀 산출물 셀 단위 removed/changed/added 0/0/0 + 해시 동일**
      (HEAD `3748719`의 coverage 7모듈을 별도 프로세스로 실행해 대조) + payload(담보 값·group12·
      agg·enrolled·by_company·overview 플래그·월납·[후] 이월·경고) diff 0 · 인쇄영역 동일
- [x] overview 값 보존(좌표 무관): 구 산출물 값 중 신 산출물에 **없는 것 0** ·
      신규 293개는 회사 열·2단 헤더·골격 열 신설분. 좌표 이동(합계 열 2→17열)으로 인한
      셀 좌표 diff(removed 112·changed 25·added 405)는 **의도된 변화**
- [x] by_company 빈 overview(합성) → 회사 열 미생성·합계만 + 해지 시 경고 유지(가드 전환 회귀)
- [x] tsc app/node · lint · npm test **95 passed**(프런트 무접촉) · PII 0
- [x] diff 범위 = `export_excel.py`·`aggregator.py`(carry+경고 헬퍼)·`consulting.py`·`compare.py`
      (경고 조건) + 테스트 1(신규) + harness. **`pipeline/` diff 0 · `parser.py` diff 0
      (256~258 무변경) · `constants.py` diff 0 · `src/` diff 0**

## 잔여(스코프 밖 기록)
- 클라이언트 미러(`src/lib/coverageAfterDisplayCache.buildAfterResult`)는 overview 행을 여전히
  합계 수준으로 이월한다(249 주석의 "규칙 변경 시 동기 수정" 대상). 화면 내보내기는 사용자
  동선상 **서버 payload를 그대로 POST**하는 경로가 아니라 클라이언트가 만든 `afterResult`를
  보내므로, 프런트에서 해지한 경우 overview `[후]` 회사 열이 합계로 남을 수 있다.
  → 프런트 동기화는 별도 태스크 필요(규모 S, `src/` 무접촉 계약 때문에 이번에 미포함).

## Stage 목록 (Codex용)
backend/coverage/export_excel.py·aggregator.py·consulting.py·compare.py,
backend/tests/test_overview_render_carry_259.py(신규),
tasks/BOHUMFIT-259-*.md, handoff.md, locks.md — 실 PDF·엑셀 제외

## 커밋 메시지 (Codex용)
feat(BOHUMFIT-259): overview 엑셀 회사 열 렌더 + [후] 회사별 이월 (255-B 완결)

## Next (handoff 명시)
① Codex — 2차 검증(overview `[전]`·`[후]` 회사열·표준 셀 diff 0·해지 시나리오·Excel 실렌더·
  배포 스모크) → 커밋·push
② Human — ★overview 문서 재다운로드 최종 검수(주력 고객층 커버리지 완성 — 표준 문서처럼
  회사별로 나오는지)
③ Chat — ★프런트 클라이언트 미러 동기화(위 잔여·S) + 잔여([후] 신규 계약·205 배지·간편 시트·
  사양 4건·카탈로그)
