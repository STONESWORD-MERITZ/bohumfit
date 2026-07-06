# BOHUMFIT-171b — 분석 히스토리 2트랙 (최근 자동 10개 + 저장)

Owner flow: Claude Chat -> Claude Cowork -> Codex
Current owner: Cowork
선행: BOHUMFIT-156a/156b, 171a. Human이 track 컬럼 SQL 실행 완료
(bohumfit_analysis_history.track: 'recent'|'saved', 기본 'saved')

## Human 확정 요구
- 히스토리 2트랙: ① 최근 분석 = 분석 실행 시 자동 기록, 최근 10개 롤링 (기본 탭)
  ② 저장됨 = 기존 156 수동 저장 트랙
- 분석 결과 화면에 "가이드 다시보기"처럼 히스토리 재진입 동선 연결

## 정책 (명세 확정값)
- 최근 트랙: 전 사용자 10개 롤링(초과 시 오래된 것 자동 삭제), 보관 7일
- 저장 트랙: 기존 정책 유지 (무료 10건/internal 무제한, 90일)
- 최근 → 저장 승격: 최근 탭 항목 "저장" 버튼 (별칭 모달 재사용, track='saved' 전환 — 저장 한도 검사 적용)

## Step 1 — 백엔드 (156 API 확장)
- POST /history: track 파라미터 ('recent'|'saved', 기본 'saved')
  · recent: 한도 검사 없이 저장 + 본인 recent 10개 초과분 오래된 순 삭제 / saved: 기존 로직
- analyze 응답 직후 서버측 recent 자동 기록 (customer_name strip 동일, 실패해도 분석 응답 정상 — try/except 격리)
- GET /history: track 쿼리 필터
- PATCH /history/{id}/save: recent → saved 승격 (한도 검사)
- lazy 삭제: saved 90일 + recent 7일
- 테스트 backend/tests/test_history_171.py:
  (a) 분석 시 recent 자동 기록 (b) recent 11개째 롤링 삭제 (c) recent→saved 승격+한도
  (d) track 필터 (e) recent 7일 만료

## Step 2 — 프런트 (History.tsx 확장)
- 탭 2개: [최근 분석(기본)] [저장됨] — 156 목록 컴포넌트 재사용
- 최근 탭: 캡션 "최근 10건이 자동 기록되며 7일 후 삭제됩니다" + 항목별 "저장" 버튼(별칭 모달)
- 저장 탭: 기존 그대로

## Step 3 — 동의 문구 정합 (법무 — 필수)
- 업로드 동의 문구 "서비스 데이터베이스에 저장되지 않습니다" → 자동 기록과 충돌 해소:
  "원본 PDF는 분석 직후 폐기됩니다. 분석 결과 요약은 편의를 위해 최근 10건 자동 기록(7일 보관)되며,
  히스토리에서 직접 삭제할 수 있습니다." 취지로 수정
- PrivacyPolicy 보관 조항에 자동 기록 트랙(7일) 1줄 추가

## Step 4 — 결과 화면 동선
- "가이드 다시보기" 인접 위치에 "분석 히스토리" 링크/버튼 (/history, 세컨더리 스타일)

## 수정 금지
- 분석 파이프라인 로직 (자동 기록은 응답 조립 이후 부수 저장만)
- 156의 저장 트랙 정책값 변경 금지

## Verification
- 신규 테스트 5케이스 /tmp 1차, 전체 pytest·tsc·build = Codex 권위 (기준선 473/8에서 증가 예상 — 신규 기준선 명시)
- 자동 기록 실패 시 분석 응답 정상 (격리 테스트)
- raw gray 0 / 접근성 후퇴 0

## 커밋 (Codex)
feat(BOHUMFIT-171b): 분석 히스토리 2트랙 (최근 자동 10개·저장 승격·동의 문구 정합)
