# BOHUMFIT-277b — PII scrubber 보정 (277 반려분)

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: Claude Code (보정·1차 검증)
Risk tier: ★고위험 — 개인정보 경계. git 쓰기 금지(커밋 Codex, ★277+277b 합쳐 커밋).
Date: 2026-08-08 · 기준 HEAD `2db2945` · 선행 BOHUMFIT-275(감사) → 277(구현·반려)

## 상황
277 구현이 워킹트리에 미커밋 상태이고 Codex 2차 검증에서 **필수 PII 계약 위반 2건**으로 반려됐다.
277을 되돌리지 않고 **그 위에 보정**한다.

---

## Step 1 — 실측 (코드 무변경)

### ★R2 재현 — Codex 보고 그대로 성립
```
anonymize_parse_errors(["🔒 a long.pdf: 오류"], ["a.pdf", "a long.pdf"])
  → ['🔒 서류 1 long.pdf: 오류']      ★`long.pdf` 잔존
```
원인은 `pii.py:58~63` `mask_filenames()`가 **파일 단위로 순회**하는 구조다.
`_variants()` 안에서만 길이순 정렬을 하므로, 첫 파일 `a.pdf`의 stem `a`가 먼저 치환되어
두 번째 파일 `a long.pdf`가 **전체 일치 기회를 잃는다**. 272b 상품명 절삭에서 겪은 부분 문자열 함정과 같다.

### R1 — 현재 scrub 대상 전수
| 위치 | 대상 | 판정 |
|---|---|---|
| `backend/pii.py` `_scrub_pdf_text` | `*.pdf` 접두/토큰 | ★**파일명만** |
| `backend/main.py:139~155` `_scrub_sensitive_event_values` | 키 기반 + 최종 문자열에 `scrub_pdf_filenames_deep` | ★**파일명만** |
| `src/lib/errorMessages.ts:128~133` `scrubPii` | `pdf/xlsx/xls` 토큰 | ★**파일명만** |
| `src/main.tsx:30~41` Sentry `beforeSend` | 위 `scrubPii`를 message·breadcrumb·exception에 적용 | ★**파일명만** |
실측 재현: `_scrub_sensitive_event_values("가상고객A 최근 3개월.pdf I10 고혈압 서울병원")`
→ 파일명만 `서류`로 바뀌고 **`I10`·`고혈압`·`서울병원`이 그대로 남는다**.
★**파일명은 간접 식별자, 상병코드·병명은 건강정보 그 자체**다 — 후자가 더 민감한데 무방비였다.

### ★지워야 할 대상 목록 (확정)
| 대상 | 판정 근거 | 이번 처리 |
|---|---|---|
| 원본 파일명 | 271 실측(실명 포함) | 전역 longest-first 치환(R2) + 패턴 |
| **상병코드** | ICD-10 형식 `영문1 + 숫자2 (+.숫자)` | ★패턴 `\b[A-Z]\d{2}(?:\.\d{1,2})?\b` |
| **기관명** | `~병원`·`~의원`·`~한의원`·`~클리닉`·`~보건소` | ★패턴 |
| **병명·진단명** | ★**사전 없음**(아래) | ★**구조적 처리**(raw 비전송) |
| 고객명·환자명 | 파일명·`customer_name` 경유 | 277이 이미 처리 |

### ★★병명 사전은 존재하지 않는다 — 설계가 갈리는 지점
`backend/keywords.json` 전수 확인 결과, 있는 것은 **상병코드 목록**과 수술·검사 키워드뿐이다.
| 키 | 내용 |
|---|---|
| `easy_q3_6codes`(115) · `health_q5_codes`(140) · `non_disease_code_prefixes`(12) | **코드** 목록 |
| `surg_keywords`(23) · `test_keywords`(12) · `procedure_keywords`(6) 등 | 행위 키워드 |
→ **병명(진단명) 사전은 없다.** 따라서 병명은 **패턴이나 사전으로 지울 수 없다**
(`고혈압`·`상세불명의 만성 폐쇄성 폐질환` 같은 임의 한글 문자열을 안전하게 식별할 방법이 없다).

★그래서 Codex 회송 요구 #2("구조화 whitelist 또는 **raw 본문 비전송 계약**")를 채택한다:
**임의 raw 문자열을 정규식으로 안전하다고 가정하지 않고, 애초에 내보내지 않는다.**
정규식 scrub은 그 위의 **방어 2선**으로만 남긴다.

### 오류 문자열에 PII가 섞여 들어오는 형태 (실측)
- 예외 메시지: `f"⚠️ {파일명}: PDF 파싱 중 예외 — {str(e)[:120]}"` → 파일명 + 예외 본문
- `console.warn("[271] 매핑되지 않은 오류:", raw)` → 서버 `detail` 원문(파일명·사유)
- Sentry breadcrumb: 위 console 출력이 자동 수집
- Sentry exception: `Error.message` — 서버 응답 문구가 그대로 들어갈 수 있다

---

## Step 2~5 — 구현

### Step 2 (R2) — 전역 longest-first 치환
`pii.py::mask_filenames`를 **파일 단위 순회 → 전체 후보 전역 정렬**로 바꿨다.
모든 파일의 (전체명·stem) 후보를 모아 **길이 내림차순**으로 치환하므로 짧은 이름이 긴 이름의
앞부분을 갉아먹지 못한다. ★**slot 번호는 원본 파일 index를 유지**한다(정렬은 치환 순서만 바꾼다).

### Step 3 (R1) — scrub 대상 확장 + ★raw 비전송 계약
- `pii.py`: `scrub_health_terms()`(상병코드 ICD 패턴 + 의료기관명 접미사) · `scrub_text()` ·
  `scrub_deep()` · **`safe_error_summary()`** 추가.
- `main.py` Sentry scrubber의 최종 문자열 처리를 `scrub_pdf_filenames_deep` → **`scrub_text`**로 격상.
- `errorMessages.ts` `scrubPii()`에 **같은 ICD·기관명 규칙** 추가.
- ★**`console.warn`이 원문을 더 이상 내보내지 않는다** — `safeErrorSummary()`(kind·length)만 남긴다.
  콘솔은 Sentry breadcrumb로 자동 수집되고, **병명은 사전이 없어 scrub으로 지울 수 없기 때문**이다.
  개발 환경(`import.meta.env.DEV`)에서는 scrub한 `preview`를 함께 남겨 진단 가능성을 지킨다
  (Sentry는 프로덕션에서만 켜지므로 운영 breadcrumb에는 preview가 없다).

### Step 4 — 프런트·백엔드 동일 규칙
언어 경계라 상수를 공유할 수 없어 **183·276a 선례대로 교차 테스트로 고정**했다:
ICD 패턴 문자열·기관명 접미사 8종·치환 라벨(`[제거됨]`)이 두 파일에 동일하게 존재함을 단언한다.

---

## 검증 결과 (1차 · 2026-08-08 · Windows 로컬)

### ★반려 2건 재현 → 소거
| 반려 | 수정 전(Codex 재현) | 수정 후 |
|---|---|---|
| **R2** | `["a.pdf","a long.pdf"]` → `['🔒 서류 1 long.pdf: 오류']` | ★`['🔒 서류 2: 오류']` — 조각 0, **slot도 원본 index** |
| **R1** | `"…pdf I10 고혈압 서울병원"` → `I10`·기관명 잔존 | ★`I10`·`서울병원`·`강남한의원` **전부 `[제거됨]`** |

### R2 경계 케이스 (전부 조각 0)
완전 부분집합(`보고서.pdf`/`보고서 최종.pdf`) · 확장자 중복(`a.pdf`/`a.pdf.pdf`) ·
공백 포함(`보 고 서.pdf`) · 동일 stem · 한 문자열에 두 파일명 동시 등장.

### ★운영 진단 가능성 유지
`scrub_text("🔒 서류 1: PDF 비밀번호 해제 실패 — 생년월일을 확인해 주세요.")` → **문자열 그대로**.
`safe_error_summary(ValueError(...), 0)` → `{kind, slot: "서류 1", length}`.
277이 확보한 `file=서류 N records=… ftype=… errors=…` 로그도 그대로다.

### 게이트
- [x] backend `pytest -q` **890 passed, 8 skipped** — 277 기준 874 + **신규 16**, 회귀 0
- [x] `npm test` **373 passed / 38 files** — 277 기준 363 + **신규 10**, 회귀 0
- [x] `smoke:coverage` PASS · tsc app/node · lint · `build:verify` 343,702 B 예상 FAIL
- [x] ★프런트·백엔드 동일 규칙 교차 테스트 3건(ICD 패턴·기관명 8종·`[제거됨]` 라벨)
- [x] ★277 무회귀: B-F3 계약·B-F1 raw 정규화·B-F2 로그 slot 유지
- [x] ★범위 diff 0: `pipeline/`·`filters.py`·`coverage/` · **279**·**278** · `vite.config.ts`

### ★기존 테스트 2건 기대값 갱신 — 사유
| 테스트 | 갱신 | 사유 |
|---|---|---|
| `errorMessages.test.ts` "원문은 콘솔에만 남는다" | 원문 미포함 + `kind` 포함 | 271이 고정한 동작을 **277b가 의도적으로 바꿨다**(raw 비전송). 271의 **표시 직전 sanitization은 그대로** |
| `test_pii_boundary_277.py` scrub 카운트 | 합산 → **경로별 개별 단언** | Sentry가 `scrub_text`로 격상돼 합산이 무의미. 묶으면 **한쪽이 약해져도 통과** |

### ★★남은 한계 — 정규식 scrub은 "0 보장"이 아니다 (정직 기록)
`scrub_text`가 완전히 지우지 못하는 것 2가지:
1. **병명** — `고혈압` 등. `keywords.json`에 **병명 사전이 없다**(코드 목록·행위 키워드만).
2. **문장 중간의 공백 포함 한글 파일명** — 파일명 목록을 모르는 경로에서 `가상고객A 최근`이 남는다.

→ console/Sentry 경로의 보장은 정규식이 아니라 **`safeErrorSummary`(raw 비전송)** 에서 나온다.
이 문서는 정규식 scrub을 "0 보장"으로 주장하지 않는다.
★완전 봉인은 **모든 emit 지점을 구조화 로깅 whitelist로 전환**하는 별도 태스크가 필요하다(범위 초과).

### 확인 불가
- **실계정 2개 E2E**: `VITE_SUPABASE_URL`·`ANON_KEY` 부재로 앱이 시작 단계에서 중단(Codex와 동일 사유).
- **운영 Sentry 실제 이벤트**: 전송 여부·보존 내용 미접근.

## Stage 목록 (Codex용)
★**277 + 277b를 합쳐 커밋**(277 단독은 반려 상태).
변경된 백엔드·프런트 소스 + 277·277b 테스트,
`tasks/BOHUMFIT-277-pii-boundary.md`·`BOHUMFIT-277b-scrub-hardening.md`, `handoff.md`, `locks.md`
★기준선 `verify.md`·`CLAUDE.md`·**`AGENTS.md` 3문서 모두**
※제외: 실 PDF·PII·산출물

## 커밋 메시지 (Codex용)
fix(BOHUMFIT-277): PII 저장·로그 경계 봉인 + scrub 대상 확장(상병코드·병명·기관명·중복 파일명)
