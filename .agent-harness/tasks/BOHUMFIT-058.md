# BOHUMFIT-058 동적 AI 예산 (남은시간 기반·최대 20초)

## Owner
- Cowork (구현+회귀) → Codex (Windows 전체 검증·실 PDF AI 예산 로그 확인·커밋·푸시) → Human(필요 시 마진/상한 튜닝)

## 배경 (057 진단 확정)
- 타임아웃 사슬 가장 약한 고리 = 서버 분석 상한 300s(main.py `ANALYZE_TIMEOUT_SECONDS`, 코드 내 완전 통제).
- Railway 인프라 타임아웃 = 900s(15분, 확인됨) → 여유 충분. 프런트 fetch abort = 350s.
- 기존 AI 예산 고정 5s → 041 "가능성 높음/낮음" Q2 주석 자주 소실(Gemini Q2 실측 3~8s).
- AI 예산은 파싱시간에 가산: 소형 3~4파일 파싱 17~30s(여유)·대용량 10파일 ~270s(빠듯).

## 확정 사양 (Human)
- 서버 300s 유지(변경 금지). 프런트 350s 무변경.
- AI 예산을 "남은 시간 기반 동적"으로(최대 20s). 끊김 재발 방지가 절대 전제.

## 구현 (analyzer.py / main.py)
- **공식**: `available = SERVER_ANALYZE_DEADLINE_SECONDS(300) - 경과 - 안전마진(30)`; `budget = clamp(available, 0, 상한)`.
  - 상한(MAX) = `BOHUMFIT_AI_BUDGET_SECONDS` env 설정 시 그 값(override), 미설정 시 기본 **20s**.
  - floor=0: 남은 시간 없으면 0 → AI 우아하게 skip(결정론 결과 유지·고지 누락 0 — 052 정신).
  - 동적 clamp 는 env override 여부와 무관하게 **항상** 적용.
- `analyzer.py`:
  - `import time` 추가. 상수 `SERVER_ANALYZE_DEADLINE_SECONDS=300`(단일 소스)·`_MAX_AI_BUDGET_SECONDS=20`·`_AI_BUDGET_SAFETY_MARGIN=30`.
  - 기존 `_ai_budget_seconds()`(고정 5) **삭제** → `_ai_budget_ceiling()`(상한 결정·env override) + `_dynamic_ai_budget(elapsed, ceiling)`(clamp) 신설.
  - `run_analysis` 진입에 `_t0 = time.monotonic()`(서버 300s wait_for가 감싸는 구간 시작점).
  - AI 예산 블록: 고정값 → `_elapsed = monotonic-_t0`·`_dynamic_ai_budget(...)`로 동적화. 분기: `budget>0`→AI 실행 / `ceiling<=0`→"비활성화"(env=0) / else→"시간이 촉박…AI skip". 로그 `BOHUMFIT-058 ai budget: elapsed=Ns avail=Ns budget=Ns ceiling=Ns` 추가.
  - 052 best-effort 구조(`_bounded_ai_enrichment` 등)·동기경로 PDF별 Gemini 제거 상태 **불변**(예산값만 동적화).
- `main.py`: `from analyzer import ..., SERVER_ANALYZE_DEADLINE_SECONDS`; `ANALYZE_TIMEOUT_SECONDS = SERVER_ANALYZE_DEADLINE_SECONDS`(값 300 무변경, 단일 소스 공유로 두 곳 어긋남 방지). **순환 import 없음**(analyzer는 main을 import하지 않음).

## 회귀 테스트 (신규 `tests/test_dynamic_ai_budget.py`, 6)
- ① 빠른 파싱(경과 1s) → 예산 20(상한). ② 느린 파싱(경과 265s) → 5로 수축·283s → 0. ③ 남은시간 ≤0(290s/300s/deadline-margin) → 0.
- ④ env 상한 override(8→8·60이어도 285s경과 시 0·미설정 20·0→0·비정상→기본20). ⑤ AI skip(budget 0·상한>0 강제) → 결정론 standard_reports 정상·"시간이 촉박" 경고·"비활성화" 아님·Gemini 미호출·크래시 0.
- ⑥ main 상수 공유(ANALYZE_TIMEOUT==SERVER_ANALYZE_DEADLINE==300; sandbox app-import 불가 시 skip-guard).
- 기존 `test_analyze_fast_path`(env=1→예산1 실행·env=0→비활성화)와 정합 보존.

## 검증
- /tmp(마운트 복구본) **①②③④ 4/4 + 독립 회귀 54 passed**(056 nhis 포함·pdf_parser 재구성본·필터/집계·pw후보), **회귀 0**.
- ⚠ **이번 세션도 마운트 view 심각 손상**: 샌드박스 analyzer.py(run_analysis 본문 절단·`standard_reports` return 누락→None)·report_pdf.py·pdf_parser.py가 stale/절단(모두 **058 신규 본문은 무관**). pdf_parser는 tail 재구성으로 056 테스트 통과, analyzer 본문 의존 통합테스트(⑤·test_analyze_fast_path)·전체 pytest는 **Codex/Windows 권위**. slowapi 미설치로 main 직접 import 테스트도 Codex.
- 실파일(Read/Grep) 확인: analyzer L1024~1060 동적 예산+분기+로깅 정상, t0 진입부 정상, helpers L19~52 정상, main 상수 공유 정상, `_ai_budget_seconds` 잔존 0.

## 자체 점검
- ☑ 동적 = clamp(300-경과-30, 0, 20) ☑ 소형→20 풀(041 보존) ☑ 대용량→자동 수축·끊김 불가 ☑ 남은시간 0→AI skip·결정론 정상·크래시 0 ☑ env 상한 override ☑ 서버 300·프런트 350 무변경 ☑ 분석 판정(filters/aggregator/result_builder) 무변경 ☑ 가용 범위 회귀 0.

## Next
- **Codex(Windows)**: 전체 pytest(기준선 331 + 신규 6)·tsc/lint/test/build·실 PDF로 `BOHUMFIT-058 ai budget` 로그(elapsed/avail/budget) 확인(소형=20 풀·대용량=수축) → 범위 파일 stage→commit→push. 커밋: `BOHUMFIT-058: 동적 AI 예산(남은시간 기반·최대 20초·floor 0 skip) — 041 Q2 주석 보존 + 끊김 재발 방지`.
- **Human**: 필요 시 안전마진(30s)·상한(20s) 운영 로그 보고 튜닝.
