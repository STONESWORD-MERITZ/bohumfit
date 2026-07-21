# BOHUMFIT-239 — 상품별 가입현황 매트릭스 페이지 감지 고정 해소

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: Codex (1차 검증 완료 — 2차 검증·커밋 대기)
Risk tier: 중위험 — 풀 하네스. git 쓰기 금지(커밋 Codex). 실 PDF 로컬 참조만·stage 금지.
Date: 2026-07-22

※ PII: 실 PDF는 `보장분석/비교분석표/` 로컬 전용. 코드·테스트·문서에 실명 0(합성 픽스처=홍길동).
※ ★파일명은 PII 보호를 위해 이하 "239 실사용 케이스"로만 기록.

## S0 — 진단 (★태스크 가정과 실제 근본 원인이 다름)

- 태스크 추정 원인(페이지 번호 하드코딩 / 다페이지 미누적)은 **실제 원인이 아니다**. 현행 classify_page는
  이미 헤더 문구("상품별 가입현황") 기반이고, parse_document는 매트릭스를 다페이지 누적한다(표준 4케이스
  A p6~8·B p7~10 정상 검출 실측).
- **진짜 원인**: 239 실사용 문서는 **'상품별 가입현황' 페이지가 아예 없는 KB 변형 문서**다. 대신 '전체
  보장현황' 페이지가 매트릭스 자리를 대체한다. classify_page가 이 헤더를 몰라 매트릭스 0 → 경고 + 담보
  가입금액 None(진단 value 미채움).
- **구조 실측**: '전체 보장현황'의 금액 열은 계약별 `(1)(2)` 인덱스가 없고 **집계 그룹**(생보/손보 등,
  헤더 count 행 "1 5 8 1"=계약수 그룹핑, 합계와 일치)이다. 즉 **담보별 합계(첫 셀)만 신뢰 가능**하고
계약별 by_company는 구성 불가. 교차검증: 진단 페이지 enrolled가 숫자로 존재하는 25개 기본담보는 overview 합계와 전부 정확 일치하고, 2개는 진단 원문 enrolled가 null이다.
- ★안전 핵심: 표준 4케이스는 **'전체 보장현황'(p3~4, 집계)과 '상품별 가입현황'(p6+, 계약별) 둘 다** 가진다.
  '전체 보장현황'을 무조건 매트릭스로 쓰면 4케이스가 이중검출로 깨진다 → **매트릭스 부재 시에만 fallback**.

## S1~S2 — 수정 (parser.py 감지·fallback + aggregator overview 분기)

- **parser.py**: `OVERVIEW_MARKER="전체 보장현황"`(파서 로컬 상수 — constants.ROLE_MARKERS 무변경) +
  classify_page에 `overview` 역할 추가. `parse_overview()` 신설(담보별 합계=첫 셀만 채집, by_company 비움,
  `overview:True` 플래그, 다페이지 누적). parse_document: `overview_pages` 수집 → **매트릭스가 없을 때만**
  `parse_overview`로 대체(`matrix_from_overview`), fallback 시 `_ensure_contracts...`·열-수 불일치 경고 skip,
  경고를 '찾지 못했습니다'(데이터 손실)에서 '전체 보장현황 합계로 대체·계약별 상세 없을 수 있음'(안내)으로 교체.
- **aggregator.py** (★스코프 확장 — 사유 아래): build_before가 summary를 by_company에서 재계산하므로,
  overview(by_company 빈) 담보는 summary가 None이 된다. `row.get("overview")` 전용 분기를 추가해
  summary=row["summary"]·enrolled=(summary 존재)로 산출. **표준 문서는 이 플래그가 없어 else 경로로 완전 무변경**.

### ★스코프 확장 1건 (사유 기록 — AGENTS.md "범위 확장은 handoff에 이유" 준수)

태스크 수정 범위는 parser.py로 명시됐으나, overview 합계를 화면·[최종] 진단에 실제로 흘리려면
build_before(aggregator.py)의 summary 산출이 overview 플래그를 인지해야 한다(parser만으론 불충분).
추가 분기는 overview 플래그 가드로 **기존 경로 0 영향**이며 234~238 로직 재변경 아님(additive).
대안(파서에서 by_company에 합성 키 주입)은 전후 비교(compare.py) 흐름을 깨트려 기각.

## S3 — 회귀·실 PDF 재실행

| 케이스 | 경고 | 월납 | enrolled 담보 | 상해사망 합계 | 판정 |
| --- | --- | --- | --- | --- | --- |
| A | (없음) | 2,835,744 | 37 | 512,610,000 | 불변 ✓ |
| B | (없음) | 681,312 | 26 | 210,000,000 | 불변 ✓ |
| C | (없음) | 183,621 | 26 | 10,000,000 | 불변 ✓ |
| D | (없음) | 763,089 | 35 | 383,080,000 | 불변 ✓ |
| 239 실사용 | 대체 안내(데이터 손실 경고 해소) | 4,675,189 | **37**(종전 0) | 332,100,000 | **신규 검출** ✓ |

- 239 케이스: 매트릭스 미검출 경고 → 안내성 대체 경고, overview 기본담보 27건과 detail 유래 추가담보를 포함해 [최종] 진단 value 37건 채움.
진단 페이지 enrolled가 숫자로 존재하는 25건은 overview 합계와 전부 일치하고, 2건은 진단 원문 enrolled가 null이다.
- 표준 4케이스: 코드 경로 자체가 동일(매트릭스 존재 → overview 분기 미진입). 회귀 0.

### 알려진 한계 (기록 — 2차 결정 항목 아님, 이 변형의 본질적 제약)

239 변형 문서는 '전체 보장현황'에 계약별 금액이 없어(집계 그룹만) **[전] 회사별 매트릭스의 계약별 셀과
전후 비교(해지 반영 재계산)는 담보 합계 수준까지만** 지원된다. 계약별 상세가 필요하면 '상품별 가입담보
상세'(detail) 페이지에서 유도하는 별도 작업 필요(범위 밖·후속 판단).

## 검증 체크리스트 (1차 — Code, 2026-07-22 결과)

- [x] backend pytest — **683 passed, 8 skipped**(기준선 677 + 신규 6; test_coverage_matrix_239). 기존 무손실.
- [x] tsc app/node · lint · npm test **77 passed**(프런트 무변경 — 파서가 기존 표시 경로로 흐름) · build 통과(청크 기록만).
- [x] 실 PDF 5건(4케이스+239) 재실행 — 위 표. 4케이스 매트릭스·금액·월납 전부 불변, 239 매트릭스 검출·경고 해소·합계 산출.
- [x] PII grep 0(실명 — 코드·테스트·239 문서). 보호영역 pipeline/ diff 0. diff 범위 = parser.py·aggregator.py·테스트 신규 + harness만. `git diff --check` 통과.
- [기록] 기존 파일 `backend/tests/test_drug_change_205.py:3`에 실명 잔존(205 태스크 산물·내 diff 밖) — 별건 잠재 PII, 후속 정리 후보.

## Stage 목록 (Codex용)

backend/coverage/parser.py, backend/coverage/aggregator.py(스코프 확장·사유 위), backend/tests/test_coverage_matrix_239.py(신규),
tasks/BOHUMFIT-239-*.md, handoff.md, locks.md — 실 PDF 제외

## 커밋 메시지 (Codex용)

fix(BOHUMFIT-239): 상품별 가입현황 매트릭스 페이지 감지 고정 해소 — 헤더 기반·다페이지 누적·전체보장현황 fallback
