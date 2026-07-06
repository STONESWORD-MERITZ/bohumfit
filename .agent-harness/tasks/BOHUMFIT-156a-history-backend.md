# BOHUMFIT-156a — 분석 히스토리 백엔드 API

Owner flow: Claude Chat -> Claude Cowork -> Codex
Current owner: Cowork

## Intent
- 설계사가 분석 결과를 저장해 두고 나중에 다시 열람할 수 있게 한다(고객 상담 연속성).
- 실명 대신 별칭(label)만 저장해 개인정보 리스크를 최소화한다.

## 공통 확정 정책 (Human 결정 완료)
- 무료 저장 한도 10건 / `profiles.role='internal'` 무제한.
- 보관 90일 (초과분 조회 제외 + lazy 삭제).
- label = 설계사 입력 별칭 (실명 저장 금지 — 프런트 안내 필수).
- Supabase 테이블 `bohumfit_analysis_history` + RLS는 Human이 이미 생성함.

## Step 0 — 진단 (구현 전 필수, handoff 기록)
1. backend의 per-user 인증 식별 패턴 확인
   (usage_logs·billing_status·verify-phone 등 기존 경로를 그대로 따를 것 — 새 인증 방식 발명 금지)
2. Supabase 접근 방식 확인 (service role 여부, RLS와의 관계)
3. 분석 결과 페이로드 크기 실측 (jsonb 적정성 — 과대 시 축약 전략 제안)

## Step 1 — API 구현 (기존 라우터 패턴 준수)
- POST /history — 저장 (label, mode, result)
  · 무료: 10건 초과 시 409 + 안내 / internal: 무제한
- GET /history — 본인 목록 (id·label·mode·created_at만, result 제외, 페이지네이션)
- GET /history/{id} — 본인 소유 단건 result
- DELETE /history/{id} — 본인 소유 삭제
- 90일 초과: 조회 제외 + lazy 삭제 (설계 근거 handoff 기록)

## Step 2 — 테스트: backend/tests/test_history_156.py
(a) 저장→목록→단건→삭제 왕복 (b) 타인 레코드 차단
(c) 무료 10건 초과 409 (d) internal 무제한 (e) 90일 초과 제외

## Scope
- 수정 허용: backend/main.py, backend/tests/test_history_156.py(신규)
- 수정 금지: 분석 파이프라인 로직 / 기존 usage_logs·billing 로직 (패턴 참조만)
- 보존: 기존 엔드포인트 동작 전부

## Verification
- 자동: 신규 테스트 5케이스(/tmp 1차, 전체 pytest는 Codex/Windows 권위)
- 기준선: backend pytest 466 passed / 8 skipped → 증가 예상, 신규 기준선 handoff 명시

## Handoff Requirements
- Step 0 진단 결과, 90일 lazy 삭제 설계 근거, 신규 기준선 기록
