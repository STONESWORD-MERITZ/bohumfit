# BOHUMFIT-226 — 브랜드 잔재 정리 + 라우트 스모크 테스트 + 레포 위생 감사 (4파트 저위험 묶음)

Owner flow: Claude Chat -> Claude Code -> Codex
Current owner: Codex (A~D 완료 — 225 선행 커밋 후 226 순차 커밋 대기)
Risk tier: 저위험 — 단, git 쓰기 전면 금지(커밋은 내일 Codex가 225 커밋 이후 순차 처리)
Date: 2026-07-17

## 목적

Human 개입 없이 진행 가능한 저위험 백로그를 일괄 소화한다:
(A) InsuranceLinks 등 비토큰 그린 잔재 정리 (B) 공개 라우트 전수 렌더 스모크 테스트 신설
(C) 레포 위생 감사 리포트 (D) FitHere 인증 메일 브랜드 분리 사전조사.
C·D는 조사·문서 전용(코드 0)이다.

## 수정 범위

- A: src/ 내 브랜드 색상 하드코딩·비토큰 사용 파일 (InsuranceLinks 우선)
- B: src/ 테스트 파일 신규 추가만
- C·D: .agent-harness/tasks/ 하위 산출 문서 신규만
- 공통: .agent-harness/handoff.md, locks.md, tasks/BOHUMFIT-226*.md

## 수정 금지

- backend/pipeline/, backend/coverage/, supabase/ (마이그레이션·manual 포함) 전부 무접촉
- 225 관련 미커밋 파일 일체 무접촉
- .env / .env.txt — 열람·수정·이동 금지 (존재 여부 조사도 금지, Human 확인 대기 중)
- 인증 코어(로그인/가입/OAuth/hCaptcha/PhoneVerify), 216 SMS 코드, 결제 관련
- 기존 테스트 수정 금지 (신규 추가만)
- git 쓰기 전면 금지 (읽기 조회는 허용)

## 파트 A — STEP 0 실측 결과 (2026-07-17)

① 구브랜드 색상(#15663D·#2E6B3E·#145C2A): src/ **0건** ✓
② FIT 토큰 hex 하드코딩: index.css(토큰 정의 자체)·Home.tsx:119(주석 문구)뿐 — 위반 **0건** ✓
③ 면 전용 색상(lime·greentea)의 텍스트/보더 사용: **0건** ✓
④ Tailwind 원색 그린·임의 hex 그린 — 분류:

| 파일:라인 | 사용 | 분류 | 조치 |
| --- | --- | --- | --- |
| InsuranceLinks.tsx:314 | `focus-visible:ring-green-500` | 브랜드(포커스 링 — 관례는 ring-accent-600) | ✅ `ring-accent-600` 치환 |
| InsuranceLinks.tsx:391 | `hover:border-green-200` | 브랜드(카드 hover) | ✅ `hover:border-accent-200` |
| InsuranceLinks.tsx:638 | `hover:bg-green-50` + `ring-green-500` | 브랜드(탭 hover·포커스) | ✅ `hover:bg-accent-50` + `ring-accent-600` |
| InsuranceLinks.tsx:639 | `text-[#2d6a4f]` | ★비토큰 그린 hex(활성 탭 텍스트) | ✅ `text-accent-600` |
| InsuranceLinks.tsx:645 | `bg-[#2d6a4f]` | ★비토큰 그린 hex(활성 탭 밑줄) | ✅ `bg-accent-600` |
| Disclosure.tsx:420 | `hover:bg-green-50/40` | 브랜드(카드 hover 틴트) | ✅ `hover:bg-accent-50/40` |
| Disclosure.tsx:2006 | `border-green-400 bg-green-50` (드래그 활성) | 브랜드(같은 라인 비활성은 accent 사용 — 불일치) | ✅ `border-accent-400 bg-accent-50` |
| Toast/Badge/Disclosure(종결·체크·안내박스)/Subscription/Signup:171·177/InsuranceCalculator | `emerald-*` 다수 | 시맨틱(성공/상태 표시 — 브랜드 아님) | 기록만(치환 시 index.css `--color-success-*` 토큰 후속 태스크 권장) |
| BeforeAfter.tsx | `emerald-*` | 고아 파일(165에서 라우트 제거) | 기록만 — C 리포트 미참조 파일 후보 |
| Disclosure.tsx:659 | `bg-[#FEE500]`·`text-[#191919]` | 카카오 공식 브랜드 색(버튼) | 기록만(잔재 아님) |
| PhoneVerify.tsx:62·Signup.tsx:72·89 | `bg-[#F8F9FC]` | 그린 아님(회색 배경) + 인증 코어 수정 금지 | 기록만 |

## 파트 A — 시각 변경 목록 (색값이 실제로 달라진 치환)

- InsuranceLinks 활성 탭 텍스트·밑줄: `#2d6a4f` → accent-600 `#084734` (더 짙은 에메랄드 파인)
- InsuranceLinks 포커스 링 2곳: green-500 → accent-600
- InsuranceLinks 카드 hover 보더: green-200 → accent-200 / 탭 hover 배경: green-50 → accent-50
- Disclosure 카드 hover 틴트: green-50/40 → accent-50/40 (#EEF6F1 40%)
- Disclosure 드롭존 드래그 활성: green-400/green-50 → accent-400/accent-50

## 검증 체크리스트 (A·B 완료 후 1차 검증 — 2026-07-17 Claude Code 실행 결과)

- [x] tsc app/node 통과
- [x] npm run lint 통과
- [x] npm test — **68 passed** (기존 50 전부 유지 + 신규 18 순증). 전체 스위트 4연속 68/68.
      ※최초 전체 실행에서 Home 스모크 1회 간헐 실패(act() 타이밍 경고) → 환경 아티팩트
      필터로 보강 후 안정 확인. 앱 오류 아님.
- [x] npm run build 통과 — 청크 342.66 kB **기록만**(225 이상 신호 미해결, 새 기준선 금지)
- [x] backend pytest **618 passed, 8 skipped** 불변
- [x] rg: 구브랜드 색상 0건(backend 테스트의 부재-assert 제외) · SURIT 0건(src/backend) ·
      면 전용 색상의 텍스트 사용 0건 · 치환 잔재(green-*·#2d6a4f) 0건
- [x] git status: 변경 = A 2파일 + B 신규 2파일 + harness 문서만 (supabase/·backend/·225 diff 0)
- [x] git diff --check 통과
- git 쓰기: **0** (지시대로 미실행 — 내일 Codex)

## Stage 목록 (내일 Codex용 — Code는 실행 금지)

- A 수정 파일 전부, B 신규 테스트, tasks/BOHUMFIT-226*.md 3개, handoff.md, locks.md
- 제외: 225 관련 전부(별도 선행 커밋), .env*, 실 PDF·PII

## 커밋 메시지 (Codex용)

chore(BOHUMFIT-226): 브랜드 비토큰 그린 정리 + 공개 라우트 스모크 테스트 + 위생/메일분리 감사 리포트
