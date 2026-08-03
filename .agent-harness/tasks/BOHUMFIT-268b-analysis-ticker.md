# BOHUMFIT-268b — 분석 진행 상태 + 추출 티커

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: Claude Code (구현·1차 검증)
Risk tier: 중위험 — git 쓰기 금지(커밋 Codex).
Date: 2026-08-02 · 기준 HEAD `96f2b54`(268a)
※워킹트리에 **182·183 미커밋분 공존** — Codex는 **182 → 183 → 268b 순서로 분리 커밋**할 것.

## ★확정 아키텍처(재검토 금지 — 패킷 지시)
uvicorn 워커 1개 → **프로세스 메모리 저장소 사용 가능**(Supabase 신설 금지) · **SSE 금지, 폴링 채택** ·
**기존 `/api/analyze` 동기 계약 유지**(작업 등록 방식으로 바꾸지 않는다).

## Step 1 — 현행 실측 (코드 무변경)

### 파싱 완료 시점에 **실제로 확정되는 값**
`analyzer._log_parsed(fn, pr)`(261행)가 유일한 완료 신호이고, 그 시점에 있는 것은:
| 값 | 출처 | 티커 사용 |
|---|---|---|
| 파일 완료순서 라벨 `서류 N` | 입력 파일 완료순서 | ○ |
| 레코드 수 `len(pr["records"])` | 파싱 결과 | ○ |
| 파일 유형별 건수 `_ftype`(basic/detail/pharma) | `Counter` | ○ |
| 파싱 오류 수 `len(pr["parse_errors"])` | 파싱 결과 | ○ |
| 원본 파일명 `fn`·환자명 `pr["patient_name"]` | 입력·파싱 결과 | ✗ **PII 가능 — 저장하지 않는다** |
| 코드·병명 | `records` 내부 | ✗ (아래 사유) |

★**코드·병명은 저장하지 않기로 했다.** 패킷은 티커에 쓸 수 있다고 했지만, 같은 패킷의
"PII 주의 — 저장 항목은 화면에 흘릴 값에 한정, 환자 식별정보 저장 금지"와 265~268a의 PII 최소화 기조를 함께
보면, **상병코드·병명은 건강정보 그 자체**라 서버 메모리에 얹는 순간 노출면이 늘어난다.
완료순서 라벨·레코드 수·유형별 건수만으로도 "무엇이 얼마나 처리됐는지"는 충분히 전달된다.
→ 코드·병명 티커가 꼭 필요하다면 **Human 결정 후 별도 태스크**로 다룬다(사유 기록).

### ★병렬 경로의 제약 — 이대로면 진행 신호가 한꺼번에 나온다
- **순차 경로**(`workers<=1` 또는 파일 1개): 파일마다 완료 즉시 `_log_parsed` → 실시간 진행 **가능**.
- **병렬 경로**(`BOHUMFIT-055`): `_run_pool()`이 **끝난 뒤** `zip(names, results)`로 `_log_parsed`를 부른다
  → 진행이 **일괄로** 나온다(실시간 아님).
  ★해결: `_run_pool` 내부 **`as_completed` 루프에서 기록**한다. 그 루프는 별도 프로세스가 아니라
  `asyncio.to_thread`로 도는 **메인 프로세스의 스레드**라 저장소에 바로 쓸 수 있다.
  이때 완료 순서는 **파일 순서와 무관**하므로 티커도 "완료된 것부터 채워지는" 형태여야 한다(순차 바 금지).

### 인증·제한 기존 패턴
`verify_jwt`(main.py:620) · `@limiter.limit("N/minute")` — 진행 조회도 같은 방식을 쓴다.

## Step 2~4 — 구현
- `backend/progress.py`(신설·순수 모듈): `job_id → {owner, files{}, created_at, finished_at}`.
  **TTL 자동 삭제**·소유자 검증·ID별 격리. 저장 항목은 위 표의 ○만.
- `analyzer.run_analysis(..., progress=None)`: **선택 인자**. 없으면 기존과 100% 동일 동작(하위 호환).
- `main.py`: `/api/analyze`에 `job_id` **Form 필드 추가**(기존 필드 무변경·미전송 시 기존 동작) +
  `GET /api/analyze/progress/{job_id}`(verify_jwt·소유자 검증·rate limit).
- `Disclosure.tsx`: 268a가 남긴 접합점에서 job_id 생성·전송 → 1.5초 폴링 → 티커.
  완료·에러·언마운트 시 **즉시 정리**. 폴링 실패·404는 **조용히 폴백**(티커만 사라지고 분석은 계속).
  ★퍼센트는 만들지 않는다 — "N개 중 M개 완료"는 실제 값이라 허용.

## Step 5 — 보장분석 적용 여부: **적용하지 않았다**
`/coverage/analyze`는 **단일 파일 업로드**라 "파일 N개 중 M개 완료"라는 티커의 재료가 애초에 없다.
진행 신호를 만들려면 `coverage/parser.py` 내부 단계(페이지 파싱·집계)를 쪼개 기록해야 하는데
그건 **`backend/coverage/` 무접촉 계약 위반**이다. 게다가 2.7~5.8s로 짧아 이득도 작다.
→ **적용하지 않고 사유를 기록**한다(패킷 Step 5가 허용한 판정).

## 검증 결과 (1차 · 2026-08-02 · Windows 로컬)

- [x] tsc app/node **PASS** · `npm run lint` **PASS**
- [x] `npm test` **246 passed / 30 files**(183까지 235 + 신규 11) · 회귀 0
- [x] backend `pytest -q` **818 passed, 8 skipped** — 183까지 803 + **신규 15**, **기존 회귀 0**
- [x] `npm run smoke:coverage` **PASS** · `build:verify` **343,225 B 예상 FAIL**
- [x] ★**하위 호환** — `job_id` 미전송 시 `progress.start("")`·`_log_parsed(..., "")` 모두 **무동작**이고
      저장소가 비어 있음을 테스트로 고정. `run_analysis`/`_parse_all_pdfs`/`_log_parsed` 모두 **선택 인자**라
      기존 호출부는 한 줄도 바뀌지 않았다.
- [x] ★**분석 결과 값 불변** — 진행 기록은 `_log_parsed`(로깅 지점)와 `as_completed` 루프에서만 일어나고
      `all_records`·`parse_errors`·`customer_name` 어디에도 개입하지 않는다. backend 전체 회귀 0이 이를 뒷받침.
- [x] ★**타인 작업 조회 차단** — 소유자가 다르면 `snapshot()`이 **None**을 주고 엔드포인트는 404.
      "남의 작업이 있다"는 사실조차 노출하지 않는다.
- [x] ★**TTL·누수** — TTL 경과분 자동 삭제 · `MAX_JOBS` 상한 · `drop()` 테스트 통과.
      (구현 정정 1건: 상한 정리를 등록 **전**에만 하면 1개씩 초과해서, **등록 후 정리**로 고쳤다.)
- [x] ★**폴링 정리** — `finished` 수신 시 자체 중단 · 정리 함수 즉시 중단 · **정리 후 도착한 응답 무시** ·
      화면 이탈 시 effect cleanup. (구현 정정 1건: ref 직접 조작이 `react-hooks/immutability`에 걸려
      **effect 기반 폴링**으로 바꿨다 — 누수 가능성이 더 낮은 관용 패턴이다.)
- [x] ★**폴링 실패 시 폴백** — 404·네트워크 오류를 **삼키고** 화면에 잘못된 값을 흘리지 않으며, 분석은 계속된다.
- [x] ★**퍼센트 미생성** — 티커에 `%`가 없다(테스트 고정). "N개 중 M개"만 쓴다.
- [x] ★**완료 순서 무관** — 저장소는 완료 순서대로 쌓이고 티커도 그 순서로 그린다(순차 바 아님).
      병렬 경로는 `as_completed` 루프에서 기록해 **실시간**으로 나간다.
- [x] ★**PII 미저장** — 저장 키가 `filename/records/ftypes/errors` **화이트리스트 그대로**이고,
      `filename` 값은 원본명이 아닌 완료순서 기반 `서류 N`임을 테스트로 고정. 원본 파일명·환자명·상병코드·병명은 넘기지 않는다.
- [x] ★**데스크톱 회귀 0** — 진행 정보가 있어도 데스크톱 대기 화면은 HEAD와 `innerHTML`·노드 수 **완전 동일**.
      진행 정보가 없으면 모바일도 HEAD와 동일. 사본·일회성 스크립트 **삭제**.
- [x] `backend/pipeline/` 268b diff **0**(변경된 `report_pdf.py`는 **183 문구분**) ·
      `backend/filters.py` diff **0** · `backend/coverage/` diff **0** · `vite.config.*` diff **0** ·
      Supabase 스키마 무변경 · 268a `MobileUploadSheet`/`uploadWithProgress` **구조 무변경**(접합만)

### 로컬에서 못 한 것 (Codex 몫)
- 375/390/430px 실렌더 넘침(jsdom 레이아웃 미계산)
- **실제 다중 파일 분석에서 티커가 실시간으로 채워지는지**(병렬 경로 `BOHUMFIT_PARSE_WORKERS=2` 포함) —
  로컬에서 순수 모듈·접합 지점까지는 고정했으나 **엔드투엔드 실측은 프로덕션/Codex 몫**이다.

## Codex 2차 검증 (2026-08-03 · Windows)

- 전체 게이트: tsc app/node·lint·frontend **246/30**·backend **818/8**·`smoke:coverage` PASS.
  build 343,225 B, `build:verify`는 확정 계약대로 예상 FAIL.
- 실 PDF 3종: 워커 1은 6.456s→42.749s→67.596s, 강제 워커 2는
  8.009s→30.324s→38.574s에 1/3·2/3·3/3 이벤트가 각각 도착했다. 병렬 완료 순서가 입력 순서와
  달라도 최종 분석 결과는 완전 동일했다. 같은 입력·워커 2에서 `job_id` 있음/없음 결과 dict도 완전 동일했다.
- ★보안 보정: 실 저장소 덤프에서 원본 파일명에 고객명이 포함될 수 있음을 발견했다. 원본명은 저장하지 않고
  완료순서 기반 익명 `서류 N`만 저장하도록 최소 보정했다. 덤프의 원본명·환자명·상병코드·병명 0을 실증했다.
- 타인 job 조회 404·하위 호환 no-op·TTL/상한·폴링 정리/폴백·퍼센트 0을 재현했다.
- 실브라우저 375/390/430px 티커 넘침 0. HEAD 별도 worktree와 데스크톱 렌더를 대조해 진행 데이터가 있어도
  기존 대기 화면 `innerHTML`·노드 수가 동일함을 확인했다. 임시 검증 산출물은 삭제했다.

## Stage 목록 (Codex용)
`backend/progress.py`(신규)·`backend/main.py`·`backend/analyzer.py`·`src/pages/Disclosure.tsx`·테스트,
`tasks/BOHUMFIT-268b-analysis-ticker.md`, `verify.md`, `CLAUDE.md`, `handoff.md`, `locks.md`
※제외: 실 PDF·PII·엑셀 원본·시안 HTML·렌더 산출물

## 커밋 메시지 (Codex용)
feat(BOHUMFIT-268b): 분석 진행 상태 폴링 + 추출 티커(하위 호환·결과 불변)
