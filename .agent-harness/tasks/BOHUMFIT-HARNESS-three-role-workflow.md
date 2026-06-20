# BOHUMFIT-HARNESS three-role workflow

## Owner
Codex

## Intent
사용자가 앞으로 새 채팅을 계속 열어도 업무 맥락이 끊기지 않도록, Claude Chat / Claude Cowork / Codex의 역할을 명확히 나누고 하네스 문서에 고정한다.

## Scope
수정 허용:

- `AGENTS.md`
- `CLAUDE.md`
- `.agent-harness/WORKFLOW.md`
- `.agent-harness/tasks/BOHUMFIT-HARNESS-three-role-workflow.md`
- `.agent-harness/handoff.md`
- `.agent-harness/locks.md`

수정 금지:

- 현재 Cowork가 잠근 SaaS/결제/본인인증 파일
- 백엔드·프런트 기능 코드
- Supabase migration
- PII/PDF/brand 자산

## Work

- 기존 운영 문구를 three-role 구조로 갱신한다.
- Claude Chat은 프롬프트 작성자, Cowork는 코딩 담당, Codex는 Windows 검증·커밋·푸시·배포 확인 담당으로 정의한다.
- 새 채팅에 붙여넣을 수 있는 작업 패킷 형식을 만든다.
- 사용자의 문장보다 취지를 기준으로 더 좋은 결과를 검증·보강하는 원칙을 문서화한다.

## Verification

- 문서 범위 외 변경 없음 확인.
- `git diff --check` 통과.
- Cowork 072~074 active lock 보존.

## Completion

- 문서 변경 커밋·푸시.
- handoff에 변경 요약과 다음 운영 방식 기록.
