# BOHUMFIT-169 — Q2 소견용 Gemini 호출 비활성화 (비용 절감)

## 배경 (Human 확정)
168에서 추가검사/재검사 소견을 결과에서 완전 제거. 그러나 소견 생성용 Gemini 호출(ai_judgment.py)은 계속 실행 → 버려지는 결과에 API 비용. Human 결정: 호출 중단.

## 설계 원칙
- ★backend/pipeline/·ai_judgment 경로 수정 허용.
- 삭제가 아닌 **플래그 방식**(환경변수/상수). 되돌릴 땐 플래그만 재활성화.
- Q2 소견 외 ai_judgment/Gemini 사용 경로가 있으면 절대 무영향(있으면 Q2만 선별 차단).

## Step 0 진단(필수)
- ai_judgment Gemini 호출 함수 + 모든 caller 매핑.
- Q2 외 용도 존재 여부 확정(있으면 handoff 명시·Q2만 차단).
- 차단 시 하류 기대 반환형 확인 → "의심 없음" 안전 기본값 설계(168 _strip이 어차피 제거).

## Step 1 구현
- 플래그 `ENABLE_Q2_AI_JUDGMENT`(env, 기본 false): false면 Gemini 호출 없이 즉시 "의심 없음"(빈 dict/리스트) 반환. 프롬프트·파싱 보존(삭제 금지).
- 결과 무결성: 168 이후 결과와 완전 동일(호출만 사라지고 출력 변화 0).
- 신규 `backend/tests/test_gemini_disable_169.py`: (a)off시 Gemini 미호출 (b)off시 결과=168 기준 (c)on시 기존 경로 정상.
- 플래그로 깨지는 기존 Gemini 테스트는 on 명시로 수정 → 목록 handoff.

## 수정 금지
- ai_judgment 프롬프트/파싱 삭제(보존, 차단만). Q2 외 Gemini 경로. 프런트 전체.

## 검증
- Step0(Q2 외 용도) handoff / 신규 3케이스 / 전체 pytest=Codex(기준선 462/8→증가, 신규 명시) / Railway env 안내(기본 false라 배포 무설정, 재활성화 시 ENABLE_Q2_AI_JUDGMENT=true).

## 커밋(Codex)
feat(BOHUMFIT-169): Q2 소견용 Gemini 호출 비활성화 (플래그 기본 off)
