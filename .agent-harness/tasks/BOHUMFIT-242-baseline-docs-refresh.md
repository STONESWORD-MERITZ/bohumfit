# BOHUMFIT-242 — 검증 기준선 문서 갱신 (실측 동기화)

Owner flow: Claude Chat -> Claude Code (커밋 허용) | Current owner: Claude Code
Risk tier: 저위험 — Chat 명시 "Code 커밋 허용", Codex 생략 가능. 문서만·코드 변경 0.
Date: 2026-07-23

## 배경

216~241 사이 테스트가 대폭 증가했고(618→684), 프런트 테스트도 신설·확장됐다(→79).
청크 기준은 240 조사로 확정됨: 커밋 `2f041fc` 격리 빌드 342.66 kB = 당시 현행 343.22 kB →
**343 kB대가 정상 기준선**이고 "500 kB warning 허용"은 구 빌드 상태 산물.

## S0 — 실측 (2026-07-23)

### ① 게이트 1회 실행 — 명세값과 일치 확인

| 항목 | 실측값 | 명세값 | 판정 |
| --- | --- | --- | --- |
| `cd backend && python -m pytest -q` | **684 passed, 8 skipped** | 684/8 | 일치 |
| `npm test` | **79 passed** | 79 | 일치 |
| `npm run build` 청크 | **343.22 kB**(gzip 101.81), 청크 경고 **없음** | 343 kB대 | 일치 |

### ② 기준선 수치 언급 전수 grep — 갱신 대상 특정

| 파일:라인 | 기존 | 조치 |
| --- | --- | --- |
| `.agent-harness/verify.md:19-22` | `618 passed, 8 skipped`(백엔드만) | ✅ 갱신 + 프런트·tsc·청크 기준선 신설 |
| `CLAUDE.md:299` | `618 passed, 8 skipped`(BOHUMFIT-217 기준) | ✅ 684/8(242 기준) + 프런트·청크 추가 |
| `AGENTS.md:100` | 커밋 전 검증 계약 `618 passed, 8 skipped` | ✅ 684/8 + `npm test` 79 + 청크 기준 추가 |
| `README.md` | 명령만 있고 **기준선 수치 없음** | ➖ 무변경(수치 부재 — 갱신 대상 아님) |
| `PROGRESS.md:61,66,80` | `91개`·`201 passed`·`279 passed` | ➖ **무변경** — "① 완료된 작업" 하위 **과거 태스크별 이력**(당시 수치 보존 원칙) |
| `locks.md`·`handoff.md`·`audit/210` | 각 태스크 당시 수치 다수 | ➖ **무변경** — 이력 기록 |

### ③ ★명세와 다른 실측 1건 (기록)

명세는 `"500 kB chunk size warning만 허용" 문구를 교체`하라고 지시했으나, **기준선 문서 4개
(verify.md·CLAUDE.md·AGENTS.md·README.md)에는 해당 문구가 0건**이었다(grep 실측). 이 표현은
handoff·locks 등 **이력 기록에만** 존재한다. 따라서 "교체"가 아니라 **청크 기준선 신설(추가)**로
처리했고, 폐기 사실은 새 문구 안에 명시했다(과거 이력은 무수정).

## 갱신 내용

- **verify.md**: "Backend pytest baseline" 단일 블록 → **`## 검증 기준선 (BOHUMFIT-242 실측 · 2026-07-23 갱신)`**
  섹션으로 확장 — 백엔드 684/8, 프런트 79, tsc 양쪽 명령, 청크 343 kB대(+"500 kB 허용" 폐기 근거·240 조사 인용),
  **±10% 초과 변동 시 중단·원인 조사** 규칙, 기준선 변경 시 3문서 동시 갱신 안내.
- **CLAUDE.md 검증 게이트**: 백엔드 684/8(242 기준으로 출처 갱신), `npm test` 79 신설, 청크 343 kB대·±10% 규칙 추가.
- **AGENTS.md 커밋 전 검증 계약**: 백엔드 684/8, `npm test` 79 신설, build에 청크 343 kB대·±10% 규칙 추가,
  기준선 변경 시 verify.md·CLAUDE.md 동시 갱신 명시.
- 하네스 운영 규칙(3트랙·위험도·루트 게이트) **내용 변경 0** — 수치·기준선 문구만 동기화.

## 검증 체크리스트 (2026-07-23 결과)

- [x] 게이트 1회 실행 수치와 문서 기재값 일치(pytest **684/8** · npm test **79** · build **343.22 kB**)
- [x] 구 기준선 `618 passed` 잔존 **0건**(기준선 문서 4개 기준. handoff·locks·PROGRESS·audit 이력은 보존)
- [x] git diff = 문서 파일(verify.md·CLAUDE.md·AGENTS.md) + tasks/242 + handoff·locks만. **코드 diff 0**
- [x] `git diff --check` 통과

## Stage 목록

.agent-harness/verify.md, CLAUDE.md, AGENTS.md, tasks/BOHUMFIT-242-*.md, handoff.md, locks.md (.env* 제외)

## 커밋 메시지

docs(BOHUMFIT-242): 검증 기준선 문서 갱신 — pytest 684/8·npm test 79·청크 343 kB대
