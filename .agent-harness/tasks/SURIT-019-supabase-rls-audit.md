# SURIT-019: Supabase 저장 범위 및 RLS 진단

## Owner
- Codex

## Status
- Completed

## Type
- Diagnosis only

## Context
- BOHUMFIT 출시 전 Supabase에 저장되는 데이터 범위와 건강정보 사용자 격리(RLS) 위험을 확인한다.
- 이번 태스크는 코드 수정 없이 저장소 내 Supabase 사용 지점과 RLS 정책 정의 존재 여부만 진단한다.

## Scope
- Read-only investigation:
  - `src/`
  - `backend/`
  - Supabase 관련 설정/마이그레이션 파일
  - `.agent-harness/handoff.md`
- No runtime code changes.
- No lock added.
- No commit.

## Investigation
- Supabase client 호출 전수 검색: `.from`, `.insert`, `.select`, `.update`, `.rpc`, `storage`.
- 진료기록 원문, 분석결과, 질병정보, 업로드 PDF가 Supabase DB/Storage에 저장되는지 확인.
- 인증 전용인지 인증+데이터 저장인지 구분.
- RLS 정책 파일 또는 Supabase 마이그레이션 존재 여부 확인.
- anon key 접근 범위는 코드 흐름상 가능성으로만 기록한다.

## Verification
- `cd backend && python -m pytest -q`

## Expected Output
- Supabase 사용 용도 분류.
- 건강정보 저장 위치 또는 미저장 결론.
- RLS 정책 코드 정의 존재 여부.
- 출시 차단급 위험 여부와 후속 태스크 제안.
