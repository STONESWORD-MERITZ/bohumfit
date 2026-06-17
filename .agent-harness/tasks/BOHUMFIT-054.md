# BOHUMFIT-054 백로그 4건 — AI예산 Q2영향 진단 + 파싱불완전 경고 + 5년기준 명시 + 대용량 부하 점검
## Owner
- Cowork (STEP2/3 구현 + STEP1/4 진단) → Codex (Windows 검증·커밋) → Human (STEP1·4 근본대응 판단)

## STEP 1 — AI 5초 예산이 Q2(041)와 충돌하는가 (읽기 전용)
- 코드(analyzer.py): `_ai_budget_seconds()` 기본 **5초**(`BOHUMFIT_AI_BUDGET_SECONDS`). `_bounded_ai_enrichment()`(의학판단+Q2 findings)를 `asyncio.wait_for(timeout=budget)`로 감쌈. **타임아웃 시** `_q2_findings`·`_med_result`가 기본값({})로 남고 `retry_warnings`에 "5초 안에 끝나지 않아 결정론 결과 먼저 표시" 추가.
- **실데이터 기본진료 실측(run_analysis, AI mock으로 지연 시뮬)**:
  · budget=60s + Q2 8s → N95 **Q2 항목 있음** + `q2_suspicion`="[추가검사·재검사 가능성 높음]…" (041 표시 정상).
  · budget=5s + Q2 8s → N95 **Q2 항목 있음**(결정론) but `q2_suspicion=''`(041 표시 **소실**) + 타임아웃 경고.
  · budget=0 → 항목 있음·suspicion 없음·"비활성화" 경고.
- **결론**: 5초 예산은 **Q2 고지 항목을 드롭하지 않음**(결정론 항목, 고지 누락 아님). 단 **041의 "가능성 높음/낮음" AI 주석은 Gemini 응답이 5초 초과 시 소실**(graceful 폴백·경고 표시). gemini-2.5-flash Q2 프롬프트(임상의사 역할+기준)는 통상 3~8s → 5초는 경계값, 운영서 041 주석이 자주 누락될 수 있음.
- **수정 방향(구현 금지·Human)**: 고지 누락은 없으나 041 표시 보존을 원하면 ① `BOHUMFIT_AI_BUDGET_SECONDS` ~10~12s 상향(052가 프록시 타임아웃 회피로 5s 설정 — 헤드룸 필요) ② 또는 Q2 전용 예산. 운영 retry_warnings 빈도로 타임아웃율 측정 권장.

## STEP 2 — 파싱 불완전 사용자 경고 (구현)
- `analyzer.py`: `_parse_quality_warning(record_counts)` 신설 — **보수적**(unknown ≥5건 AND 전체의 ≥30%)일 때만 사람이 읽는 경고 문자열 반환. run_analysis가 record_counts 직후 계산해 결과 dict에 `"parse_quality_warning"`(None=정상) 추가. **분석은 막지 않음**(경고만).
- 회귀 `tests/test_parse_quality_warning.py`(4): 정상→None·unknown다수→경고·경계(5건/30%)·빈값 안전.
- **프런트 표시는 범위 외** → Disclosure.tsx가 `result.parse_quality_warning` 있으면 배너 노출하는 후속 필요(Next).

## STEP 3 — "5년 기준" 명시 (구현)
- 확인: 화면 섹션 헤더가 이미 `cleanQTitle` 로 **"5년 이내 입원·수술·통원·투약"** 표시(L549), 카드 detail도 "5년이내 통원 N회" 표시(L411). PDF(051)와 동일하게 5년 기준 명시돼 있음.
- 보강(칩 레벨 명확화 — 정답표 전기간/10년 혼동 방지): `Chip`에 `title?` 추가, DiseaseCard에서 질문별 창 라벨(Q1 3개월·Q2 1년·Q3 5년·Q4 5~10년·Q5 5년; 간편 Q2 10년) → 통원/입원/수술/투약 칩 hover 툴팁 "가입예정일 기준 {창} 집계입니다.". **표현만**, 카운트/판정 로직 무변경.
- `src/pages/Disclosure.tsx` 만 변경(tsc/build는 sandbox 불가 → Codex).

## STEP 4 — 대용량 10파일 부하 (읽기 전용)
- 단일 파싱 측정(BOHUMFIT-047 권위): 세부 104p ≈ **27s/peak RSS 250MB**, 처방 70p ≈ 22s/239MB. (이번 세션은 샌드박스 부하로 재측정 타임아웃 → 047 수치 인용.)
- `_parse_all_pdfs` 순차 파싱(OOM 핫픽스·gc·flush_cache) → **피크 RSS ≈ 1파일분(~250-300MB)**. 레코드는 경량 dict(파일당 ~수십~수백) 누적이라 메모리 영향 미미.
- `main.py:321` `ANALYZE_TIMEOUT_SECONDS=300`.
- **결론**:
  · **메모리**: 10 대용량 파일도 순차라 피크 ~250-300MB → Railway 512MB~1GB 내 **안전**(병렬화 금지 유지가 핵심).
  · **시간**: 10 × 104p ≈ 270s 파싱 + AI 5s + 집계/리포트 → **300s 타임아웃 근접/초과 위험**(최악: 10×100p+ = ~1000p+). 현실 고지형 파일(병력 53~204KB·소수 페이지)은 10개라도 ~30~60s로 안전.
  · **한계 추정**: 합산 ≤ ~600~700p(≈≤180s)면 여유 / 1000p+면 타임아웃 위험. **OOM보다 타임아웃이 먼저 한계**.
- **근본 대응(구현 금지)**: ① 업로드 시 총 페이지 추정→과대 시 분할 안내 ② 타임아웃 상향(프록시 한계 고려) ③ 메모리는 순차 파싱으로 충분 — 타임아웃 대응 우선.

## 검증
- /tmp pytest **311 passed**(신규 STEP2 4 포함, 회귀 0; `test_main_launch_guardrails`만 sandbox app-import 제외 → Codex). report_pdf 템플릿/analyzer 마운트 view 절단은 tail 재구성으로 검증.
- 자체 점검: ☑STEP1 5초 Q2 실측 결론 ☑STEP2 경고+회귀2(정상/비정상) ☑STEP3 5년 명시 확인·칩 툴팁 보강 ☑STEP4 부하 수치·한계 ☑분석 카운트/판정 무변경 ☑회귀0.

## 작업 범위
- 구현: `analyzer.py`(parse 품질 경고)·`src/pages/Disclosure.tsx`(칩 창 툴팁)·신규 `tests/test_parse_quality_warning.py`. 진단: STEP1/4(읽기). 분석 카운트·판정 로직 무변경.

## Next
- **Codex(Windows)**: 전체 pytest·tsc/lint/test/build(Disclosure.tsx 포함) → 커밋·푸시. 커밋: `BOHUMFIT-054: 파싱 불완전 경고(parse_quality_warning) + 통원/투약 칩 5년 기준 툴팁`.
- **Human**: STEP1 AI 예산값(5s vs ↑) 판단 / STEP4 대용량 타임아웃 근본대응(페이지 한계·타임아웃·플랜).
- **프런트 후속**: Disclosure.tsx가 `parse_quality_warning` 배너 노출(STEP2 표면화 완결).
