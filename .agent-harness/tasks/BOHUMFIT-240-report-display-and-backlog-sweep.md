# BOHUMFIT-240 — 리포트 표시 개선 + 계류 백로그 일괄 소진 (6파트)

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: Codex (1차 검증 완료 — 파트별 2차 검증·커밋 대기)
Risk tier: 혼합 — 풀 하네스. git 쓰기 전면 금지(커밋 Codex 파트별 분리). 프로덕션 DB 연결 0. 실 PDF 로컬 참조만.
Date: 2026-07-22

※ PII: 실 PDF는 `보장분석/` 로컬 전용. 코드·테스트에 실명 0(합성=홍길동). 파트 독립 원칙 적용.

## P1 — 계약 라벨 회사명화 (완료)

- 헬퍼 신설(프런트 `companyLabel`·PDF/엑셀 `_company_label`): 회사명 표기, 동일 회사 복수 계약은 "회사명 (1)/(2)"(계약 idx 데이터 유지), 보험사 미제공은 "계약 N" fallback.
- 적용: CoverageRemodel ⑤ 매트릭스 컬럼 헤더·⑤ 카드 / export_pdf ⑤ 헤더 / export_excel [전]·⑤ 헤더. 236 B의 헤더 nowrap·세로중앙 유지. **파서 무변경**(표시 매핑만).
- 실측: D 케이스 교보생명 2계약 → "교보생명 (1)/(2)" 구분 대상 확인. 236 excel 테스트 갱신 + 중복 보험사 신규 테스트.

## P2 — 방향 토글 제거 (완료)

- 236 C의 `matrixByRows` 상태·토글 버튼·계약=행 모드 블록 완전 제거 → 회사=열 단일 방향 고정.
- 236의 계피·납만기·납입완료 병기·정렬은 유지(토글만 제거). tsc·npm test 회귀 0.

## P3 — 대분류 문단 구분 (완료)

- 담보를 13대분류 순서(GROUP_ORDER/GROUP13 — 락된 도메인 순서)로 그룹핑, 대분류 헤더 행 + 소속 담보 + 시각 구분(에메랄드 소프트 헤더·들여쓰기).
- 적용: CoverageRemodel ⑤ 매트릭스(Fragment 그룹 헤더 행)·export_pdf ⑤(grp-head 행·indent, per-row 대분류 열 제거). ④ 특약별 비교표는 기존에 이미 group12 섹션(h3)이라 무변경. 엑셀은 "시트 구조 유지 범위"라 대분류 열 유지(P1 라벨만).

## P4 — vite 보안 업그레이드 (★보류 — 태스크 가드 발동)

- S0: `.env` 무접촉(정책)하에 build 1회 실행 → 청크 **343.22 kB**(gzip 101.81). 기존 500kB 경고대로 **복귀하지 않음**.
- 태스크 명시 가드("★.env 복구로도 청크가 여전히 342kB대면 업그레이드 보류·원인 재조사 기록·무리한 진행 금지") 발동 → **vite 업그레이드 보류. package.json 무접촉.**
- npm audit 잔여: vite 8.0.0–8.0.15 high 1건(launch-editor NTLMv2·fs.deny 우회 — 둘 다 dev 서버/Windows 한정, `npm audit fix` 경로 존재).
- ★원인 재조사 필요(Human/Chat): 청크가 500kB 경고대로 복귀하지 않는 이유 — (a).env 미복구 (b)342kB가 실제 정상이고 과거 500kB 경고가 특이했던 것 (c)기타. .env 상태는 정책상 Code가 확인 불가(Human 게이트). 청크 정상화 확정 후 별도 태스크로 vite 업그레이드 재개 권장.

## P5 — phoneGate·history·billing role→tier 정합 (완료·231 후속)

- **phoneGate.ts**: `role==='internal'` 우회 → `bohumfit_tier==='internal'`. 미지값·null·role=advisor는 우회 안 함(fail-closed). ProfileRow 타입에 bohumfit_tier 추가. **usePhoneGate.tsx**: `.select("phone_verified, role")` → `"phone_verified, bohumfit_tier"`(P5 스코프 보강 — 셀렉트 없으면 판정 불가).
- **_history_is_internal**: `select("role")==="internal"` → `select("bohumfit_tier")` + `_normalize_bohumfit_tier`(미지값·조회실패→customer, fail-closed).
- **billing/status**: 231에서 이미 bohumfit_tier를 읽어 값은 tier로 정합(응답 `role` 키는 레거시명이나 값=tier, **프런트 미사용 실측**). 추가 변경 불요로 판정·기록.
- 232 봉인(SELECT 유지)·212 게이트와 정합. 테스트: phoneGate.test +3(tier 우회·advisor+customer fail-closed·미지값 fail-closed), history 가짜 admin을 bohumfit_tier 키 반환으로 갱신(로직 불변).

## P6 — test_205 실명 마스킹 (완료)

- `test_drug_change_205.py:3` docstring "이미숙님 처방조제 실데이터" → "실사용 처방조제 데이터·익명화". 테스트 로직·기대값·약품명(제품명, PII 아님) 무변경. 239 후속 후보 처리.

## 검증 체크리스트 (1차 — Code, 2026-07-22 결과)

- [x] backend pytest — **684 passed, 8 skipped**(기준선 683 + 신규 1[중복보험사 excel]. P5 history·236 테스트는 갱신). 기존 무손실.
- [x] tsc app/node · lint · npm test **79 passed**(77 + phoneGate P5 +2) · build 통과(청크 343.22 kB — P4 판단 근거).
- [x] 실 PDF 5건 재실행 — 월납·부값·계약수 **전부 불변**(A 2,835,744/B 681,312/C 183,621/D 763,089/239 실사용 4,675,189, 239 값 동일). N대·종수술 환산·239 실사용 합계 로직 무변경.
- [x] P4 라우트 스모크 18건(PublicRoutes 14+ProtectedRoute 4) npm test 포함 통과(P1~P3 렌더 회귀망).
- [x] P5 fail-closed 통과(advisor role+customer tier·미지값 → 우회 안 함). 232/212 정합.
- [x] PII grep 0(실명 전원). diff 범위 = 선언 파일만. pipeline/·migrations/ diff 0. `git diff --check` 통과.

## Stage 목록 (Codex용 — 파트별 분리 커밋)

- 커밋1(P1~P3): src/pages/CoverageRemodel.tsx, backend/coverage/export_excel.py, export_pdf.py, backend/tests/test_coverage_display_236.py
- 커밋2(P4): **없음(보류)** — package.json 무접촉
- 커밋3(P5): src/lib/phoneGate.ts, src/lib/phoneGate.test.ts, src/lib/usePhoneGate.tsx, backend/main.py, backend/tests/test_history_156.py, test_history_171.py
- 커밋4(P6): backend/tests/test_drug_change_205.py
- 공통: tasks/BOHUMFIT-240-*.md, handoff.md, locks.md (.env*·실 PDF·PII 제외)

## 커밋 메시지 (Codex용 — 파트별)

- feat(BOHUMFIT-240): 리포트 계약 라벨 회사명화 + 방향토글 제거 + 대분류 문단 구분
- refactor(BOHUMFIT-240): phoneGate·history role→bohumfit_tier 정합 (231 후속)
- chore(BOHUMFIT-240): test_205 실명 마스킹
- ※ vite 업그레이드(P4)는 청크 이상 신호 미해결로 보류 — 별도 태스크
