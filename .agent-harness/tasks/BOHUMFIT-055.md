# BOHUMFIT-055 대용량 PDF 파싱 병목 진단 + 처리시간 개선
## Owner
- Cowork (PHASE1 진단 + PHASE2 구현) → Codex (Windows 전체 검증·실 부하 재측정·커밋) → Human (Railway 플랜·워커수 승인)

## 전제
- 분석 카운트·판정 로직(filters/aggregator/result_builder) 무변경. AI 5초 예산 무변경(052 동기경로 유지).
- 변경은 "파싱 처리 인프라"(동시성)만.

## PHASE 1 — 병목 정밀 진단 (읽기)
- **구간별 계측(실 PDF)**: 기본진료 20p → 총 4.8s 중 `extract_text` **4.5s(95%)** · `extract_tables` 0.2s(5%) · row 0.0s. 처방조제 70p → 총 17.5s 중 text **16.7s(95%)** · tables 0.7s(4%). → **병목 = page.extract_text()**(페이지별 ftype 판정용), tables 아님.
- **CPU vs IO**: pdfminer 텍스트 레이아웃 분석 = 순수 파이썬 **CPU 바운드**(네트워크/디스크 대기 없음, 1회 파일 read만). 코어 = **2 vCPU**(sandbox=Railway 가정).
- **동시성**: `_parse_all_pdfs` 순차(for). 파일 간 독립(공유상태 없음, 결과 병합 순서 보존 가능). → **CPU 바운드 + 파일 독립 = 파일 단위 프로세스 병렬 적합**.
- **접근 선택**: PHASE1 결과는 (a) 프로세스 병렬. **단 실측 반전**: ProcessPool은 요청마다 프로세스 spawn + 모듈 재import 고정 오버헤드(~수 초)가 있어 **소형 2파일에서 0.53×(오히려 느림)**. 병렬은 파싱시간 ≫ spawn 오버헤드(=대용량 다파일)일 때만 이득. → (a) + **워크로드 게이트**로 구현.

## PHASE 2 — 개선 구현 (analyzer.py only)
- `_parse_all_pdfs` 에 **파일 단위 프로세스 병렬 경로** 추가(순차 기본 유지):
  - `_ParseInput`(picklable bytes+name) / `_parse_one_worker`(워커서 parse_single_pdf 재import) / `_container_mem_bytes`(cgroup v2/v1) / `_parse_workers(n_files, total_bytes)` / `_log_parsed`.
  - **자동 병렬(2) 조건(모두)**: cpu≥2 AND cgroup 메모리 ≥ ~1.4GB AND 총 업로드 ≥ `_MIN_PARALLEL_BYTES`(3MB). 그 외 **순차**(소규모 무회귀·메모리 안전).
  - `BOHUMFIT_PARSE_WORKERS` env 명시 override(게이트 무시; 0/1=순차, 2~=병렬) — 운영 Railway 플랜·실측에 맞춰 강제.
  - **순서 보존 병합**(as_completed → 인덱스 배열 → 파일 순서대로 extend) → 결정성·분석 결과 불변.
  - **fail-loud**: 워커 예외 시 해당 파일만 빈 결과+ERROR 로깅+parse_errors(047 일관). 순차 경로도 동일 유지.
- 회귀 `tests/test_parse_workers.py`(8): env override(1/0/bad/2/8·cpu·파일수 캡)·단일파일→순차·저메모리→순차·대용량+메모리→병렬·**소형 대용량미만→순차**·_ParseInput picklable.

## 검증
- **PHASE1 수치**: 위 구간 계측(95% text) 실측. (104p 단일 27s/250MB·70p 22s/239MB는 047 권위 — 이번 세션 샌드박스 부하로 대용량 재측정 타임아웃.)
- **PHASE2 동등성(실측)**: 동일 20p ×2, 순차 recs=[215,215] vs 병렬(2) recs=[215,215] — **레코드·순서 동일(동등성 ✓)**. speedup 0.53×(소형 → spawn 오버헤드 지배) → **워크로드 게이트로 소형은 순차 유지**(무회귀). 대용량(10×104p≈270s)에서는 2코어 병렬로 ~145s 추정(타임아웃 300s 내).
- **로직 검증(standalone, 동일 코드)**: _parse_workers(env/메모리/워크로드 게이트/캡) + _ParseInput picklable 통과.
- ⚠ **마운트 view 심각 손상(이번 세션)**: analyzer.py bash-view 가 파일도구(Read/Grep)와 불일치(stale)·report_pdf 절단 → /tmp 전체 pytest 불가. **analyzer.py 편집은 Grep 도구로 실파일 확인(_ParseInput·_parse_workers·ProcessPool·_total_bytes 12참조)**. 비-analyzer 회귀는 248 passed(stale/stub 아티팩트 4건 제외). **전체 pytest(test_parse_workers·integration)·실 10대용량 타이밍은 Codex/Windows 권위.**
- 자체 점검: ☑PHASE1 구간 분해(text 95%, CPU) ☑접근 근거(a+게이트, spawn 오버헤드) ☑PHASE2 구현+동등성(215==215 순서보존)+소형 무회귀 ☑메모리 가드(워커×1파일, ≥1.4GB만) ☑분석 로직 무변경 ☑AI 5초 무변경 ☑047/054 경고 일관(fail-loud).

## 작업 범위
- `analyzer.py`(_parse_all_pdfs 병렬 경로·워커 게이트 — 처리 인프라만)·신규 `tests/test_parse_workers.py`. filters/aggregator/result_builder/pdf_parser 파싱 로직·main.py 무변경.

## 미채택·후속
- extract_text(95%) 직접 단축(layout=False 등)은 ftype 판정→분석 변경 위험으로 **미채택**(분석 무변경 원칙).
- PHASE 2-C(페이지 수 사전 가드/타임아웃 상향)는 병렬이 대용량 타임아웃을 해소하므로 보류 — 저메모리(순차) 환경 대용량 대비 보완책으로 Human 검토 가능.

## Next
- **Codex(Windows)**: 전체 pytest(기준선 317 + 신규 8)·tsc/lint/build → 커밋·푸시. 커밋: `BOHUMFIT-055: 대용량 파싱 파일단위 프로세스 병렬(워크로드·메모리 게이트, 순서보존·fail-loud)`. **실 10대용량 PDF 순차 vs 병렬 처리시간 재측정**.
- **Human**: Railway 플랜 메모리 확인 → `BOHUMFIT_PARSE_WORKERS` 설정(≥1GB·다코어면 2). 운영 배포 후 큰 파일 10개 실측.
