# BOHUMFIT-203 - 데이터 접근 및 개인정보 보안 정책 문서화

Owner flow: Human -> Codex Windows
Current owner: Codex Windows

## Intent

- BOHUMFIT의 신규 Supabase 테이블·RPC·PII 경로에 공통으로 적용할 접근 제어 기준을 영구 의사결정 문서에 남긴다.
- 2026-07-09 레드팀 F-01 대응 이력과 BOHUMFIT/FitHere 공유 Supabase 변경 주의사항을 명확히 한다.

## Scope

- Allowed: `.agent-harness/decisions.md`, this task file, `.agent-harness/handoff.md`, `.agent-harness/locks.md`.
- Excluded: application code, backend, Supabase migration/RLS/grant execution, PII data, `backend/pipeline/`.

## Work

1. default deny, 소유자 RLS, PII 최소화, 감사 로깅 원칙을 기록한다.
2. 신규 테이블 RLS/grant/소유자 SELECT/anon 파괴 권한 체크리스트를 기록한다.
3. F-01 대응 이력과 공유 인스턴스 저트래픽·검토 후 실행 절차를 기록한다.

## Verification

- 문서 범위만 변경됐는지 `git diff --check`, `git diff --name-only`로 확인한다.
- 정책 핵심 키워드와 F-01/공유 Supabase 주의사항이 `decisions.md`에 존재하는지 확인한다.
