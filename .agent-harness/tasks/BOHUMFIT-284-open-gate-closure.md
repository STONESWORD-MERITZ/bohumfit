# BOHUMFIT-284 — 오픈 게이트 마감 (rate limit·응답 표면·업로드 상한)

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: Claude Code (구현·1차 검증)
Risk tier: 중~고위험 — 보안 경계(rate limit)·업로드 입구. git 쓰기 금지(커밋 Codex).
Date: 2026-08-10 · 기준 HEAD `329a630` · 선행 BOHUMFIT-283(F-3·F-6·F-7)

## 배경
283 판정 **조건부 오픈 가능**의 조건 3개 중 2개(실기기 검수·DB 정리)는 Human이 완료했다.
남은 **F-6**을 닫고 **F-3·F-7 최소 방어**를 함께 처리한다.

---

## Step 1 — 실측 (코드 무변경)

### T1 — limiter 미적용 4종 현황 (283 목록 그대로 재확인)
| 엔드포인트 | limiter | 인증 | `request: Request` 인자 |
|---|---|---|---|
| `POST /billing/webhook` | ✖ | 없음(외부 콜백 · HMAC 서명 검증) | ✔ 있음 |
| `GET /billing/status` | ✖ | `verify_jwt` | ✖ **없음** |
| `GET /admin/tier/list` | ✖ | `verify_jwt` + `_require_tier_admin` | ✖ **없음** |
| `POST /admin/tier/set` | ✖ | `verify_jwt` + `_require_tier_admin` | ✖ **없음** |
★slowapi는 시그니처에 `request: Request`가 있어야 동작한다 — 3종은 **인자 추가가 선행**돼야 한다.

### 기존 한도 분포 (새 정책을 만들지 않기 위한 근거)
| 성격 | 기존 한도 | 해당 엔드포인트 |
|---|---|---|
| 조회(읽기) | **60/minute** | 히스토리 조회 계열(`main.py:1628,1680`) |
| 일반 쓰기·파싱 | **20/minute** | coverage 파싱·저장 계열 |
| 결제·발급 | **10/minute** | `POST /billing/issue-key`(`:854`) |
| 무거운 생성 | 10/minute,60/hour | 리포트·엑셀 |
| 분석 | 5/minute,30/hour | `/api/analyze` |
| 진행 폴링 | 120/minute | `/api/analyze/progress` |

### T3 — 실사용 최대치 실측 (읽기 전용, 로컬 정본 6건)
| 쪽수 | 파일 크기 | 콘텐츠 스트림(압축 해제) | 이미지 원시 바이트 | 문서 |
|---:|---:|---:|---:|---|
| 28 | 7,233,962 | 1,736,420 | 120,579,439 | 20260729_우O균님_보장분석 |
| 27 | 7,158,166 | 1,592,118 | 116,597,576 | 20260804_오현지님_보장분석 |
| 10 | 643,231 | 316,567 | 0 | BohumFit_보장분석_우상균 |
| 30 | 4,821,010 | 1,168,268 | 127,864,223 | 라금실INPUT |
| 26 | 929,473 | 2,665,001 | 8,384,991 | 오현지 가입제안서 |
| **42** | 6,976,362 | 2,644,160 | **174,628,166** | 이인숙-INPUT |

★**진료내역(심평원) 경로의 실사용 최대치는 318쪽**이다 — 로컬에 표본은 없으나
`main.py:619` 주석(BOHUMFIT-BUG-006)에 "318p 대용량 PDF"가 **실사용 사고 기록**으로 남아 있다.
정본 6건의 최대 42쪽만 보고 상한을 잡으면 **정상 사용을 막는다**.

### 상한값 근거 (여유 배수)
| 상한 | 값 | 근거 |
|---|---|---|
| `MAX_PDF_PAGES` | **1,000쪽** | 실사용 확인 최대 **318쪽의 3.1배** · 정본 최대 42쪽의 23.8배 |
| `MAX_PDF_CONTENT_BYTES` | **200 MB** | 실측 최대 2,665,001 B의 **75배**. 1,000쪽 × 실측 밀도(63 KB/쪽) = 63 MB의 3.2배 |
| `MAX_PDF_IMAGE_BYTES` | **4 GB** | 실측 최대 174,628,166 B의 **23배**. ★진짜 상한은 파일 크기 15 MB다 — 실측 최대 압축비 **25.0배**(174,628,166 / 6,976,362)를 15 MB에 적용해도 375 MB이므로 **10.7배 여유** |

### 가드 비용 실측 (정상 사용을 막지 않는지)
| 쪽수 | 가드 | 전체 파싱 | 비중 |
|---:|---:|---:|---:|
| 28 | 0.02s | 3.95s | 0.5% |
| 27 | 0.02s | 4.11s | 0.5% |
| 10 | 0.06s | 1.72s | 3.3% |
| 30 | 0.02s | 3.09s | 0.7% |
| 26 | 0.02s | 7.45s | 0.3% |
| 42 | 0.02s | 6.89s | 0.2% |
★이미지 dict 스캔(압축 해제 없음)도 0.01~0.04s. **전체 파싱의 0.2~3.3%** — 무시할 수준이다.

### T2 — `registry_hints` 응답 경로
소비처 실측: 생성 지점(`proposal_parser.py:561,563`) 외 **0건**. `src/` 참조 **0건**.
응답 경계는 **`_finalize_proposals()` 한 곳**이다
(`service.py:27` → `parse_proposal_files` → `_finalize_proposals`; `/coverage/parse`는
`pipeline/coverage_parser.py` 경유라 이 metadata를 애초에 싣지 않는다).
→ ★**`_finalize_proposals`에서만 벗겨내면 응답에서 사라지고 내부 반환값은 그대로 남는다.**

---

## Step 2~4 — 구현

### T1 — limiter 4종 추가 (한도는 기존과 동일 수준, 새 정책 없음)
| 엔드포인트 | 추가한 한도 | 왜 이 값인가 |
|---|---|---|
| `/billing/webhook` | `60/minute` (IP 기준) | 외부 콜백이라 **넉넉히**(283 수정 방향 그대로). 조회 계열과 같은 값이며 토스 재시도를 막지 않는다. ★서명 검증 전에 걸리므로 위조 요청도 함께 눌린다 |
| `/billing/status` | `60/minute` | **조회** 성격 — 기존 히스토리 조회와 동일 |
| `/admin/tier/list` | `20/minute` | **쓰기·관리** 성격 — 기존 일반 쓰기와 동일 |
| `/admin/tier/set` | `20/minute` | 동일 |
- ★4종 모두 **기본 key_func(`_ratelimit_key`)** 를 쓴다 — 별도 `key_func`를 주지 않았다.
  `/billing/webhook`은 Authorization 헤더가 없으므로 이 함수가 알아서 IP fallback으로 떨어진다
  (063이 만든 동작 그대로). 실측에서 키가 `ip:testclient`로 잡히는 것을 확인했다.
- 3종에 `request: Request` 인자를 추가했다(slowapi 요구사항). ★기존 인자 순서·기본값 무변경.

### T2 — `registry_hints` 응답 제거
`_finalize_proposals()`에서 각 제안서 `metadata`의 `registry_hints`를 **응답 직전에 벗긴다**.
- ★`parse_proposal_text()`·`parse_proposal_pdf()`의 반환값은 **그대로**다 — 서버 내부·276b 수기 확인은 계속 쓴다.
- `bundle_subbenefits`·`unresolved_coverages`는 **남긴다**(전자는 276b가 쓰는 파생값, 후자는
  276a가 "지어내지 않고 알린다"를 지키는 근거다). 제거 대상은 소비처 0인 `registry_hints` 하나뿐이다.

### T3 — 업로드 상한 (`backend/pdf_guard.py` 신설)
★**`backend/pipeline/`을 건드리지 않기 위해 새 모듈로 분리**했다(AGENTS 보호 영역 규칙).
- 세 가지를 **입구에서** 본다: 쪽수 · 콘텐츠 스트림 압축 해제 누적 · 이미지 원시 바이트.
- ★**조기 중단**: 누적이 상한을 넘는 즉시 멈춘다 — 폭탄 전체를 펼치지 않는다.
- ★**이미지는 압축을 풀지 않는다** — `/Width`·`/Height`·`/BitsPerComponent`를 **dict에서만** 읽어
  원시 픽셀 바이트를 계산한다. 폭탄을 재려고 폭탄을 터뜨리는 일이 없다.
- ★**열기 실패는 통과시킨다**(fail-open). 비밀번호 불일치·손상 PDF의 정확한 안내는 기존 파서가
  이미 하고 있고, 가드가 먼저 다른 문구로 가로채면 **기존 동선이 나빠진다**.
- 적용 지점 4곳: `/api/analyze` · `/api/coverage/parse` · KB 제안서 · 회사별 제안서 목록.

### 오류 문구 (271 사전 정합)
- 서버: `PdfGuardError` → 413. 문구는 원인 + 다음 행동, **파일명 미포함**(277 PII 기조).
- 프런트 `errorMessages.ts`에 규칙 2건 추가 — 쪽수/내용 초과, 그리고 ★**429**.
  ★429는 **기존에 사전이 없어 폴백으로 떨어지고 있었다**(서버는 "요청이 너무 잦습니다"라고
  정확히 알려주는데 화면에는 "요청을 처리하지 못했어요"가 떴다). T1로 429가 실제로 늘어나므로 함께 채웠다.

---

## 검증 결과 (1차 · 2026-08-10 · Windows 로컬)

### ★T1 — 실제 HTTP 요청으로 429 확인 (소스 grep 아님)
| 엔드포인트 | 한도 | 429가 뜬 시점 | 응답 detail |
|---|---|---|---|
| `/billing/webhook` | 60/minute | **61번째** | `요청이 너무 잦습니다. 잠시 후 다시 시도해 주세요.` |
| `/billing/status` | 60/minute | **61번째** | 동일 |
| `/admin/tier/list` | 20/minute | **21번째** | 동일 |
| `/admin/tier/set` | 20/minute | **21번째** | 동일 |
★**정상 사용 패턴 무영향**: `/billing/status` 연속 20회 → 429 **0건**.
`/billing/status`는 화면 진입마다 1회 부른다(`UsageBadge`는 `/disclosure` 1곳, `Dashboard`,
`Subscription` — **폴링 아님**). 현실 사용량 대비 여유가 크다.
★**기존 적용분 무변경**: `/api/analyze` 5/minute,30/hour · 진행 폴링 120/minute ·
결제 발급 10/minute · `Limiter(...)` 생성 인자 그대로(테스트로 고정).

### ★T1 부수 발견 — `default_limits`는 무효다 (기록만, 수정 안 함)
`limiter = Limiter(key_func=_ratelimit_key, default_limits=["60/minute"])`가 있지만
**`SlowAPIMiddleware`가 등록돼 있지 않다**. slowapi는 미들웨어가 있어야 기본 한도를 적용하므로
이 인자는 현재 **아무 일도 하지 않는다** — 283 F-6의 "4종은 정말로 무제한"이 그대로 성립한다.
★"전역 기본 한도가 있다"고 오해할 여지가 있어 `decisions.md`에 남겼다.
미들웨어 추가는 **전 라우트 정책 변경**이라 이번 범위 밖이다(패킷: 새 정책 금지).

### T2 — `registry_hints`
- 응답(`parse_proposal_texts`/`parse_proposal_files` → `_finalize_proposals`)에서 **사라졌다**.
- `parse_proposal_text()`·`parse_proposal_pdf()` 반환값에는 **그대로 남는다**(서버 내부 접근 유지).
  ★276a의 `test_registry_hints_remain_as_metadata_only`가 **그대로 통과**한다 — 이게 증거다.
- `bundle_subbenefits`·`unresolved_coverages`는 **함께 지우지 않았다**(276a/276b 근거).

### T3 — 업로드 상한
★**정본 6건 전부 통과** (가드 소요 0.01~0.05초):
우O균 28p · 오현지 27p · 우상균 10p · **라금실 30p** · **오현지 가입제안서 26p** · 이인숙 42p.
- 합성 초과 PDF: 쪽수 1,001p → `PdfGuardError` + 쪽수 문구 / Flate 압축폭탄 → 압축 해제 문구.
- ★**경계 포함 확인**: 정확히 1,000쪽은 통과한다(`>` 비교).
- ★**fail-open 확인**: 열리지 않는 바이트열은 조용히 통과 → 기존 파서가 "비밀번호 해제 실패"를 안내.
- 적용 4곳 전부 배선(테스트로 고정) — 한 곳만 빠져도 그 경로가 무방비다.

### 게이트
- [x] backend `pytest -q` **932 passed, 8 skipped** — 기준선 902 + **신규 30**, 회귀 0
- [x] `npm test` **402 passed / 41 files** — 기준선 393 + **신규 9**, 회귀 0
- [x] `npx tsc -p tsconfig.app.json --noEmit` / `tsconfig.node.json` — PASS
- [x] `npm run lint` — 무경고
- [x] `npm run smoke:coverage` — ★**정본 2건 기준값 완전 일치**(월납 681,312 · 4,675,189 불변)
- [x] `npm run build:verify` — **343,702 B 예상 FAIL**(248 Application Control, 로컬 정직 상태)
- [x] ★277 PII·278 표면·279 문구 무회귀 — 해당 테스트 파일 직접 재실행 통과
- [x] ★보호 영역 **diff 0**: `backend/pipeline/` · `backend/filters.py` · `vite.config.ts`

### ★기존 테스트 12건 호출 규약 갱신 — 사유 (기대값 완화 아님)
`test_admin_tier_233.py`(9) · `test_usage_middleware.py`(3)이 라우트 핸들러를 **HTTP 없이 직접 호출**한다.
284가 limiter를 붙이면서 시그니처에 `request`가 생겼으므로 호출부에 가짜 `Request`를 넘겼다
(060·063 테스트의 기존 방식과 동일). ★**단언은 한 줄도 바꾸지 않았다** — 인자만 맞췄다.
함께 넣은 autouse fixture는 limiter를 끈다: 직접 호출이 반복되면 20/minute에 걸려
**테스트가 실행 순서에 의존**하게 되기 때문이다.

### ★확인 불가
- **심평원 진료내역 실 PDF**: 로컬에 표본이 없다. 쪽수 상한의 근거는 `main.py:619` 주석에 남은
  **실사용 318쪽 사고 기록**(BUG-006)이며, 실제 파일로 통과를 확인하지는 못했다.
  ★상한 1,000쪽은 그 3.1배라 여유가 있지만, **표본으로 검증한 것은 아니다**.
- **운영 환경 429 체감**: Railway 프록시 뒤 IP 집계 방식은 로컬에서 재현할 수 없다
  (`_ratelimit_key`가 JWT sub 우선이라 인증 경로는 사용자별로 갈리지만, `/billing/webhook`은 IP 기준이다).
- **이미지 XObject 폭탄 실물**: 악성 표본을 만들지 않았다(생성 자체가 범위 밖).
  픽셀 예산 로직은 정본 6건 실측값(최대 174,628,166 B)으로만 검증했다.

### ★남은 한계 — 정직 기록
가드는 **페이지 콘텐츠 스트림**과 **이미지 dict**만 본다. 따라서 막지 못하는 것:
1. **단일 스트림 폭탄** — 하나의 스트림이 한 번에 수 GB로 펼쳐지면, 누적을 재기 **전에** 이미 펼쳐진다
   (pdfminer의 `get_data()`가 one-shot이라 중간에 끊을 지점이 없다).
2. **폰트·객체 그래프 폭탄** — 구조 검사 범위(패킷이 명시적으로 범위 밖으로 뒀다).
→ 이번 변경은 "크기 상한만 있던 상태"보다 나아진 **최소 방어**이지 완전 방어가 아니다.

## Stage 목록 (Codex용)
변경된 백엔드·프런트 소스 + 284 테스트, `.agent-harness/decisions.md`,
`tasks/BOHUMFIT-284-open-gate-closure.md`, `handoff.md`, `locks.md`
★기준선 변동 시 `verify.md`·`CLAUDE.md`·`AGENTS.md` 3문서 모두
※제외: 실 PDF·PII·산출물

## 커밋 메시지 (Codex용)
fix(BOHUMFIT-284): 오픈 게이트 마감 — rate limit 4종·응답 표면 축소·업로드 상한
