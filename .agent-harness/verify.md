# Verification

Standard verification for BOHUMFIT:

Codex runs these commands directly in the Windows workspace unless a task states a narrower verification scope.

```powershell
npm run lint
npm test
npm run build
```

For UI changes, also run the app locally and do a browser smoke test:

```powershell
npm run dev
```

## 검증 기준선 (BOHUMFIT-294 Codex 2차 실측 · 2026-08-18 갱신)

백엔드 pytest — `cd backend && python -m pytest -q`:

```text
1052 passed, 8 skipped
```

(BOHUMFIT-294 Codex 2차 실측·2026-08-18 — 293 기준선 1044/8에 카카오 중복 생략 계약 8건을 더해 1052/8.
BOHUMFIT-293은 292 기준선 1031/8에 서식 회귀 스위트 13건을 더해 1044/8.
구 40행 양식 파생 상수 5종 제거로 줄어든 테스트는 없다(구 상수 단언을 V2 또는 파서 사전 단언으로 이관).
직전 이력: BOHUMFIT-292 Claude Code 1차 실측·2026-08-18 — 291 기준선 1003/8에 S4 매칭·분배 배선 계약 28건을
더해 1031/8. Codex 2차 실측으로 확정.)

프런트 테스트 — `npm test`(라우트 스모크 18건 포함):

```text
406 passed / 41 files
```

(BOHUMFIT-294 Codex 2차 실측·2026-08-18 — 기존 402/41에 카카오 중복 생략 회귀 4건을 더해 406/41.)

타입체크 — 양쪽 모두 통과해야 한다:

```powershell
npx tsc -p tsconfig.app.json --noEmit
npx tsc -p tsconfig.node.json --noEmit
```

빌드 산출물 — `npm run build && npm run build:verify`(BOHUMFIT-248 게이트):

```text
정상 참조치: 프로덕션(Vercel) 786 kB대 (2026-07-26 실측 786,541 B)
판정: scripts/build-verify.mjs — ①크기 하한 600 kB ②필수 앱 문자열 ③index.html 참조 무결
```

- ★기준선 정정(BOHUMFIT-248 · 2026-07-26): 과거 "343 kB대 정상"(240 조사·242 문서화)은 **폐기**.
  로컬 Windows 번들 343 kB대는 rolldown 네이티브 바인딩 부재로 앱 코드가 통째로 빠진 껍데기였고
  (247 실측: 번들 내 앱 문자열 0건·vite preview 본문 공백·조용한 exit 0), 240의 격리 빌드 대조는
  동일하게 고장난 로컬 빌더 위에서 수행돼 오판이 재생산됐다. 이력 보존을 위해 기록한다.
- ※현 로컬 Windows: Application Control이 신규 네이티브 바이너리를 차단(248 P1 실측 — rolldown
  1.1.5·tailwind oxide 4.3.3 로드 차단, 구 설치본은 허용)하고 rolldown WASI는 Windows 절대경로를
  해석하지 못해 클린 재생성으로도 복구 불가. **로컬은 build:verify FAIL이 정직 상태**이며 기능
  판정은 소스 게이트(tsc·lint·vitest) + Codex의 프로덕션 번들 대체 검증으로 한다(Human 결정).
  ★껍데기 크기는 **약 343 kB로 코드 증가에 따라 변동**한다(271 실측 343,702 B — 이전 343,225 B에서
  사전 모듈만큼 증가). 특정 바이트 수치 일치를 "변경 무관"의 근거로 쓰지 말 것.
  근본 해결 후보: 정책 예외 등록(Human·관리자) / WSL·CI 빌드 검증 — 카탈로그 참조.
- ★248 제약은 **`npm run build` 산출물에 한정**된다. `npm run dev`(Vite dev 서버)는 정상 기동하므로
  실브라우저 기능 검증은 로컬 dev 서버로 수행할 수 있다(BOHUMFIT-277b 재실측: Vite v8.0.10 정상 기동).
  과거 기록에서 단순히 "로컬 빌드 불가"를 이유로 브라우저 검증을 생략한 항목은 dev 서버로 재검증 가능한지
  먼저 다시 판정한다. 인증 환경변수·실계정 등 별도 전제가 없을 때만 그 정확한 사유로 확인 불가를 기록한다.

### PII scrub 검증 한계 (BOHUMFIT-277b)

- `scrub_text`/`scrubPii`는 ICD 형식 상병코드와 기관명 접미사, 알려진 파일 토큰을 제거하지만,
  **병명**과 **문장 중간의 공백 포함 한글 파일명**을 완전히 식별하지 못한다.
- 따라서 console/Sentry breadcrumb의 PII 차단 근거는 정규식 자체가 아니라 운영 환경에서
  `safeErrorSummary`만 내보내는 **raw 본문 비전송 계약**이다. 회귀 검증은 scrub 패턴과 raw 비전송을
  분리해 단언하며, 정규식 통과만으로 "PII 0"이라고 판정하지 않는다.

기준선 수치가 바뀌면 이 파일과 `CLAUDE.md`·`AGENTS.md`를 함께 갱신한다.

## 스모크 정본 세트 (BOHUMFIT-255 P2 · 2026-07-29 신설)

보장분석(coverage) 트랙의 실데이터 회귀는 아래 **2케이스를 정본**으로 한다. 2026-07-29 시점에
기존 5케이스 중 3건이 삭제돼(임의 정리) 회귀 근거가 끊긴 사고가 있었다 — 재발 방지를 위해
**파일 없이도 복구·판정이 가능하도록 기준 수치를 여기에 고정**한다.

| 케이스 | 유형 | 파일(로컬 전용) | 계약 | 담보행/enrolled | 총액 | 월납(부값) | overview행 | 파싱 경고 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 표준(계약별 매트릭스) | 상품별 가입현황 존재 | `보장분석\비교분석표\이*숙-INPUT.pdf` | 15 | 57/29 | 614,860,000 | 681,312 (531,312) | 0 | 0 |
| overview(합계-only) | 239 fallback(매트릭스 부재) | `보장분석\비교분석표\라*실INPUT.pdf` | 15 | 59/42 | 1,501,690,000 | 4,675,189 (4,675,189) | 25 | 1 |

- 기준일 `today="2026-07-29"`, 해지 0(`build_after_analysis(..., {"existing": [], "proposals": []})`)
  기준값이며, 두 케이스 모두 **해지 0에서 [전]=[후] 상이 0**이 성립해야 한다.
- 표준 케이스 추가 고정값: 회사합=합계 대사 [전]/[후] 상이 0, Y/N 회사별 = payload 파생 일치
  (자동차부상=계약3·가족일상=계약7만 Y), 보험료 셀은 9행(254 개정)·계약 idx 7은 월납 None(공란).
- overview 케이스 추가 고정값: 259 이후 귀속 가능한 담보는 회사 열 15개로 전개하고,
  장기요양간병비 9,000,000은 합계-only·미귀속 경고 유지(246/239). overview 담보 25종 합계
  1,358,940,000·귀속률 99.3%.

### 자동 대조 (BOHUMFIT-262 P5)

```powershell
npm run smoke:coverage
```

- 위 표의 기준값과 실 산출을 대조하고 **불일치 시 exit 1**로 실패한다(248 `build:verify` 선례).
- 계약 수·담보행/enrolled·총액·월납(부값)·overview행/합계·귀속률에 더해 **회사합=합계 0**
  (payload·엑셀 `컨설팅 전` 시트 양쪽)·**해지 0 시 전=후 0**·**`'?'` 잔존 0**·4시트 구성을 항상 검사한다.
- 실 PDF가 없으면 **경고 후 건너뜀(exit 0)** — CI·타 환경에서 깨지지 않는다(PII로 커밋 불가).
- 기준값은 `scripts/smoke-coverage.mjs`의 `BASELINE`에 있다. ★위 표를 고칠 때 함께 갱신한다.
- ★**BOHUMFIT-290(S2) Human Q6 승인 반영**: 49행 V2 스키마 배선으로 담보행·총액·overview행·귀속률이
  의도적으로 바뀌었다. 표준 +10,300,000(경증치매진단 비고 노출), overview −41,300,000
  (실손 입원·통원 rep 병합 −50,300,000 + 장기요양간병비 비고 노출 +9,000,000)이며,
  월납·회사합=합계·해지 0 전=후·Y/N·death_dedup은 불변이다. 위 표와 `BASELINE`은 같은 승인값이다.
- ★**BOHUMFIT-291(S3) 양식 전환**: 엑셀이 49행 4시트(`표지(세로)`·`컨설팅 전`·`컨설팅 후`·`최종`)로 바뀌어
  프로브의 **엑셀 좌표만** 새 양식(시트 `컨설팅 전`·담보 7행~·합계 F:G 2열·회사당 2열 H~)으로 옮겼다.
  ★BASELINE 수치는 290 승인값 그대로이며 291 산출물에서 **PASS**(회사합=합계 0 · 4시트 구성).
- ★**BOHUMFIT-292(S4) 매칭·분배 배선 — Human ① 승인 반영**: 프로브 좌표는 종수술 위 2열 헤더 삽입분을
  `track_row_of()`로 반영했고, 라금실 enrolled 기준을 **41→42로 갱신**했다 —
  p19#19 `항암약물치료특약` 1,000만이 비고 `항암약물방사선`에서 `항암 약물 치료` 행으로 옮겨진 Phase E 규칙의
  직접 귀결(총액·행 수·월납·overview 불변 · 이인숙 PASS). 사용자 지시로 Human ① 승인이 확정돼
  `BASELINE`과 이 표를 함께 갱신했으며 smoke가 PASS해야 한다.

### ★스키마 정본 (BOHUMFIT-293 · 층위 2 정리 완료)

- **49행 V2가 유일한 산출물 스키마다.** `KB_COVERAGES_V2`(49) · `GROUP12_V2`(11) · `PAYOUT_CASCADE_V2`(17체인)로
  엑셀 4시트(`표지(세로)`·`컨설팅 전`·`컨설팅 후`·`최종`)·PDF·API가 만들어진다. 구 40행 양식은 **폐기**다.
- 구 양식 파생 상수 5종(`NEW_ITEM_ORDER`·`YN_ITEMS`·`STAGE_COMPONENTS`·`STAGE_COMMON_ADD`·`STANDARD_COUNT`)은
  293에서 삭제했다. 되살아나면 `test_schema_v2_287.py`가 실패한다(모듈 속성 검사).
- ★`KB_COVERAGES`·`KB_NAME_ALIASES`·`GROUP12/13`은 **남아 있다** — 이제 "양식"이 아니라 **KB 원문 담보명 사전**
  (`match_coverage`·`coverage_meta` · `agg` → V2 행 sum/rep)과 **구 페이로드 호환 축**이다. 지우려면 파서와
  프런트 미러를 먼저 옮겨야 한다(층위 3). 사유는 `decisions.md`(2026-08-18) 참조.
- **서식 회귀**는 `tests/test_format_regression_293.py`가 실문서 3건으로 막는다 — 차액 색상(261)·합계 강조·
  Q2 메모·Q5 메모·L 접두·2열 헤더·브랜드 색(빨강 0)·인쇄 설정·PDF 고령 가독성·비고 보존.
  ★291에서 261 차액 색상이 조용히 빠진 유형을 겨냥한다(뮤테이션 4종으로 검출력 확인 완료).

### smoke 기준값 이력 — 한곳에

| 시점 | 기준값 변화 | 승인 |
|---|---|---|
| BOHUMFIT-290(S2) | 49행 배선 — 표준 총액 **+10,300,000**(경증치매진단 비고 노출) · overview **−41,300,000**(실손 입원·통원 rep 병합 −50,300,000 + 장기요양간병비 비고 노출 +9,000,000) | Human Q6 |
| BOHUMFIT-291(S3) | **없음** — 프로브의 엑셀 좌표만 새 양식으로(BASELINE 무변경) | — |
| BOHUMFIT-292(S4) | overview 정본 `enrolled 41→42`(`항암약물치료특약` 1,000만이 비고에서 `항암 약물 치료` 행으로 · 총액·월납·overview 불변) | Human ① |
| BOHUMFIT-293 | **없음** — 산출물 12종(4문서 × 엑셀·HTML·payload) 해시 완전 동일(정리만) | — |

★월납·회사합=합계·해지 0 시 전=후·Y/N·death_dedup은 위 전 구간에서 **불변**이다.

### 집계 바이트 증명 — 직렬화 방식 (BOHUMFIT-287·289 Codex 방식 → 290에서 고정)

이후 모든 "산출물 바이트 동일" 증명은 아래 방식으로 한다(다른 방식으로 얻은 해시는 대조 불가).

- 대상: `analyze_kb_coverage(pdf)["before"]`의 **행 단위** `coverages`(kb_name·group12·agg·summary·
  by_company·enrolled·row_id·columns) + `premium` + `yn_flags` + `stage_totals` + `death_dedup`
  + `final.rollup_by_group12` + `final` 행별 status. 입력 6종 = 이인숙·라금실·오현지 [전] + 오현지 [후] 3제안서
  (`parse_proposal_pdf`의 insurer·monthly_premium·coverages 3튜플).
- 직렬화: `json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)` → **sha256**.
- 스크립트는 스크래치에 두고 실행 후 삭제한다(실데이터 산출물 저장 금지). 290 실측:
  배선 전(HEAD `56aa60a`) `a27ced38…` / 배선 후 `ff540eba…` — 차이는 Q6 대조표로 전수 설명됐다.

### 규칙
- ★**실 PDF·산출 xlsx는 저장소에 커밋 금지**(현행 `.gitignore` 유지 — PII). 이 문서에는
  **수치만** 기록하고 성명·주민·전화·주소는 어떤 형태로도 남기지 않는다.
- 파일이 유실되면 **Human이 재확보**한다(재다운로드 또는 대체 실 PDF). 대체본을 쓸 경우
  위 표의 수치는 그 문서 기준으로 갱신하고 갱신 사유를 handoff에 남긴다.
- ★**유형이 다른 2건(표준 1 + overview 1)을 항상 유지**한다. overview 문서가 없으면 239·246
  분기와 overview 회귀(255 계열)를 실데이터로 검증할 수 없다.
- 스모크 실행은 **사용자 동선(엔드포인트 `POST /coverage/export/excel`) 경유**로 한다(249 원칙 —
  "산출물 검증은 사용자 동선 기준"). 상비 자동 대조는 위 `npm run smoke:coverage`이며,
  그 밖의 태스크별 임시 검증 스크립트는 스크래치에 만들고 실행 후 삭제한다(실데이터 산출물 저장 금지).

## 수동 확인 체크리스트

- [ ] (태스크별 수동 확인 항목을 여기에 기록)

Record the exact commands and results in `.agent-harness/handoff.md`.
