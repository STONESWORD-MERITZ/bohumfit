# BOHUMFIT-047 q_raw None 크래시 수정 + 파싱 가시성 + 비결정성 진단
## Owner
- Cowork (구현+회귀+진단) → Codex (Windows 검증·git) → Human (메모리 근본 대응 판단)

## 배경 (운영 로그)
- 같은 입력(files=3)인데 비결정: 07:47 flagged=16/q=3, 11:32 flagged=13/q=3, 12:07~ flagged=3/q=2(Q3 고착).
- `_build_pool` `TypeError: expected string or bytes-like object, got 'NoneType'` 다발 — `re.split(r"[,/\s]+", q_raw)`에서 q_raw=None(AI 항목 duty_question 누락).

## STEP 1 — q_raw None 크래시 수정 (구현)
- `pipeline/result_builder.py` `_build_pool`: `source`를 루프 상단으로 이동 후 `q_raw = item.get("duty_question")` 가 None/비문자열/빈값이면:
  · AI(source!=code) → 조용히 skip(038 정신: AI는 Q2만, q 불명이면 폐기)
  · 결정론(source=code) → `logger.warning` 후 skip(정상 결정론엔 q 항상 존재).
  → re.split 크래시 제거. **한 항목 결함이 전체 분석을 죽이지 않음.** `import logging`·모듈 logger 추가.
- 회귀 `tests/test_build_pool_qraw_guard.py`(4): ①q=None/누락/빈값 AI 혼입에도 무크래시·결정론 Q3 유지 ②정상 Q2 AI 유지 ③결정론 q=None skip·전체 생존 ④결정성.

## STEP 2 — 파싱 가시성 (구현, fail-loud)
- `analyzer.py`: `import logging/Counter`·logger.
  · `_parse_all_pdfs`: 파일별 성공 시 `INFO "BOHUMFIT-047 parsed: file=.. records=N ftype={..} errors=K"`. 예외 시 조용한 continue → `ERROR "parse failed: file=.. error=.."` + parse_errors 적재.
  · `run_analysis`: `record_counts = Counter(_ftype)` 산출 → 결과 dict에 `"record_counts"` 추가 + 완료 `INFO "run_analysis done: flagged=.. total_q=.. records={..} parse_errors=.."`.
- ※ main.py("analyze done" 로그·HTTP 응답에 record_counts 노출)는 **변경 허용 파일 외**라 미수정 — record_counts는 analyzer 결과 dict에 이미 실려 있어 main.py 1줄 후속(응답 패스스루)만 필요. handoff에 명시.

## STEP 3 — 비결정성 진단 (읽기 전용)
- **파싱은 결정적**: 기본진료 6회 반복=215 전부 동일, 처방조제=747, 세부=1117(반복 동일). 즉 record 수 변동 없음 → 파싱 자체는 비결정 아님.
- 피크 RSS(단일 PDF 파싱): 처방조제 239MB, 세부 250MB. (순차 파싱 OOM 핫픽스로 피크≈1파일분.)
- `main.py:318` `ANALYZE_TIMEOUT_SECONDS=300`(넉넉, 총 파싱 ~53s).
- **결론**: 운영 비결정(16/13/3)은 파싱 변동이 아니라 (a) **q_raw=None 크래시**(Gemini가 run마다 duty_question 누락 항목을 가변적으로 반환 → TypeError → 부분/실패 결과 → flagged 가변)와 (b) **메모리 압박**(파일당 ~250MB)으로 인한 OOM/부분 파싱(`parse_single_pdf`는 페이지 루프 예외 시 부분 레코드 반환, `_parse_all_pdfs`는 조용히 continue) → disease_stats 축소 → 5년 누적 Q3 소실. **flagged=3 고착**은 메모리 압박 지속(시간 경과 누적) 시 부분 파싱이 고착된 상태로 가장 잘 설명됨.

## 운영 flagged=3 고착 — 가장 유력 원인
지속적 메모리 압박 → 대용량 PDF(세부104p/처방70p) 부분·실패 파싱 → 소수 레코드만 집계 → 최근 Q1/Q2만, Q3 소실. q_raw 크래시가 비결정 노이즈를 가중. (STEP1로 크래시 제거, STEP2로 부분 파싱 가시화.)

## 근본 수정 방향 (Human 판단)
1. **메모리**: Railway 컨테이너 메모리 상향, 또는 페이지 스트리밍/조기해제로 피크 추가 억제, 또는 파싱 페이지수 vs 총 페이지수 비교로 **부분 파싱 감지 시 fail-loud/재시도**(현재 조용한 부분반환 금지).
2. **타임아웃**: 300s는 충분하나, 부분 결과를 성공처럼 반환하지 않도록 부분 파싱 가드.
3. (STEP2 후속) main.py가 record_counts/parse_errors를 HTTP 응답·"analyze done" 로그에 노출 → 프런트 "결과 불완전" 배지.

## 검증
- /tmp pytest **285 passed**(신규 4 포함, 회귀 0; `test_main_launch_guardrails`만 sandbox app-import 의존으로 제외 → Codex/Windows 권위). 기준선 281 + 4 = 285.
- result_builder.py 마운트 view 절단은 tail 재구성·writeback으로 보정 후 검증. 실 PDF 로컬 파싱만·PII 미커밋·작업파일 삭제.

## 작업 범위
- `pipeline/result_builder.py`·`analyzer.py`·`tests/test_build_pool_qraw_guard.py`(신규). 산식·Q구조·간편·결정론 불변. main.py 미변경(범위 외).
