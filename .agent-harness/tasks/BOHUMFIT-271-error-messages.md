# BOHUMFIT-271 — 오류 문구 표준화 (262 D-13 확정분)

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: Claude Code (구현·1차 검증) · ★야간 무인 세션
Risk tier: 중위험 — git 쓰기 **일절 금지**(읽기만). 커밋은 Codex.
Date: 2026-08-03 · 기준 HEAD `04bef53`(268b)
※워킹트리에 **269a·269b 미커밋분 공존** — ★건드리지 않았다. Codex는 269a → 269b → 271 순서로 분리 커밋할 것.

## Step 1 — 현행 실측 (코드 무변경)

### ★명세 전제 부분 정정 — 백엔드 `detail`은 이미 사용자 문구다
명세는 "백엔드 `detail`이 그대로 노출된다"를 문제로 봤는데, 실측하니 `backend/main.py`의 `detail` 60여 개가
**이미 한국어 존댓말**이다(예: "PDF 파일만 업로드할 수 있어요.", "잠시 후 다시 시도해 주세요.").
기술 용어·에러 코드가 새는 지점은 **따로 있었다**. 재설계가 필요한 수준은 아니라 목적(행동 지침형)은 유지하고,
아래 **실제 결함 3가지**를 표적으로 삼는다.

### 실제 결함 3가지
1. ★**클라이언트 검증 문구에 파일명(PII)이 들어간다** — `Disclosure.tsx:1995` `(${nonPdf.name})`,
   `:2000` `(${tooLarge.name})`. 268b가 서버 저장 파일명을 "서류 N"으로 익명화한 기조와 어긋난다.
2. ★**미매핑 오류가 원문 그대로 샌다** — `Disclosure.tsx:2108`·`CoverageRemodel.tsx:401,444`가
   `e.message`를 그대로 뿌린다. 서버가 예상 못 한 오류(500 본문, 프록시 HTML 등)를 내면 기술 문구가 노출된다.
3. **원인만 있고 다음 행동이 없는 문구**가 있다 — "PDF는 최대 10개까지 업로드할 수 있습니다."처럼
   무엇을 하면 되는지가 빠져 있다.

### 오류 노출 지점 전수
| 지점 | 현재 | 271 처리 |
|---|---|---|
| `Disclosure` 클라이언트 검증(1986~2013) | 자체 문구 · **파일명 포함 2건** | 사전 문구로 교체(PII 제거) |
| `Disclosure` 분석 실패(2106~2108) | 네트워크는 전용 문구 · 그 외 **`e.message` 원문** | 사전 → 폴백 |
| `CoverageRemodel` 업로드(401) | **`uploadError.message` 원문** | 사전 → 폴백 |
| `CoverageRemodel` 내보내기(444) | **`exportError.message` 원문** | 사전 → 폴백 |
| 268a `uploadWithProgress`(XHR) | `detail` 우선 → `UploadError.message` | ★**구조 변경 없이** 호출부에서 사전 통과 |
| 268b 폴링 실패 | **이미 조용한 폴백**(문구 없음) | ★**그대로 둔다**(분석은 진행 중) |

### 백엔드 `detail` 주요 값(수집 요약)
파일 형식/개수/크기(`PDF 파일만…`·`최대 N개…`·`개별 PDF 크기…`·`전체 PDF 합계…`) ·
`PDF에서 진료 데이터를 추출하지 못했습니다` · `🔒 …비밀번호가 걸린 PDF입니다` ·
`무료 분석 최초 N회를 모두 사용했습니다`(402) · `로그인이 필요합니다` ·
`분석이 시간 내에 끝나지 않았어요`(504) · `서버에서 분석을 완료하지 못했어요`(500) ·
히스토리·결제·인증 계열 다수.

### 268a `detail` 규약은 깨지 않는다
`uploadWithProgress`는 응답 JSON의 `detail`을 `UploadError.message`로 싣고 `status`를 보존한다.
271은 **그 위에서 표시 직전에만** 사전을 적용한다 — 402 판정(`status === 402`)은 그대로라 159 업셀 동선도 유지된다.

## Step 2~4 — 구현
- `src/lib/errorMessages.ts` 신설: `detail`/`Error` → **행동 지침형 문구** 단일 사전.
  · 부분 일치 규칙(백엔드가 숫자를 채워 보내므로 완전 일치로는 안 잡힌다)
  · ★미매핑은 **폴백 문구**, 원문은 화면에 내보내지 않고 **`console.warn`으로만** 남긴다(개발 진단용)
  · ★문구에 파일명·환자명·에러 코드·기술 용어를 넣지 않는다
- 적용: `Disclosure`(검증·분석 실패), `CoverageRemodel`(업로드·내보내기). 268b 폴링은 **무변경**.

## 검증 결과 (1차 · 2026-08-03 · Windows 로컬 · 야간 무인)

- [x] tsc app/node **PASS** · `npm run lint` **PASS**
- [x] `npm test` **304 passed / 33 files**(기준선 278 + 신규 **26**) · 회귀 0
- [x] backend `pytest -q` **818 passed, 8 skipped**(불변) · ★**`backend/` diff 0**
- [x] `npm run smoke:coverage` **PASS**
- [x] `npm run build:verify` **예상 FAIL** — 수치가 **343,225 → 343,702 B**로 늘었다(사전 모듈 +477 B).
      껍데기 상태(248 이슈)는 그대로이므로 판정은 종전과 같다.
- [x] ★**정상 경로 데스크톱 회귀 0** — HEAD 사본 대비 `CoverageRemodel` 결과 화면 `innerHTML`·노드 수
      **완전 일치**(271은 오류 경로만 바꿨다). 빈 화면 오통과 방지 마커 포함. 사본·스크립트 **삭제**.
- [x] ★**XHR·fetch 양 경로 문구 동일** — 두 화면이 같은 `toUserErrorMessage`를 쓴다(소스로 고정).
- [x] ★**미매핑 → 폴백** — 모르는 오류·HTML 응답·빈 값·null 전부 폴백 문구. 원문은 **`console.warn`으로만**.
- [x] ★**PII·기술 용어 0** — 사전 전 문구를 전수 검사(파일명·확장자·환자 표현·기술 흔적 0).
      ★파일명을 섞어 넣어도 문구에 반영되지 않음을 테스트로 고정.
- [x] ★**268b 폴링 실패는 여전히 조용** — `analysisProgress.ts`에 `toUserErrorMessage`·`setError` **0건**.
- [x] ★**268a `detail` 규약 무변경** — `uploadWithProgress`에 사전이 들어가지 않았고 `payload.detail`·
      `UploadError`가 그대로다. 402 판정은 `status`로 하므로 **159 업셀 동선 유지**.
- [x] `vite.config.*` diff 0 · 라우트 변경 0 · 265 캐시·Q1~Q5 배지·판정·요금제/결제/인증 무접촉
- [x] ★**269a·269b 미커밋분 무접촉** — 271이 손댄 파일은 `errorMessages.ts`(신규)·`Disclosure.tsx`·
      `CoverageRemodel.tsx`·`errorMessages.test.ts`(신규) **4개뿐**이다.

### 구현 요약
- `src/lib/errorMessages.ts` — 부분 일치 규칙 사전 + 폴백. 원문은 화면에 절대 내보내지 않는다.
- `Disclosure.tsx` — 클라이언트 검증 7건 + 분석 실패 catch. ★**파일명 삽입 2건 제거**(PII).
  네트워크 단절은 기존 `connectionErrorMessage`(API 주소 확인 안내 포함)가 더 유용해 **그대로 뒀다**.
  화면 문구와 토스트 문구를 **같은 값**으로 통일했다(예전엔 서로 달랐다).
- `CoverageRemodel.tsx` — 업로드·내보내기 실패 2건.

### 자체 정정 1건
"전체 PDF 합계 크기…"가 "개별 PDF 크기…" 규칙에 먼저 걸렸다(두 문구가 "크기는 … 넘을 수 없습니다"를 공유).
→ **전체 합계 규칙을 앞으로** 옮기고 사유를 주석에 남겼다.

### ★워킹트리 이상 신호 (건드리지 않음 · 기록만)
271 작업 중 워킹트리에 **내가 만들지 않은 파일 4개**가 나타났다:
`.codex-269-browser.html` · `.codex-269-vite.config.mjs` · `src/__codex269Browser.tsx` · `src/__codex269Supabase.ts`
(타임스탬프 20:16~20:19 — 271 작업과 **동시간대**). 이름으로 보아 **Codex의 269 브라우저 검증용 임시 파일**로
보인다. 야간 규칙(막히면 멈춘다·남의 변경분을 건드리지 않는다)에 따라 **삭제·수정하지 않고 기록만** 한다.
→ ★Codex가 269 커밋 시 **stage에서 제외**하거나 정리해야 한다.

### 로컬에서 못 한 것 (Codex 몫)
- 375/390/430px에서 **문구 잘림·넘침** 실측(jsdom은 레이아웃을 계산하지 않는다)
- 실제 서버 오류를 유발한 엔드투엔드 확인(파일 형식·크기·402·타임아웃)

## Codex 2차 검증 — PASS (2026-08-04)

- **전체 게이트 재현**: tsc app/node · lint · `npm test` **304 passed / 33 files** · backend
  **818 passed, 8 skipped** 불변 · `smoke:coverage` 정본 2건 PASS · `build:verify` **343,702 B 예상 FAIL**
  (248 계약 — 껍데기 상태 동일, +477 B는 사전 모듈분).
- **★중점 A — 실 오류 화면 확인(jsdom 실렌더 8케이스)**: ①PDF 아닌 파일 → "PDF 파일만 올릴 수 있어요"
  문구에 **파일명 미포함**(선택 파일 목록 UI는 171a 기존 기능이라 대상 아님 — 오류 요소로 스코프해 확인)
  ②개수 초과 → "나눠서 올려 주세요" ③★**개별 크기 vs 전체 합계 구분 정확**(1차가 규칙 순서를 조정한 지점 —
  16MB 단일 파일은 개별 문구, 14MB×3은 합계 문구가 나오고 서로 섞이지 않음) ④비밀번호 PDF(서버 400) →
  생년월일 안내·서버 detail의 파일명 미노출 ⑤★**402 → 오류 폴백이 아니라 159 업셀 카드**("무료 분석 5회를
  모두 사용했어요") ⑥인증 만료(401) → 다시 로그인 안내 ⑦★미매핑(502 HTML) → 폴백만 표시, "nginx"·"502"
  화면 미노출 ⑧원문은 `console.warn` 경로로만.
- **중점 B**: XHR(모바일)·fetch(데스크톱)가 같은 catch → 같은 `toUserErrorMessage`를 통과함을 소스·테스트로
  확인(1차 `errorMessages.test.ts`가 고정). 375~430px 문구 넘침은 문구가 `break-keep` 일반 플로우 요소라
  구조상 넘침 없음 — 실기기 확인은 Human 검수 항목에 편승.
- **중점 C**: 268b 폴링 조용한 폴백 유지(`analysisProgress.ts`에 사전·setError 0건) · 268a
  `uploadWithProgress` diff 0 · `detail`·`status` 보존으로 402 판정 경로 무손상.
- **중점 D**: 사전 전 문구 PII·기술 용어 0(전수 테스트) + 환자명 포함 파일명으로 실제 오류를 내도
  오류 문구에 미반영(위 ①·④ 실측).
- **중점 E**: ★정상 경로 데스크톱 회귀 0 — HEAD(269b 포함) 사본 대비 **Disclosure 결과 화면·CoverageRemodel
  결과 화면 `innerHTML`·노드 수 완전 일치**(사본·일회성 스크립트 삭제).
- **중점 F**: `backend/` diff 0 · `vite.config.*` diff 0 · 265 캐시·배지·판정·요금제/결제/인증·라우트 무접촉.
- **워킹트리 정리**: 1차가 보고한 `codex269` 임시 파일 4개는 **이미 삭제돼 있었고 어떤 커밋에도 미포함**
  (269a `d6059b0`·269b `6333119` stat 검사로 확인). ★향후 검증 임시 파일은 레포 밖(%TEMP%)에 만든다(메모).
- **기준선 갱신**: `verify.md`·`CLAUDE.md` 프런트 **304 passed / 33 files** · ★build:verify 안내에
  "**약 343 kB로 코드 증가에 따라 변동** — 특정 바이트 일치를 판정 근거로 쓰지 말 것" 명시(패킷 지시).
- **검증 하네스 자체 정정 2건**(제품 코드 무변경): ①user-event v14의 `applyAccept`는 **setup 옵션**이라
  호출별 인자로는 무시됨 → setup으로 이동 ②파일명 부재 단언이 선택 파일 목록 UI(171a 기존 기능)까지 잡아
  오류 요소로 스코프 정정.

## Stage 목록 (Codex용)
`src/lib/errorMessages.ts`(신규)·`src/pages/Disclosure.tsx`·`src/pages/CoverageRemodel.tsx`·테스트,
`tasks/BOHUMFIT-271-error-messages.md`, `handoff.md`, `locks.md`
※제외: 실 PDF·PII·엑셀 원본·시안 HTML·렌더 산출물 · **269a·269b 변경분**

## 커밋 메시지 (Codex용)
feat(BOHUMFIT-271): 오류 문구 표준화(행동 지침형 사전·XHR/fetch 통일)
