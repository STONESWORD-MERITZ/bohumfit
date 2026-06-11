# BOHUMFIT-LAUNCH-001: BOHUMFIT.ai 오픈 준비 1차 구현

## Owner
- Codex

## Status
- Completed

## Context
- 운영 도메인을 `bohumfit.ai`로 선택했다.
- 사용자 노출 브랜드는 `BOHUMFIT` / `보험핏`으로 전환한다.
- 내부 코드/하네스 태스크 prefix는 기존 이력 보존을 위해 `BOHUMFIT-*`를 유지한다.
- 서비스는 보험 가입을 보장하지 않고, 고지 리스크 점검 및 상담 보조자료를 제공한다.

## Scope
- 외부 노출 브랜드/카피 전환
- `bohumfit.ai` 도메인 기준 CORS/CSP/env 템플릿 정리
- 오픈 전 리스크 체크 문서화
- 민감정보·제3자 자료 동의 UX 보강
- 복사/고객 안내 문구 면책 고정
- 기존 인증/업로드 제한/로그 필터링 상태 검증

## Verification
- `cd backend && python -m pytest -q`
- `npx tsc -p tsconfig.app.json --noEmit`
- `npx tsc -p tsconfig.node.json --noEmit`
- `npm run lint`
- `npm test`
- `npm run build`
- Browser smoke check for the local app when practical.

## Notes
- 실제 도메인 구매 및 Vercel/Supabase 콘솔 설정은 코드 커밋만으로 완료할 수 없으므로 handoff에 Human 조치로 남긴다.
