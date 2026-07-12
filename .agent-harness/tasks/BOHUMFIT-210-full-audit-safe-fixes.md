# BOHUMFIT-210 Full Audit + Safe Fixes

Owner flow: Human -> Codex Windows
Current owner: Codex

## Intent
- BOHUMFIT 전체 코드, 테스트, 문서를 전수 감사한다.
- 기준은 설계사 병목 자동화 완결성과 구조적 신뢰성(정확성, 투명성, 검증가능성, 데이터 정합, 무침묵실패)이다.
- 위험 영역은 자동수정하지 않고 Human 태스크로 분리한다.

## Scope
- 수정 허용:
  - hCaptcha fail-open 안전화
  - 로직 변경 없는 lint/dead-code 정리
  - 기준선 문서 정합
  - `.agent-harness/audit/BOHUMFIT-210-full-audit-report.md`
  - handoff/locks/task 문서
- 보고 전용:
  - `backend/pipeline/`
  - `backend/coverage/`
  - DB/RLS/Supabase 설정
  - phone_verified 서버 게이트 정책 변경
- 금지:
  - 실 PDF, 의료정보, 고객명, 주민번호, 키, 시크릿 커밋
  - pipeline/coverage/DB/auth 정책 위험 수정

## Work
- PASS 1: 정확성/신뢰성 감사.
- PASS 2: 완결성/UX 감사.
- PASS 3: 보안 잔여 감사와 hCaptcha fail-open 안전수정.
- PASS 4: 코드 건강, lint, 번호 발번, stash, 기준선 정합 감사.

## Verification
- `npx tsc -p tsconfig.app.json --noEmit`
- `npx tsc -p tsconfig.node.json --noEmit`
- `npm run build`
- `npm test`
- `cd backend && python -m pytest -q`
- hCaptcha key 없는 환경에서 OAuth와 이메일 UI가 렌더되는지 확인.

## Handoff Requirements
- 감사 리포트 경로와 요약.
- 자동수정 파일 목록.
- Human 태스크 분리 목록.
- 검증 결과와 커밋 해시.
