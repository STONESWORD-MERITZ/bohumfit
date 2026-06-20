# BOHUMFIT Three-Role Workflow

BOHUMFIT 작업은 새 채팅이 열려도 이어서 진행할 수 있도록 역할과 산출물을 분리한다.

## Roles

### 1. Claude Chat - Prompt Author

Claude Chat은 사용자의 요구를 바로 코딩 지시로 옮기지 않고, 먼저 취지를 작업 패킷으로 번역한다.

필수 산출:

- 사용자 의도: 왜 이 작업을 하는지, 어떤 결과가 좋아지는지.
- 완료 기준: 사용자가 실제로 확인할 수 있는 성공 조건.
- 작업 범위: 수정 허용 파일, 수정 금지 파일, 기존 동작 보존 조건.
- 위험: 개인정보, 결제, 법무, 배포, 데이터 삭제, 외부 대시보드 의존성.
- 검증: 자동 테스트, 수동 화면 확인, 실 PDF/실 결제/배포 확인 등.
- Next 담당: Cowork, Codex, Human 중 하나.

Claude Chat은 코드 완료를 선언하지 않는다. 애매한 요구는 더 안전하고 검증 가능한 프롬프트로 다듬어 Cowork 또는 Codex에 넘긴다.

### 2. Claude Cowork - Implementer

Cowork는 샌드박스에서 코드 읽기, 구현, 테스트 추가, /tmp 기반 1차 검증, handoff 작성을 맡는다.

Cowork 원칙:

- 마운트에서 git 명령을 실행하지 않는다.
- 구현은 사용자의 문자보다 취지를 우선한다.
- 누락될 가능성이 큰 회귀 테스트, 경계조건, 오류 메시지, UX 방어는 범위 안에서 보강한다.
- 범위 밖 문제가 보이면 고치지 말고 handoff Notes와 Next에 남긴다.
- 마운트 truncation, 권한 문제, 의존성 문제는 숨기지 않고 원문 증거를 남긴다.

### 3. Codex - Windows Authority

Codex는 Windows 원본에서 권위 검증, 좁은 보정, 커밋, 푸시, 배포 확인을 맡는다.

Codex 원칙:

- 시작 시 `git status --short -uall`로 워킹트리와 사용자 변경을 확인한다.
- Cowork 산출물을 그대로 믿지 않고, 파일 무결성·AST·타입·테스트·빌드·브라우저 또는 실 PDF를 재검증한다.
- 실패하면 푸시하지 않고, 정확한 실패 로그와 다음 처방을 handoff에 남긴다.
- 통과하면 태스크 범위 파일만 stage하고 커밋·푸시한다.
- 배포 대시보드, 결제, Supabase, 법무 문구처럼 Human 권한이 필요한 일은 방법만 정리한다.

## New Chat Packet

새 채팅으로 넘길 때는 아래 형식을 기본으로 한다.

```markdown
# [태스크ID 또는 작업명]

Owner flow: Claude Chat -> Claude Cowork -> Codex
Current owner: [Claude Chat / Cowork / Codex / Human]

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
- Windows 원본 파일이 마운트 절단본으로 오염되지 않았다.
- 지정 검증이 통과했다.
- 사용자의 실제 의도 기준으로 핵심 케이스가 확인됐다.
- stage 범위가 태스크 파일과 정확히 일치한다.
- 실패 또는 보류 사유가 있으면 push하지 않고 handoff에 남겼다.
