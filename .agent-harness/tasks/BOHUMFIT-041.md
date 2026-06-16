# BOHUMFIT-041 Q2 추가검사 Gemini 게이팅 완화 + 임상의사 프롬프트 + 가능성 출력
## Owner
- Cowork (구현+회귀mock) → Codex (Windows 검증·git) → Human (실 Gemini E2E)

## 확정 사양
- 게이팅: 세부진료 검사근거 없어도 1년 내 진단코드(Q1/Q2) 있으면 Gemini 호출. 0건이면 미호출.
- 프롬프트: "한국 보험 심사 경험 풍부한 임상의사" 역할 + 판단기준(추가검사=A후 다른종류 B / 재검사=같은종류 재시행 / 제외=단순처방·추적관찰·일련진단·일반인 인식기대 없음 / 불확실시 보수적).
- 출력: 진단코드/병명별 가능성 "높음/낮음/해당없음". 해당없음·예외→기존 폴백.
- ★ 038 가드(_build_pool Q2 한정) 절대 불변. 한국어 프롬프트·JSON 스키마 보존.

## 구현 (완료)
- `backend/analyzer.py`: `_suspicion_prompt_items = list(_q1_items + _q2_health_items)`(검사근거 `_test_evidence_codes` 필터 제거). 0건이면 미호출 유지. 폴백·warning 경로 불변.
- `backend/pipeline/ai_judgment.py` `_call_q2_health_findings`: system_instruction "임상의사·보수적", contents에 판단기준 + 출력 스키마 `possibility(높음/낮음/해당없음)` 추가. 파싱: 높음/낮음만 `[추가검사·재검사 가능성 N] {suspicion}`로 부착, 해당없음·불명→미부착(폴백). 결정성 파라미터(temp0/seed42/top_k1)·JSON 스키마 보존. genai 실패→{} 폴백 유지.
- `src/pages/Disclosure.tsx`: q2_suspicion 있을 때 "AI 임상 참고 판단(가능성 추정)·확정 아님" 참고 문구. (가능성 텍스트는 q2_suspicion에 인코딩되어 기존 clinicalReviewText로 표시.)
- `backend/tests/test_q2_gemini_mock.py`(신규 8): genai.Client mock — 높음/낮음 부착·해당없음 폴백·예외 폴백·프롬프트 임상의사/기준 포함·결정성·★게이트 완화(소스)·★038 가드 보존(소스).

## 검증
- /tmp pytest **203 passed**(신규 8 포함; 마운트 손상 test_filters·test_report_pdf_q1q5·test_history_filter_fix 제외). 실마운트 신규 8/8·038 가드 grep=1.
- ⚠ 실제 Gemini 호출 불가(샌드박스) → mock으로 게이팅/프롬프트/파싱/폴백 검증. 실 판단은 Human E2E.
- Codex(Windows): 전체 pytest·tsc/lint/test/build.

## 작업 범위
- analyzer.py(게이트), ai_judgment.py(Q2 함수), Disclosure.tsx(참고문구), tests. ★result_builder 038 가드·결정론 룰·간편 불변.
