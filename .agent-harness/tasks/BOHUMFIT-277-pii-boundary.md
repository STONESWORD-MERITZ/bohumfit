# BOHUMFIT-277 — PII 저장·로그 경계 봉인

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: Claude Code (구현·1차 검증)
Risk tier: ★고위험 — 개인정보 경계. 오픈 전 필수. git 쓰기 금지(커밋 Codex).
Date: 2026-08-07 · 기준 HEAD `c3445ab`(276b) · 선행 조사 BOHUMFIT-275 B 섹션

## 목적
275가 확인한 **개인정보 유출 경로 4건**을 봉인한다.
★설계 원칙: **서버에서 익명화한다**(271이 표시 직전만 처리해 B-F1이 생겼다). 표시 직전
sanitization은 **방어 2선**으로 남긴다. 파일 식별자는 응답·로그·저장 **전에** 익명 slot으로 정규화한다.

---

## Step 1 — 실측 (코드 무변경)

### ★파일 식별자 전 경로 추적 — 원본 파일명이 어디서 들어와 어디까지 흐르는가
| # | 지점 | 코드 | 원본 파일명 존재 |
|---|---|---|---|
| ① 진입 | 업로드 `UploadFile.filename` | `main.py` `/api/analyze` | ✔ |
| ② 파싱 | `parse_single_pdf` → `parse_errors`에 `🔒 {파일명}: {사유}` | `pipeline/pdf_parser.py:368~384` | ✔ |
| ③ 성공 로그 | `"…parsed: file=%s …"` | `analyzer.py:243~248` | ★**Railway 로그에 기록** |
| ④ 실패 로그 | `"…parse failed: file=%s error=%s"` (순차) / `(parallel)` | `analyzer.py:281~283`·`315~319` | ★**기록** |
| ⑤ 실패 문구 | `f"⚠️ {fn}: PDF 파싱 중 예외 — …"` | `analyzer.py:282`·`320` | ✔ |
| ⑥ 응답 raw | `result["parse_errors"]` | `/api/analyze` 응답 | ★**클라이언트로 나감** |
| ⑦ DB 저장 | `_history_record_recent`가 `payload.pop("customer_name")` **만** 수행 | `main.py:1505~1527` | ★**7일 저장** |
| ⑧ saved 저장 | 동일 패턴 | `main.py:1559~1564` | ★**90일 저장** |
| ⑨ 화면 | `sanitizeParseErrors`로 `서류 N` 치환 | `errorMessages.ts:136~163` | ✖ (271이 막음) |
| ⑩ 진행 티커 | `"filename": f"서류 {N}"` — 원본 저장 금지 | `progress.py:79` | ✖ (268b가 막음) |

→ ★**271은 ⑨ 한 곳만 막았다.** ③④⑥⑦⑧이 전부 열려 있다. 봉인 지점은 **②~⑤가 만들어지는 서버**다.

### ★익명 slot 규칙 — 이미 두 곳에 선례가 있고 서로 같다
- 268b: `progress.py:79` → `f"서류 {len(job['files']) + 1}"` (1-based 등장 순서)
- 271: `errorMessages.ts:158` → `서류 ${index + 1}` (1-based `parse_errors` 순서)
→ **`서류 {1-based index}`** 로 통일한다. 서버가 같은 규칙으로 먼저 정규화하면 ⑨의 재정규화는
멱등이 되어 방어 2선이 그대로 유지된다.

### `sessionStorage` 저장/복원 vs 삭제 계약의 간극
| 항목 | 현행 |
|---|---|
| 저장 | `Disclosure.tsx:2097`·`2139` — `{ result, ts }` **user id 없음**, 10분 |
| 복원 | `:1963~1976` — `ts`만 검사, **현재 사용자와 대조 없음** |
| 삭제 | `:2415`(새 분석 시작 시) 뿐 |
| 삭제 계약 | `auth-context.tsx:32~45` 단일 지점이 **`clearAnalysisCache()`(IndexedDB)만** 호출 |
→ ★**`sessionStorage`는 삭제 계약 밖**이다. 275 B-2가 "5경로가 한 계약으로 연결된다"고 판정한 것은
IndexedDB 한정이고, 이 키는 포함되지 않는다. **A 분석 → 로그아웃 → 10분 내 B 로그인 → A 결과 복원**이 성립한다.

### history deep scrub 필요 필드
`payload.pop("customer_name")` 하나뿐이라 아래가 그대로 저장된다:
- `parse_errors[]` — ★원본 파일명(본 태스크 표적)
- `standard_reports`/`easy_reports` 내부 병원명·상병코드·병명 — **의도 저장**(275 B-1 3항: 히스토리는
  고객명만 제거하고 건강정보 결과는 보관). ★이번 범위는 **파일명 한정**이고 건강정보 보관 정책은 손대지 않는다.

### Sentry·콘솔 현행
- 프런트 `main.tsx:21~25`: `event.request.data`·`cookies`만 삭제. **breadcrumb·exception 문자열 미처리**.
- `errorMessages.ts:129~132`: 미매핑 원문을 `console.warn`에 그대로 출력 → breadcrumb로 Sentry 전송 가능.
- 백엔드 `main.py:135~173`: `_scrub_sensitive_event_values`가 **키 기반**이라 이미 포맷된 문자열 안의
  파일명은 남는다.

### ★기존 DB 저장분 (범위 밖 · Human 정책 결정)
`recent`(7일)·`saved`(90일) 테이블의 기존 `result.parse_errors`에 원본 파일명이 남아 있을 수 있다.
- **대상 추정**: parse error가 발생한 분석에 한정된다. 정상 분석은 `parse_errors`가 비어 영향 없다.
- ★**실제 건수는 확인 불가** — 운영 DB에 접근하지 않았다(조회 자체가 PII 열람이다).
- recent는 7일 후 자동 만료되지만 **saved(90일)는 사용자가 지우기 전까지 남는다**.
→ 정리 여부·방식은 Human 데이터 정책 결정 사안으로 남긴다.

---

## Step 2~5 — 구현

### Step 2 (B-F3) — 세션 결과에 소유자 바인딩 + 삭제 계약 편입
`src/lib/sessionResultQueue.ts` **신설**(저장·복원·삭제를 한 파일에 모아 계약에서 다시 빠질 수 없게).
- 레코드에 `uid` 추가. 복원 시 **현재 사용자와 대조**하고, 불일치·비로그인·`uid` 미기록(277 이전 레코드)·
  TTL 초과·파싱 실패면 **읽지 않고 삭제**한다.
- ★비로그인 상태에서는 **저장도 하지 않는다**(주인 없는 건강정보를 남기지 않는다).
- `AuthContext.tsx`의 **단일 삭제 지점**(사용자 id 전이)과 카카오 이탈 flush에 `clearSessionResult()` 추가 —
  ★265 구조는 그대로 두고 **키만 추가**했다. 275 B-2의 5경로가 자동으로 커버된다.
- `Disclosure.tsx`는 `sessionStorage`를 **직접 만지지 않는다**(계약 우회 방지·테스트로 고정).

### Step 3 (B-F1) — 서버에서 익명화 + 저장 전 deep scrub
`backend/pii.py` **신설** — slot 규칙은 268b·271과 **같은 `서류 {1-based}`**.
- `analyzer.py`가 `pr["parse_errors"]`를 **응답에 나가기 전에** `anonymize_parse_errors()`로 정규화
  (순차·병렬 두 경로 모두). ★`pipeline/pdf_parser.py`는 **무접촉**이다.
- history 저장 **두 경로 모두**(recent 7일·saved 90일) `scrub_pdf_filenames_deep()` 통과 —
  최상위 `customer_name`만 지우던 것을 중첩 전체로 넓혔다.
- ★271의 표시 직전 `sanitizeParseErrors`는 **제거하지 않았다**(방어 2선). 서버가 먼저 같은 규칙으로
  정규화하므로 프런트 재정규화는 **멱등**이다(테스트로 고정).

### Step 4 (B-F2) — 로그
성공 로그 `file=%s`를 `document_slot(index)`로 교체. 실패 로그(순차·병렬)도 slot을 쓰고,
★**예외 문자열도 `mask_filenames()`를 통과**시킨다(예외 메시지에 경로·파일명이 섞일 수 있다).

### Step 5 (B-F5) — 콘솔·Sentry
- `errorMessages.ts`에 `scrubPii()` 추가 → 미매핑 원문 `console.warn`에 적용
  (콘솔은 Sentry breadcrumb로 실려 나간다).
- `main.tsx` `beforeSend`에 **message·breadcrumbs(+data)·exception.values** scrub 추가.
  기존 request data/cookies 삭제는 유지.
- 백엔드 `_scrub_sensitive_event_values`를 **키 기반 → 최종 문자열 검사까지** 확장.

---

## 검증 결과 (1차 · 2026-08-07 · Windows 로컬)

### ★★E2E — 실명 형태의 가상 파일명(`가상고객A 최근 3개월.pdf`)으로 parse error 유발
| 경로 | 결과 |
|---|---|
| 서버 응답 raw `parse_errors` | `🔒 서류 1: PDF 비밀번호 해제 실패 — …` · **파일명·실명 0** |
| 운영 로그 | `BOHUMFIT-047 parsed: file=서류 1 …` · **파일명·실명 0** |
| history payload(저장 직전) | **실명 0** |
| 화면(271 방어 2선) | `서류 1: …` — 여전히 동작 |

### 게이트
- [x] backend `pytest -q` **874 passed, 8 skipped** — 기준선 861 + **신규 13**, **기존 회귀 0**
- [x] `npm test` **363 passed** — 기준선 342 + **신규 21**, 회귀 0
- [x] `npm run smoke:coverage` **PASS**(정본 2건 기준값 완전 불변) · tsc app/node · lint
- [x] `npm run build:verify` **343,702 B 예상 FAIL**(248 껍데기)
- [x] ★**데스크톱 회귀 0** — HEAD 사본 대비 `/disclosure` 결과·`/history` `innerHTML`·노드 수 **완전 일치**
      (★`src/pages/Disclosure.tsx` diff에 **JSX 변경 0** — 저장 계층만 바뀌었다). 사본·스크립트 삭제.
- [x] ★B-F3 실동작 11건: 계정 전환 미복원·레코드 폐기 / 같은 사용자 정상 복원 / 비로그인 삭제·미저장 /
      277 이전 레코드 폐기 / TTL / 깨진 레코드 / 멱등 / **삭제 계약 배선 3건**
- [x] ★271 방어 2선 유지(서버 정규화 실패해도 화면엔 파일명 0) · 슬롯 규칙 268b와 동일(소스 고정)
- [x] ★보호 영역 **diff 0**: `backend/pipeline/`·`filters.py`·`backend/coverage/`·`vite.config.ts`·
      `src/components/mobile/`(270·273 무접촉) · **`PrivacyPolicy.tsx`·`ConsentGate.tsx`·`analysisCache.ts` diff 0**(279 범위)

### ★한계 — 최후 방어선이 못 잡는 경우 (기록)
`scrub_pdf_filenames_deep()`은 ①`{이모지} {파일명}.pdf: {사유}` **접두 구간** ②문장 속 `*.pdf` 토큰을 지운다.
그러나 **문장 중간에 공백을 포함한 한글 파일명이 박힌 경우**(`"본문에 홍길동 검진.pdf 포함"` → `"본문에 홍길동 서류 포함"`)
앞의 실명이 남는다. 정상 경로는 `analyzer`가 **실제 파일명 목록을 알고** 정확히 마스킹하므로 이 한계에 걸리지 않는다.
이 함수는 어디까지나 **최후 방어선**이며, 완전 방어가 필요하면 파일명을 아는 지점에서 마스킹해야 한다.

### ★기존 DB 저장분 — 범위 밖 · Human 정책 결정
- `recent`(7일)는 자동 만료되지만 **`saved`(90일)는 사용자가 지우기 전까지 남는다**.
- 대상은 **parse error가 발생한 분석에 한정**된다(정상 분석은 `parse_errors`가 비어 영향 없음).
- ★**실제 건수 확인 불가** — 운영 DB에 접근하지 않았다(조회 자체가 PII 열람이다).

### 범위 밖(279)으로 남긴 것
B-F4(오프라인 캐시 미배선 ↔ 방침 문구 불일치)와 개인정보처리방침·동의문은 **손대지 않았다**
(`PrivacyPolicy.tsx`·`ConsentGate.tsx`·`analysisCache.ts` diff 0).
★단 277이 `sessionStorage` 10분 보관에 소유자 바인딩을 넣었으므로, 279가 방침 문구를 정리할 때
**"세션 10분 임시 보관"이 문구에 없다는 275 B-F4 지적**을 함께 다뤄야 한다.

---

## 2차 검증 보강 (2026-08-07 야간 세션 · 코드 변경 0)

★재발행 패킷이 새로 요구한 항목과, 1차에서 못 채운 체크리스트를 보강했다. **제품 코드는 한 줄도 바뀌지 않았다**
(워킹트리 diff는 1차와 동일). 게이트 재현: backend **874 passed, 8 skipped** · `npm test` **363** ·
`smoke:coverage` PASS · tsc app/node · lint 클린.

### ★신규 요구 — 운영 진단 가능성 유지 (실측)
파일 3건이 각각 실패하는 상황을 만들어 로그·문구를 확인했다.
```
BOHUMFIT-047 parsed: file=서류 1 records=0 ftype={} errors=1
BOHUMFIT-047 parsed: file=서류 2 records=0 ftype={} errors=1
BOHUMFIT-047 parsed: file=서류 3 records=0 ftype={} errors=1
🔒 서류 1: PDF 비밀번호 해제 실패 — 생년월일을 확인해 주세요.
```
| 항목 | 결과 |
|---|---|
| 원본 파일명·실명 | **0** |
| **몇 번째 파일인지** | ★`서류 1`·`서류 2`·`서류 3` — 전부 식별 가능 |
| **왜 실패했는지** | ★`PDF 비밀번호 해제 실패` 등 사유 유지 |
| 레코드 수·유형·오류 수 | `records`·`ftype`·`errors` 유지 |
→ **PII만 제거되고 진단 정보는 그대로**다(패킷 설계 원칙 충족).

### ★★B-F3 — **실브라우저** 검증 (Vite dev + 실제 모듈)
★1차 검증 때 "로컬 빌드 불가(248)"를 근거로 실브라우저를 시도하지 않았는데, **248은 `npm run build`
한정**이고 **dev 서버는 정상 기동**한다(실측: `VITE v8.0.10 ready in 745ms`). 그래서 실제 브라우저에서
Vite가 변환한 **`src/lib/sessionResultQueue.ts` 모듈 그 자체**를 불러 계약을 검증했다(jsdom 아님).

| # | 검증 | 결과 |
|---|---|---|
| 1 | A 저장 시 레코드 존재 | ✔ |
| 2 | ★**B가 A 결과를 복원** | ✖ **복원 안 됨** |
| 3 | ★불일치 시 레코드 폐기 | ✔ |
| 4 | 같은 사용자 정상 복원 | ✔ (기능 회귀 0) |
| 5·6 | 비로그인 복원 / 폐기 | ✖ 복원 안 됨 · ✔ 폐기 |
| 7 | 비로그인 저장 | ✖ 저장 안 됨 |
| 8·9 | 277 이전 레코드(uid 없음) 복원 / 폐기 | ✖ · ✔ |
| 10 | TTL 초과 복원 | ✖ |
| 11 | ★**B 진입 후 저장소에 건강정보 잔존** | ✖ **없음** (A 저장 시엔 있었음 — 대조 확인) |

★11번이 핵심이다 — "복원만 막고 데이터는 남는" 상태가 아니라 **실제로 지워진다**.

### ★확인 불가 (야간 세션 · 사유 명시)
1. **실제 2계정 로그인 전환 E2E** — dev 서버는 뜨지만 Supabase 자격증명이 없어 로그인 동선을 태울 수 없다.
   위 실브라우저 검증은 **저장소 계약**을 실제 모듈로 증명한 것이고, `AuthContext`의 id 전이 시 호출은
   소스 계약 테스트로만 고정돼 있다(`sessionResultQueue.test.ts` 배선 3건).
2. **데스크톱 4경로 중 `/dashboard`·`/coverage-compare` 실브라우저 렌더** — 두 라우트 모두
   `ProtectedRoute` 뒤라 로그인 없이는 렌더되지 않는다. 두 페이지 **소스 diff 0**이고 `AuthContext` 변경은
   `onAuthStateChange` 콜백·`signOut` 내부라 **렌더 경로가 아니다**(diff 전수 확인). 렌더 자체는 기존
   스위트(`mobileHome`·`CoverageRemodelResponsive`·`CoverageRemodelUx182`·`PublicRoutesSmoke`)가 덮는다.
3. **운영 DB 기존 저장분** — 1차와 동일하게 접근하지 않았다(조회 자체가 PII 열람).

### 범위 격리 재확인 (diff 0)
| 범위 | 대상 | 결과 |
|---|---|---|
| **279** | `PrivacyPolicy.tsx`·`TermsOfService.tsx`·`ConsentGate.tsx`·`analysisCache.ts` | **diff 0** |
| **278** | `src/components/mobile/`·`Layout.tsx`·`src/index.css` | **diff 0** |
| 276a/b·272·273·270·269b | `backend/coverage/`·`backend/pipeline/`·`filters.py`·`vite.config.ts` | **diff 0** |

## Stage 목록 (Codex용)
변경된 백엔드·프런트 소스 + 277 테스트,
`.agent-harness/tasks/BOHUMFIT-277-pii-boundary.md`, `handoff.md`, `locks.md`
★기준선 변동 시 `verify.md`·`CLAUDE.md`·**`AGENTS.md` 3문서 모두**
※제외: 실 PDF·PII·산출물

## 커밋 메시지 (Codex용)
fix(BOHUMFIT-277): PII 저장·로그 경계 봉인(계정 전환 누수·raw 파일명·로그·Sentry)
