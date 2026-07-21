# BOHUMFIT-238 — 종수술비 5종 기준 → 1~5종 환산 세팅 (룩업표 기반)

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: Codex (1차 검증 완료 — 2차 검증·커밋 대기)
Risk tier: 고위험(DB 시딩 동반) — 풀 하네스. git 쓰기 금지(커밋 Codex), 프로덕션 DB 연결·실행 0(SQL 산출만), 실 PDF 로컬 참조만.
Date: 2026-07-21

※ PII: 고객명 마스킹(A=임*효, B=이*숙, C=이*연, D=지*주). 실 PDF는 `보장분석/` 로컬 전용.

## S0 — 실측·설계 확정

- 원문 2형(237-F 재사용): **종별 분리형**(D — "…_1종"~"_5종"/"(1종," 각 행 금액) vs **단일 합산형**(A 라이나 — "질병1~5종수술(수술당1회한)(5종수술) 1,000만").
- 구분 기준 확정: 담보명에 종별 마커 `_[1-5]종` 또는 `([1-5]종`+`,`/`)` 존재 → 종별 명시(환산 미적용·원문 우선). "1~5종" 범위 표기·"(5종수술)" 기준 표기는 마커 아님(실측 검증).
- 룩업 위치: **DB 테이블 `jong_surgery_conversion`**(Human 수정 가능) + **코드 내장 기본표 fallback**(`coverage/jong_surgery.py DEFAULT_JONG_TABLE` — 값 동일, 테스트가 SQL 시딩표와 일치 고정). 배포↔SQL 순서 안전망(237-A식): 테이블 미존재·조회 실패·게이트 비활성 시 내장표 사용, 프로세스 수명 캐시.

## S1 — SQL 산출

`supabase/manual/BOHUMFIT-238-01-jong-surgery-table.sql`: 첫 줄 `set bohumfit.human_approved='BOHUMFIT-238'` 실행문(232 표준),
단일 트랜잭션·idempotent(create if not exists + upsert 시딩 — Human이 표 수정 시 재실행 가능)·가드.
테이블 생성 + **확정표 10행 시딩**(만원 단위) + RLS(전체 SELECT 정책) + anon/authenticated **SELECT만** grant(232 봉인 정합 — 공개 읽기 허용 테이블). 실행 전/후 확인쿼리·롤백(drop — 내장표 fallback으로 무장애) 주석.

## S2 — 파서/집계

- `coverage/jong_surgery.py` 신설: DEFAULT_JONG_TABLE(확정표)·`lookup_jong_tiers`(이하 최대값 룩업 — 750만→700행·1,500만→1,000행 / 100만 미만→None)·`has_explicit_tier`·라벨 헬퍼.
- parse_detail_pages: 종수술 라인 중 마커 없음 → 환산 적용, `종수술비(k종·표준환산)` 5개 버킷 세팅(entry `estimated: True`). 100만 미만 → 세팅 안 함·`종수술비(표 외)` 버킷으로 원액 유지. 마커 있음 → 기존 통합 합산(값 변경 0).
- main.py `_get_jong_conversion_table()`: service role 조회·캐시·실패 시 None(fallback). `/coverage/analyze`에서 주입.
- aggregator: `estimated` 구분 필드를 coverage 행에 전달(표시명에도 "표준환산" 고정 — 렌더러 무수정 반영).

## S3 — 표시/내보내기

화면(④·⑤)·엑셀([전] 시트)·PDF(⑤)에 환산 행 존재 시 문구 병기:
"※ 종수술비 종별 금액은 표준 환산 기준으로 산출되어 상품별 실제와 상이할 수 있습니다."

## 실 PDF 4건 재실행

| 케이스 | monthly/active (불변) | 종수술 |
| --- | --- | --- |
| A | 2,835,744 / 2,282,564 (KB 일치 유지) | **환산 적용** — 5종 기준 2건(질병·상해 각 1,000만) → 1종 40만·2종 100만·3종 200만·4종 1,000만·5종 2,000만 (5종 합 = 종전 통합값 2,000만 보존) |
| B | 681,312 / 681,312 | 해당 없음 |
| C | 183,621 / 183,621 | 해당 없음 |
| D | 763,089 / 495,389 | **미적용(원문 우선)** — 종별 분리형, 통합 3,410만 불변 |

## 검증 체크리스트 (1차 — Code, 2026-07-21 결과)

- [x] SQL 정적 검사: 첫 줄 set·가드·$$ 짝·괄호 균형·commit 종결·**10행 시딩**·SELECT-only grant·secret 0·migrations 미포함
- [x] backend pytest — **677 passed, 8 skipped**(기준선 657 + 신규 20). 파급 2건 갱신(234 종수술 assert→환산 동작·usage lambda 시그니처 — 사유 주석)
- [x] tsc app/node · lint · npm test **77 passed** · build 통과(청크 기록만)
- [x] fallback 내장표 = SQL 시딩표 값 일치 테스트(`test_fallback_matches_sql_seed`) 통과
- [x] 실 PDF 4건 — 기존 수치 전부 불변 + A 환산 적용·D 원문 우선 확인(위 표)
- [x] PII grep 0, diff 범위 = coverage(신규 1+수정 4)·main.py·export 2종·CoverageRemodel·supabase/manual 신규·테스트(신규 1+갱신 2) + harness만

## Stage 목록 (Codex용)

backend/coverage/{jong_surgery.py(신규), parser.py, service.py, aggregator.py, export_excel.py, export_pdf.py},
backend/main.py, backend/tests/{test_coverage_jong_238.py(신규), test_coverage_parser_234.py, test_usage_middleware.py},
src/pages/CoverageRemodel.tsx, supabase/manual/BOHUMFIT-238-01-jong-surgery-table.sql,
tasks/BOHUMFIT-238-*.md, handoff.md, locks.md — 실 PDF 제외

## 커밋 메시지 (Codex용)

feat(BOHUMFIT-238): 종수술비 5종 기준 1~5종 표준 환산 세팅 (룩업표 시딩 + fallback)
