# BOHUMFIT Three-Role Workflow

BOHUMFIT 작업은 새 채팅이 열려도 이어서 진행할 수 있도록 역할과 산출물을 분리한다.

> 구성 변경(BOHUMFIT-224, 2026-07-17): 구현 트랙이 Claude Cowork(샌드박스)에서 Claude Code(Windows 로컬)로 교체됐다. 순서 불변: Chat → Code → Codex. 과거 Cowork 표기는 역사 기록이며, 해석 규칙은 `AGENTS.md`의 "[퇴역] Cowork 이력" 참조.

모든 레포 작업(Claude Code·Codex)은 시작 전 루트 게이트를 통과한다: ① `pwd`=`C:\Users\18_rk\BOHUMFIT` ② remote=`STONESWORD-MERITZ/bohumfit` ③ 리트머스 파일 `.agent-harness/tasks/BOHUMFIT-219-shared-rls-migration-alignment.md` 존재. 불일치 시 즉시 중단·Human 보고.

## Roles

### 1. Claude Chat - Prompt Author

Claude Chat은 사용자의 요구를 바로 코딩 지시로 옮기지 않고, 먼저 취지를 작업 패킷으로 번역한다. 레포 접근은 없다.

필수 산출:

- 사용자 의도: 왜 이 작업을 하는지, 어떤 결과가 좋아지는지.
- 완료 기준: 사용자가 실제로 확인할 수 있는 성공 조건.
- 작업 범위: 수정 허용 파일, 수정 금지 파일, 기존 동작 보존 조건.
- 위험: 개인정보, 결제, 법무, 배포, 데이터 삭제, 외부 대시보드 의존성.
- 위험도 판정: 저위험(문구·스타일·소규모 UI·문서 — "Code 커밋 허용" 명시 가능) / 고위험(DB·보안·인증·pipeline·coverage 코어·대형 리팩터·마이그레이션 — 풀 하네스 + DB는 Human 게이트). 위험도 판단·명시는 Chat 책임이다.
- 검증: 자동 테스트, 수동 화면 확인, 실 PDF/실 결제/배포 확인 등.
- Next 담당: Claude Code, Codex, Human 중 하나.

Claude Chat은 코드 완료를 선언하지 않는다. 애매한 요구는 더 안전하고 검증 가능한 프롬프트로 다듬어 Claude Code 또는 Codex에 넘긴다.

### 2. Claude Code - Windows Local Implementer

Claude Code는 Windows 로컬(레포 원본)에서 코드 읽기, 구현, 테스트 추가, 1차 검증, handoff 작성을 맡는다. 샌드박스 제약("실행 불가")은 없다 — tsc/lint/build/pytest를 직접 실행하고 그 결과를 신뢰한다. 권위 커밋은 Codex가 담당한다.

Claude Code 원칙:

- git 읽기(pwd·remote·status·log·diff)는 허용, git 쓰기(add/commit/push)는 기본 금지. 예외는 저위험 태스크에서 Chat이 "Code 커밋 허용"을 명시한 경우뿐이다.
- 구현은 사용자의 문자보다 취지를 우선한다.
- STEP 0 실측 없이 수정하지 않는다. 최소 수정 — 스펙 밖 발견은 기록만 하고 Human이 결정한다.
- 누락될 가능성이 큰 회귀 테스트, 경계조건, 오류 메시지, UX 방어는 범위 안에서 보강한다.
- 범위 밖 문제가 보이면 고치지 말고 handoff Notes와 Next에 남긴다.
- 이상 신호(빌드 산출물 급감·핵심 구조 "없음" 보고·파일 절단 징후·과거 커밋 회귀) 감지 시 즉시 중단·보고하고, 권한·의존성 문제는 숨기지 않고 원문 증거를 남긴다.

### 3. Codex - Second-Pass Verifier & Committer

Codex는 Windows 원본에서 2차 검증, 커밋, 푸시, 배포 확인을 맡는다. 검증·반려 전용이며 직접 수정은 한 줄급만 허용한다 — 그 이상이 필요하면 반려하고 handoff로 Claude Code에 회송한다.

Codex 원칙:

- 시작 시 `git status --short -uall`로 워킹트리와 사용자 변경을 확인한다.
- Claude Code 산출물을 그대로 믿지 않고, 타입·테스트·빌드·브라우저 또는 실 PDF를 재검증한다.
- 실패하면 푸시하지 않고, 정확한 실패 로그와 다음 처방을 handoff에 남겨 Claude Code에 회송한다.
- 통과하면 태스크 범위 파일만 stage하고 커밋·푸시한다. 커밋 전 `AGENTS.md`의 "커밋 전 검증 계약"(tsc app/node·lint·build·pytest 618/8 기준선·SURIT/구브랜드 grep 0건·보호 영역 diff 검사)을 만족해야 한다.
- 배포 대시보드, 결제, Supabase, 법무 문구처럼 Human 권한이 필요한 일은 방법만 정리한다.

## New Chat Packet

새 채팅으로 넘길 때는 아래 형식을 기본으로 한다.

```markdown
# [태스크ID 또는 작업명]

Owner flow: Claude Chat -> Claude Code -> Codex
Current owner: [Claude Chat / Claude Code / Codex / Human]
Risk tier: [저위험 (Code 커밋 허용 여부 명시) / 고위험 (풀 하네스, DB는 Human 게이트)]

## Intent
- 사용자가 진짜 해결하려는 문제.

## Scope
- 수정 허용 파일:
- 수정 금지 파일:
- 보존해야 할 기존 동작:

## Work
- 해야 할 일:
- 하지 말 것:

## Verification
- 자동 검증:
- 수동 검증:
- 실데이터/배포 확인:

## Handoff Requirements
- Changed:
- Verified:
- Notes:
- Next:
```

## 호출 템플릿

Claude Chat이 각 트랙을 호출할 때 아래 2벌을 기본으로 한다.

### Claude Code용 (구현 + 1차 검증 + handoff, git 쓰기 금지)

```text
하네스 방식으로 진행해줘. Claude Code 구현 트랙. 발번 {번호}.
루트 게이트(pwd·remote·리트머스) 통과 후 AGENTS.md·handoff·WORKFLOW·태스크 파일을 읽고 locks 잠금.
작업: {구현 내용}
검증(1차, 로컬 직접 실행): tsc app/node · lint · build · pytest(기준선 618/8) + 태스크별 검증.
완료 후 handoff 상단 기록(Next: Codex)·locks 해제.
git 쓰기(add/commit/push) 금지 — 커밋은 Codex.
{저위험이고 Code 커밋을 허용하는 경우에만: "저위험 — Code 커밋 허용. 검증 계약 통과 후 커밋·push까지."}
```

### Codex용 (2차 검증 + 커밋·push)

```text
하네스 방식으로 진행해줘. Codex 2차 검증 트랙. 발번 {번호}.
루트 게이트 통과 후 handoff 최신 항목·태스크 파일 확인, `git status --short -uall` 확인.
Claude Code 산출물을 재검증: tsc app/node · lint · build · pytest(기준선 618/8) +
커밋 전 검증 계약(SURIT 0건·구브랜드 색상 0건·보호 영역 diff 검사).
통과 시 태스크 범위 파일만 stage → 커밋 메시지 `{메시지}` → push.
실패·한 줄급 초과 수정 필요 시 커밋하지 않고 handoff로 Claude Code에 회송.
```

## Intent-Based Execution

AI는 사용자의 지시를 다음 순서로 해석한다.

1. 사용자가 원하는 최종 상태를 먼저 파악한다.
2. 문자 그대로 수행하면 위험하거나 불완전한 부분을 찾는다.
3. 작업 범위 안에서 더 나은 결과를 만드는 보강을 한다.
4. 범위 밖이거나 Human 결정이 필요한 부분은 자동 실행하지 않고 Next로 남긴다.
5. 검증은 "명령이 통과했다"에서 끝내지 않고, 사용자가 기대한 결과가 실제로 재현되는지 확인한다.

## Publish Gate

Codex가 다음 조건을 만족할 때만 push한다.

- 최신 handoff와 task를 읽었다.
- active lock 충돌이 없다.
- 파일 절단·이상 신호(빌드 산출물 급감·핵심 구조 소실·과거 커밋 회귀)가 없다. (마운트 절단본 오염 검사는 Cowork 퇴역으로 이력 규칙)
- 지정 검증이 통과했다.
- 사용자의 실제 의도 기준으로 핵심 케이스가 확인됐다.
- stage 범위가 태스크 파일과 정확히 일치한다.
- 실패 또는 보류 사유가 있으면 push하지 않고 handoff에 남겼다.
