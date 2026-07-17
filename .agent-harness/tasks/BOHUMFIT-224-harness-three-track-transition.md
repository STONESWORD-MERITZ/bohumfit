# BOHUMFIT-224 하네스 3트랙 전환 — Cowork 퇴역·Claude Code 구현 트랙·위험도 규칙

Owner flow: Claude Chat -> Claude Code -> Codex
Current owner: Human (Codex 2차 검증 통과·커밋/push 결과는 최종 응답 참조)
Risk tier: 저위험(문서만) — 단, 하네스 헌법 변경이므로 이번 건은 풀 하네스(Code 커밋 금지, Codex 커밋)

## Intent

- 구현 트랙을 Claude Cowork(샌드박스)에서 Claude Code(Windows 로컬)로 교체한다.
- 퇴역 사유: 마운트 truncation 반복(182~184·195·213 mid-token 절단).
- 순서 불변: Claude Chat → Claude Code → Codex.
- 유사 폴더 오작업 방지를 위한 루트 게이트, 위험도 운영 규칙, 커밋 전 검증 계약을 명문화한다.

## Scope

- 수정 허용: `AGENTS.md`, `CLAUDE.md`, `README.md`, `.agent-harness/WORKFLOW.md`, `.agent-harness/tasks/BOHUMFIT-224-*.md`, `.agent-harness/handoff.md`, `.agent-harness/locks.md`
- 수정 금지: `src/`, `backend/`, `supabase/` 전체(코드 무변경), handoff 과거 기록, `tasks/` 과거 문서
- 보존: 기존 Cowork 규칙은 삭제하지 않고 "[퇴역] Cowork 이력"으로 이동(과거 handoff 해석용)

## Work

1. 루트 게이트 신설(AGENTS.md, 모든 트랙 작업 시작 전): ① pwd=`C:\Users\18_rk\BOHUMFIT` ② remote=`STONESWORD-MERITZ/bohumfit` ③ 리트머스 `.agent-harness/tasks/BOHUMFIT-219-shared-rls-migration-alignment.md` 존재. 불일치 시 즉시 중단·Human 보고. 유사 폴더 작업 금지.
2. 트랙 구성 교체: Chat(기획·결정·프롬프트, 레포 접근 없음) / Claude Code(구현+1차 검증 직접 실행·신뢰, git 읽기 허용·쓰기 기본 금지) / Codex(2차 검증+커밋·push, 검증·반려 전용, 직접 수정 한 줄급만 — 초과 시 handoff로 Code 회송).
3. 위험도 운영 규칙: 저위험(문구·스타일·소규모 UI·문서)은 Chat이 "Code 커밋 허용" 명시 시 Code가 커밋·push, Codex 생략 가능. 고위험(DB·보안·인증·pipeline·coverage 코어·대형 리팩터·마이그레이션)은 풀 하네스 + DB 변경 Human 게이트(SQL은 Chat 작성, Human 실행). 위험도 판단·명시 = Chat 책임.
4. 원칙 보강: STEP 0 실측 없이 수정 금지 / 최소 수정(스펙 밖 발견은 기록만, Human 결정) / 이상 신호(빌드 산출물 급감·핵심 구조 "없음" 보고·파일 절단 징후·과거 커밋 회귀) 감지 시 즉시 중단·보고.
5. 커밋 전 검증 계약 명문화: tsc app·node / lint / build / pytest(618/8 기준선) + 도메인 계약 grep(SURIT 0건·구브랜드 색상 0건) + 보호 영역(backend/pipeline/·backend/coverage/ 코어·supabase/·auth) diff 발생 시 태스크 명시 없으면 커밋 금지.
6. CLAUDE.md·WORKFLOW.md·README.md의 Cowork 단계 서술을 Claude Code로 교체, 호출 템플릿 2벌(Code용/Codex용)을 WORKFLOW.md에 추가, "샌드박스라 실행 불가" 제약 문구를 "Code는 로컬 직접 실행, 권위 커밋은 Codex"로 교체.

## Verification

- 문서만 — 코드 무변경이므로 검증은 diff 범위 확인이 핵심.
- `git diff` / `git status --short -uall` 결과가 `.agent-harness/` + 루트 MD(AGENTS.md·CLAUDE.md·README.md) 범위만인지 확인.
- `git diff --check` 통과.
- Codex 2차: 위 범위 재확인 후 커밋·push.

## Completion

- Codex가 커밋 메시지 `docs(BOHUMFIT-224): 하네스 3트랙 전환 — Cowork 퇴역·Code 구현트랙·위험도 규칙`으로 커밋·push.
- ※ Chat 지시에 언급된 "223 d73638c 미푸시분"은 실측과 다름: d73638c는 어느 브랜치에도 속하지 않은 구(舊) 223 커밋(amend로 대체 추정)이고, 최종 223 커밋 `2f041fc`는 이미 origin/main에 푸시 완료(로컬 HEAD = 원격 main = `2f041fc`). Codex는 224 단건만 커밋·push하면 된다.
