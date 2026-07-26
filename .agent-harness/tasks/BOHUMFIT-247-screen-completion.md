# BOHUMFIT-247 — 신 체계 3단계: 화면 완성 (비분양식 의미 구조 반영)

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: Codex (2차 검증·커밋 — build 게이트는 프로덕션 대체 검증)
Risk tier: 중위험 — 풀 하네스. git 쓰기 금지(커밋 Codex). 실 PDF·엑셀 로컬 참조만·stage 금지.
Date: 2026-07-26

## ★중단 보고 — 빌드 산출물 이상 신호 (AGENTS.md 절대 규칙 발동)

### 발견 경위
247 구현 완료 후 1차 게이트 중 build 검증에서, 화면 코드가 늘었는데 청크가 343.22 kB로
불변인 점을 이상하게 여겨 번들 내용을 실측했다.

### 실측 증거 (2026-07-26)
1. **로컬 빌드 번들(343,225 B)에 앱 코드가 없다**: 신규 문자열은 물론 기존 화면 문자열
   ("전후 비교 계산"·"수동 담보 추가" 등 236 구현분)까지 **0건**. 한글은 전체에서 32자뿐
   (supabase 환경변수 오류 문구가 유일)이고 파일이 그 문구에서 끝난다. `node --check`는
   통과(구문상 유효)하나 내용상 vendor+초기 모듈만 있는 껍데기다.
2. **빌드된 앱이 렌더되지 않는다**: `vite preview`(dist 서빙) 실행 → 페이지 본문 **완전 공백**
   (콘솔 에러 0 — 조용한 실패).
3. **배포본(Vercel Linux 독립 빌드)은 정상 추정**: 프로덕션 엔트리
   `/assets/index-SQcvu3ZC.js` = **786,541 B**(로컬의 2.3배). 실서비스가 정상 동작하는 이유.

### 판정
- **로컬 Windows `npm run build` 산출물이 240 이후 줄곧 껍데기였을 가능성이 높다.**
  타임라인: 240 P4에서 "청크 500 kB대 → 343 kB대 급감"이 관찰됐고, 이후 조사에서
  "343 kB대 = 정상(경고 없는 상태가 정상)"으로 기준선이 재정의됐다(242 문서화).
  이번 실측은 그 판정과 모순된다 — **급감분이 곧 앱 코드 소실분**이었다.
- 유력 원인: 241에서 확정한 rolldown-vite의 Windows npm optionalDependencies 바인딩
  문제 계열(당시 dev 서버 한정으로 판정했으나, 로컬 프로덕션 번들 생성에도 조용한 실패가
  있는 것으로 보인다). 빌드는 exit 0·"✓ built"를 출력해 게이트가 감지하지 못했다.
- **영향 범위**: 배포(Vercel)는 무영향 추정(독립 빌드·크기 정상). 백엔드 pytest·프런트
  vitest·tsc·lint 게이트는 소스 기준이라 유효. 무효인 것은 "빌드 청크 343 kB대 = 정상"
  기준선(242 문서·CLAUDE.md·AGENTS.md·verify.md)과 로컬 빌드 산출물의 기능 검증 가치다.

### Human 결정 필요
1. 기준선 정정: "343 kB대 정상" 폐기 → 로컬 빌드 산출물 신뢰 불가 명시(문서 3종+verify.md).
2. 원인 수정 태스크 발번(241 재개 계열): rolldown 바인딩 수리 또는 wasm fallback 강제,
   그리고 **빌드 산출물 스모크**(번들 내 앱 문자열 존재·크기 하한) 게이트 추가.
3. 247 커밋 진행 여부: 코드 게이트(tsc·lint·vitest 89)는 통과 — build 게이트만 판정 불가.
   Codex(2차)는 Linux/정상 환경 빌드로 대체 검증 가능하면 진행 가능(Codex도 같은 Windows면
   동일 문제 예상 — Vercel 배포 빌드 성공 여부로 대체 확인 권장).

---

## 배경
246으로 데이터 계층 완성(신 11그룹·40행·뇌심 단계·[후] 이월·overview 가드). 246의 화면
반영은 "최소 정합"(GROUP_ORDER 교체)까지였고, 이번에 양식의 의미 구조를 화면에 완성한다.
엑셀 파일 재현은 248(별도) — 이번엔 웹 화면만.

## 목적 (패킷 A~F 요약)
A. [전|담보|후] 비교 뷰: 신 40행 순서·계약 열 전부·[후]=이월 결과·전=후 시각 동일
B. 종합비교 블록(시트3): 암/뇌·심장 초중말 — 전→후 화살표·개선(후−전) + 강조
C. 보험료 차액=후−전 표기·특이사항 영역(246 경고 노출)
D. Y/N 5행 파생 표시·overview [후] 동일성
E. 신담보 3행 "신규 설계 반영 대상" 구분
F. 기타 그룹 접이식(정보 보존 가시화)

## 진행 기록 (Claude Code · 2026-07-26)

### S0 — 실측
- 화면 구조: `CoverageRemodel.tsx` 1,374행 단일 파일 — ①표지 ②유지/해지 ③신규제안 ④비교표
  ⑤회사별 매트릭스. [후] 계산은 **클라이언트 표시 캐시**(`coverageAfterDisplayCache.buildAfterResult`
  — 211 패리티로 백엔드 compare와 잠금).
- ★부족 필드/결함: ① 캐시 타입에 246 파생 필드(stage_totals·yn_flags·overview·estimated) 부재
  ② **캐시에 246 회송 보정(overview 합계-only 이월) 미반영** — E 케이스에서 브라우저 [후] 계산이
  백엔드 반려 결함과 동일하게 26행 소실 재현(211 패리티 위반 상태) ③ 계약 미상 키('?') 이월
  규칙도 미반영 ④ ④비교표 그룹 내 정렬이 이름 가나다순(양식 순서 아님).
- backend 필드 노출: build_before가 stage_totals·yn_flags·overview를 이미 payload에 포함
  (246) — **backend 추가 수정 0**으로 충분함을 확인.

### 구현 (완료 — 코드 게이트 통과)
- `src/lib/coverageAfterDisplayCache.ts`: 타입 확장(overview·estimated·stage_totals·yn_flags)
  + 246 미러 상수(ITEM_ORDER·YN_ITEMS·STAGE_COMPONENTS/COMMON_ADD — 백엔드 정본 주석) +
  `computeYnFlags`/`computeStageTotals`/`itemOrderKey`/`NEW_COVERAGE_PLACEHOLDERS` +
  **buildAfterResult overview 이월 패리티 보정**(합계 수준 유지 + 신규 제안 가산 + 해지 시
  보존·경고 — 백엔드 246 회송 보정과 동일 규칙) + 계약 미상 키 이월.
- `src/lib/coverageFormat.ts`(신설): 237 금액 포맷터 단일 소스화(페이지·블록 공용).
- `src/components/CoverageInsightBlocks.tsx`(신설): `StageComparisonTable`(전→후·개선 + 강조·
  H10 심장중기 정정 라벨) · `YnFlagTable`(전/후 Y·N 배지) · `SpecialNotes`(특이사항).
- `src/pages/CoverageRemodel.tsx`: ④에 보험료 차액(후−전) 라벨·특이사항(warnings+cautions+
  improvements 중복 제거)·종합비교/Y/N 블록·신담보 오독 방지 문구, ④⑤ 기타 접이식(기본 접힘·
  개수 표기), ⑤ 담보 열 sticky(15계약 가로 스크롤 UX), 그룹 내 정렬 = 시트2 항목 순서.
- 테스트 +10: `coverageNewTaxonomyDisplay.test.ts`(순서·단계 수식·Y/N·overview 전=후·
  해지 보존+경고·'?' 이월) · `CoverageInsightBlocks.test.tsx`(렌더 4건).

### 검증 체크리스트 (1차 — 완료 · 2026-07-26 재개)
- [x] tsc app/node · lint · npm test **89 passed**(기준선 79 + 신규 10)
- [x] backend pytest 무접촉(백엔드 수정 0 — 705/8 기준선 그대로)
- [x] build — **로컬 무효(Human 결정 ①: 343 kB 기준선 폐기)** → Codex가 배포 후
      **프로덕션 번들로 대체 검증**(Human 결정 ③). 빌드 수리는 248 별도 태스크(결정 ②).
- [x] 실 PDF 5건 화면 payload 검증(소스 기준 — jiti로 클라이언트 캐시 직접 실행):
      ① 행 순서 5건 전부 OK(그룹 = 비분양식 순, 그룹 내 = 시트2 항목순 — A54·B46·C48·D48·E54행)
      ② 계약 열 전부 전개 — A9·B15·**C3**·D10·E15(실측 일치 · ※패킷 "9~15"는 개괄치,
        C는 실제 3계약으로 243 실측과 일치 — 누락 0 의도 충족)
      ③ 전=후 동일(해지 0) 5건 전부 OK(의미 비교: 계약값·overview·estimated + 단계·Y/N 파생
        — 백엔드 payload 파생값과 클라이언트 재산출 정합 확인)
      ④ E overview: 플래그 존재·해지 1건 시 "합계형 해지 불가" 경고 노출·합계 보존 OK
      ⑤ 월납/부값 5건 불변(A 2,835,744/2,282,564 · B 681,312 · C 183,621 · D 763,089/495,389 · E 4,675,189)
- [x] PII grep 0(신규 파일)·pipeline diff 0·diff 범위 = 프런트 5파일+테스트 2파일+harness.
      실 PDF payload 임시 파일은 검증 후 스크래치에서 삭제.

### 검증 체크리스트 (2차 — Codex · 2026-07-26)
- [x] backend **705 passed, 8 skipped**(backend diff 0)·tsc app/node·lint·frontend **89 passed**.
- [x] 로컬 build exit 0·JS **343.22 kB**(gzip 101.81 kB)는 참고 수치만 기록하고 판정에 사용하지 않음.
- [x] 실 PDF 5건을 backend payload→클라이언트 캐시 경로로 재실행: 시트2 행 순서·계약 열 전수·계약값/overview/estimated 전=후·단계/Y/N·월납/부값 모두 1차 결과와 일치.
- [x] E 클라이언트 캐시 [후] **54행·1,542,990,000원** 유지, overview 해지 요청 시 합계 보존+경고.
- [x] PII 0·런타임 브랜드 계약 0·backend/pipeline/supabase/package diff 0·실 PDF/엑셀 tracked 0·diff check 통과. 변경 TSX React 체크리스트 차단 항목 0.

### 재개 경위 (Human 결정 · 2026-07-26)
① 343 kB 기준선 폐기 확정 ② 빌드 수리 = 248(클린 재생성+vite+산출물 스모크 게이트)
③ 247 커밋 진행 — Codex가 배포 후 프로덕션 번들로 build 게이트 대체 검증.

## Stage 목록 (Codex용 — 재개 시)
src/pages/CoverageRemodel.tsx, src/lib/coverageAfterDisplayCache.ts, src/lib/coverageFormat.ts,
src/components/CoverageInsightBlocks.tsx, 테스트 2파일, tasks/BOHUMFIT-247-*.md, handoff.md,
locks.md — 실 PDF·엑셀 제외

## 커밋 메시지 (Codex용 — 재개 시)
feat(BOHUMFIT-247): 신 체계 화면 완성 — 종합비교·차액·특이사항·Y/N·신담보 표시

## Next
① **Codex** — 2차 검증(payload 검증 재현·기존 기능 회귀) → 커밋·push → **배포 후 프로덕션
   번들로 build 대체 검증**(크기·신규 문자열 존재 — 로컬 빌드는 무효)
② Human — 재업로드 육안 검수(신 화면 전체) + 계류 확인 2건(D 재해사망·E 중입자/표적)
③ Chat — 248(빌드 수리: 클린 재생성+vite+산출물 스모크 게이트) 발번 — 엑셀 양식 재현은 후속 재번호
