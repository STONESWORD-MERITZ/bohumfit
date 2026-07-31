# BOHUMFIT-262 — Human 무의존 백로그 일괄 (조사·정리·검증 강화 5파트)

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: Codex (파트별 3커밋) / Human (결정지 3종)
Risk tier: 혼합(저~중) 5파트 — 풀 하네스. git 쓰기 금지(커밋 Codex).
실 PDF·엑셀 로컬 참조만·stage 금지. ★파트 독립.
Date: 2026-07-31 · 기준 HEAD `73fa74f`(261)

## 공통 수정 금지
backend/pipeline/(P4 제외)·coverage 집계·parser 로직 변경 금지(P3 정리 제외)·
실 PDF/엑셀 stage 금지·PII 0·사양 결정 필요 사항은 보고만(구현 금지)

## P1 — 248 QA 결정지 정리 ✅ 완료 (문서)
- 248 QA 사양결정 4건 + 카탈로그 18항목을 **실측 재확인**해 산출:
  **`tasks/BOHUMFIT-262-decision-sheet.md`**.
- ★해소 판정 5건(결정 불요로 제외): QA-3 인쇄 1장(250 `fitToWidth` + 261 실렌더 확인) ·
  1-3 계약 `'?'` 축소(253·256 — 이번 재실측 **정본 2건 `'?'` 0건**) · 4-1 스모크 고정 세트
  (255-P2) · 4-2 3계층 자동화(**262-P5**) · 5-2 성능(248 시점 조치 불요).
  부분 해소 1건: 3-4 PDF 렌더 검증 — 261에서 로컬 실렌더 복구, **CI 골든만 잔존**(D-6 승계).
- 잔존 **16항목을 D-1~D-16으로 번호화**해 [현상·옵션·권장안·규모·위험도·선행조건] 표로 정리,
  **번호+옵션 숫자만으로 답변** 가능하게 구성. 선행조건(에셋·샘플·관리자 권한)도 명시.

## P2 — 가입제안서 [후] 트랙 사전 설계 ✅ 완료 (문서)
- 산출: **`tasks/BOHUMFIT-262-proposal-track-design.md`**.
- 현행 경로 실측 지도(수동 카드 / 제안서 업로드 → `proposal_parser` 23룰 → `plan.proposals`
  → `carry_coverage_row(extra_values)` → 252 회사 열·254 Y/N·261 20년 차액).
- 확정 가능 설계: 신규 계약 스키마·40행 매핑 규칙(미매칭은 기타 보존 — 248 누락 0 계약)·
  업로드 흐름·통합치료비 3행 채움 규칙·**어댑터 패턴**(유일 지문일 때만 전용 어댑터,
  아니면 Generic 폴백 — 253/256 유일성 원칙 재사용) + **S1~S5 단계 분할안·각 검증 기준**.
- ★**「샘플 필요」 5항목 명시**(회사별 지문·담보 표기 사전·금액 형식·통합치료비 문구·
  납입/만기 위치) — 추측 0.

## P3 — 코드 위생 정리 ✅ 완료 (저위험 구현 · 동작 변경 0)
- **제거(완전 미사용 실측)**: `excel_style`의 `FILL_HEADER`·`FILL_HIGHLIGHT`·`FILL_SPECIAL`·
  `FILL_SOFT`·`FILL_GRAY`·`FONT_HEADER`·`FONT_TITLE`·`BODY`(외부·내부·테스트 참조 전부 0) +
  불필요해진 `PatternFill` import. `src/index.css`의 `--text-fluid-title`(참조 0).
- **★제거하지 않은 것(오판 방지 기록)**: `--text-fluid-hero`·`--text-fluid-headline`은
  `var()` 검색으로는 0건이지만 **Tailwind 유틸 클래스로 실사용 중**(`Home.tsx`,
  `WhyDisclosure.tsx`) → 유지. `SIDE_THIN`·`GRAY_TX`·`_yn_map`·`_grp_key`·
  `OUT_OF_RANGE_LABEL`은 사용처 확인돼 유지. 262 위생 대상 파일·신규 diff의 `TODO/FIXME`는 **0건**이며,
  기존 `backend/main.py` 본인인증 스텁 TODO 1건은 범위 밖이라 유지.
  `_is_overview`(259 제거분) 잔재도 **0건** 확인.
- ★검증: **HEAD 대비 실 PDF 2건 payload 완전 동일 + 엑셀 셀 diff 0/0/0**(표지 시트는 작성일이
  생성 시각이라 대조 제외 — 261 신설분) → **동작 변경 0 증명**.

## P4 — 205 투약 배지 진단 ✅ 완료 (조사 전용 · 코드 0)
- 산출: **`tasks/BOHUMFIT-262-med-badge-diagnosis.md`**.
- ★**패킷 전제 정정**: 배지는 "약값"이 아니라 **투약 일수**이며, "최대 단일청구"도
  "단순 누적 총합"도 아닌 **날짜별 최대의 누적 합**(`filters._sum_daily_max_presc`)이다.
  초록/주황은 별개 스펙이 아니라 **30일 임계 색상**(≥30 주황).
- 코드 근거 확정: `disease_aggregator`(날짜별 적재) → `result_builder:283~291`(창·함수 확정)
  → `Disclosure.tsx:372`(렌더). 이 산식은 **030 진단 → 031/032에서 "배지=헤더 판정 일치"를
  위해 의도적으로 채택**된 것.
- 실데이터 재현(고지 정본·실명 미기재): I10 **1,002일**(근거 23건)·G45 344일·E78 210일 등
  22건 — 전부 30일 이상이라 초록 배지는 이 문서에서 미발생.
- 3안(A 현행 유지 / B 최대 단일 / C 건별 나열) + 규모·회귀 위험 비교, **권장: A + 표기 보강**
  (툴팁에 "5년 내 처방일수 합계(N건)"). **B는 채택 금지 권장**(배지와 고지 판정이 어긋나 030 재발).
- ★구현 0(`pipeline/` 무접촉).

## P5 — 스모크 자동화 강화 ✅ 완료 (중위험 구현)
- 신설 **`scripts/smoke-coverage.mjs`** + `npm run smoke:coverage` 등록 + `verify.md` 실행법 수록.
- 대조 항목: 계약 수·담보행/enrolled·총액·월납(부값)·overview행/합계·귀속률(기준표) +
  **항상 성립해야 하는 불변식** — 회사합=합계 0(**payload·엑셀 시트2 양쪽**)·해지 0 시 전=후 0·
  `'?'` 잔존 0·3시트 구성. 불일치 시 **exit 1**.
- ★3동작 전부 실증:
  · **PASS** — 정본 2건 전부 기준값 일치(exit 0)
  · **FAIL** — 기준값 1개를 의도적으로 1원 틀리게 하자 `✗ total: 기준 604560001 vs 실측 604560000`
    출력 + **exit 1**(248 `build:verify` 정직성 선례 준수). 실증 후 즉시 원복.
  · **skip** — PDF 경로 부재 시 경고 3줄 + **exit 0**(CI·타 환경 무실패)
- 인접 정정: `verify.md`·`AGENTS.md`·`CLAUDE.md`의 게이트 기준선이 255 시점(750/8·95)으로
  낡아 있어 **792/8·99로 3문서 동시 갱신**(CLAUDE.md 규칙), `verify.md`의 "별도 상비 스크립트는
  없으며" 문구도 P5 신설로 무효가 되어 정정.

## 검증 체크리스트 (1차 — 완료 · 2026-07-31)
- [x] backend pytest **792 passed, 8 skipped**(P3·P5는 코드 동작 변경 0이라 신규 테스트 없음 —
      P5는 스크립트 자체가 실행 검증) · tsc app/node · lint · npm test **99 passed**
- [x] ★P3 동작 변경 0: HEAD(`73fa74f`) 대비 실 PDF 2건 **payload 완전 동일** ·
      **엑셀 셀 removed/changed/added 0/0/0**(표지 제외)
- [x] ★P5: 정본 2건 **PASS** · 의도적 불일치 시 **FAIL(exit 1)** · 파일 부재 시 **skip(exit 0)**
- [x] P1·P2·P4 문서 3종 산출 · **해당 파트 코드 변경 0**
- [x] PII 0(문서 실명 미기재·실데이터 산출물 미보존) · diff 범위 = `excel_style.py`·
      `src/index.css`(P3) · `scripts/smoke-coverage.mjs`·`package.json`·`verify.md`(P5) ·
      tasks 4종·`AGENTS.md`·`CLAUDE.md`(기준선)·handoff·locks.
      **`pipeline/`·집계·parser·`export_excel`·`export_pdf` 로직 diff 0**

## Stage 목록 (Codex용 — 파트별 분리 커밋)
- 커밋1(P3): `backend/coverage/excel_style.py`, `src/index.css`
- 커밋2(P5): `scripts/smoke-coverage.mjs`, `package.json`, `.agent-harness/verify.md`,
  `AGENTS.md`, `CLAUDE.md`(기준선 동기 — P5 인접 정정)
- 커밋3(P1·P2·P4): `tasks/BOHUMFIT-262-*.md` 4종 + `handoff.md`·`locks.md`

## 커밋 메시지 (Codex용)
1) chore(BOHUMFIT-262): 244~261 잔재 코드 위생 정리 (동작 변경 0)
2) feat(BOHUMFIT-262): 스모크 정본 세트 자동 대조 스크립트
3) docs(BOHUMFIT-262): QA 결정지 + 가입제안서 트랙 설계 + 205 배지 진단

## Next (handoff 명시)
① Codex — 파트별 검증·3커밋 (P3는 값 diff 0, P5는 FAIL 실증 중점)
② Human — 결정지 3종 검토(**D-1~D-16 번호 답변** · 205 배지 스펙 · 가입제안서 샘플 수집)
③ Chat — 결정 수신 후 후속 발번
