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

## 검증 기준선 (BOHUMFIT-268a 실측 · 2026-08-02 갱신)

백엔드 pytest — `cd backend && python -m pytest -q`:

```text
792 passed, 8 skipped
```

(BOHUMFIT-262 실측·2026-07-31 갱신 — 255 시점 750/8에서 256~261 신규분 반영.)

프런트 테스트 — `npm test`(라우트 스모크 18건 포함):

```text
217 passed / 27 files
```

(BOHUMFIT-268a 실측·2026-08-02 갱신 — 267 시점 203/26에 모바일 업로드 회귀 14건 반영.)

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
  근본 해결 후보: 정책 예외 등록(Human·관리자) / WSL·CI 빌드 검증 — 카탈로그 참조.

기준선 수치가 바뀌면 이 파일과 `CLAUDE.md`·`AGENTS.md`를 함께 갱신한다.

## 스모크 정본 세트 (BOHUMFIT-255 P2 · 2026-07-29 신설)

보장분석(coverage) 트랙의 실데이터 회귀는 아래 **2케이스를 정본**으로 한다. 2026-07-29 시점에
기존 5케이스 중 3건이 삭제돼(임의 정리) 회귀 근거가 끊긴 사고가 있었다 — 재발 방지를 위해
**파일 없이도 복구·판정이 가능하도록 기준 수치를 여기에 고정**한다.

| 케이스 | 유형 | 파일(로컬 전용) | 계약 | 담보행/enrolled | 총액 | 월납(부값) | overview행 | 파싱 경고 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 표준(계약별 매트릭스) | 상품별 가입현황 존재 | `보장분석\비교분석표\이*숙-INPUT.pdf` | 15 | 46/29 | 604,560,000 | 681,312 (531,312) | 0 | 0 |
| overview(합계-only) | 239 fallback(매트릭스 부재) | `보장분석\비교분석표\라*실INPUT.pdf` | 15 | 54/42 | 1,542,990,000 | 4,675,189 (4,675,189) | 26 | 1 |

- 기준일 `today="2026-07-29"`, 해지 0(`build_after_analysis(..., {"existing": [], "proposals": []})`)
  기준값이며, 두 케이스 모두 **해지 0에서 [전]=[후] 상이 0**이 성립해야 한다.
- 표준 케이스 추가 고정값: 회사합=합계 대사 [전]/[후] 상이 0, Y/N 회사별 = payload 파생 일치
  (자동차부상=계약3·가족일상=계약7만 Y), 보험료 셀은 9행(254 개정)·계약 idx 7은 월납 None(공란).
- overview 케이스 추가 고정값: 회사 열 미생성·합계 열만·특이사항 경고 유지(246/239),
  overview 담보 26종 합계 1,400,240,000.

### 자동 대조 (BOHUMFIT-262 P5)

```powershell
npm run smoke:coverage
```

- 위 표의 기준값과 실 산출을 대조하고 **불일치 시 exit 1**로 실패한다(248 `build:verify` 선례).
- 계약 수·담보행/enrolled·총액·월납(부값)·overview행/합계·귀속률에 더해 **회사합=합계 0**
  (payload·엑셀 시트2 양쪽)·**해지 0 시 전=후 0**·**`'?'` 잔존 0**·3시트 구성을 항상 검사한다.
- 실 PDF가 없으면 **경고 후 건너뜀(exit 0)** — CI·타 환경에서 깨지지 않는다(PII로 커밋 불가).
- 기준값은 `scripts/smoke-coverage.mjs`의 `BASELINE`에 있다. ★위 표를 고칠 때 함께 갱신한다.

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
