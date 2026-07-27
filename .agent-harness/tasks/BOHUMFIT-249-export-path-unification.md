# BOHUMFIT-249 — 엑셀 다운로드 경로 통일(비분양식 정본) + 레거시 경로 [후] 이월 결함

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: Codex (2차 검증 통과·커밋/배포 확인)
Risk tier: 고위험(고객 산출물 값 결함) — 풀 하네스. git 쓰기 금지(커밋 Codex). 실 PDF·엑셀 로컬 참조만·stage 금지.
Date: 2026-07-27

## 배경 (2026-07-26 Human 실물 검수)
프로덕션 다운로드 엑셀(E 케이스 — 실명 마스킹)이 ① 구 5시트 구조 ② overview [후] 보장금액 전부 0원
(월납 이월은 정상). 화면 payload는 54행·1,542,990,000 보존 — 화면↔엑셀 불일치(211 위반).

## 진행 기록 (Claude Code · 2026-07-27)

### S0 — 다운로드 동선·[후] 산출 경로 전수 실측

**동선 지도(HEAD 9ee78b5)**:
- 프런트 다운로드 버튼(CoverageRemodel `exportFile`) → `POST /coverage/export/{excel|pdf}`
  (단일 경로 — src grep 유일) → main.py `coverage_export_excel/pdf` →
  `export_excel.build_workbook_bytes`(248 신규 3시트) / `export_pdf.generate_coverage_pdf`.
- **★레거시 5시트 exporter는 HEAD에 존재하지 않는다**: 구 시트명 문자열("전후 특약별"·
  "② 전 계약"·"최종 보장진단" 등) 코드 grep **0건**(테스트 포함 제거 완료 — 248 P2 전면
  재작성 시 삭제). xlsx 생성 모듈도 export_excel.py 하나뿐. → **A항(레거시 퇴역)은 248에서
  기수행** — 이번엔 "호출처 0 + 생성 불가"를 테스트로 고정한다.
- **Human 실물 5시트의 소거법 판정**: HEAD 코드로는 5시트 생성이 불가능 → 다운로드 시점의
  프로덕션 백엔드(Railway)가 248 반영 전 상태(구 exporter)였다는 것이 유일한 정합 설명
  (구 5시트 + 신 체계 라벨 = 246·247 시점 코드와 정확히 일치). **Codex 배포 확인·재배포가
  필수 조치**(Next ①에 명시).

**[후] 산출 경로 3중 복제 실측 — ★근본 결함 발견**:
| 경로 | 소비처 | 246 overview 보정 | '?' 키 이월 |
| --- | --- | --- | --- |
| `consulting.apply_consulting_plan` | 백엔드 [후](190 계열) | ✅(246 회송 보정) | ✅ |
| `coverageAfterDisplayCache.buildAfterResult` | 화면(211 캐시) | ✅(247 패리티) | ✅ |
| **`compare.build_after_analysis`** | **서버 권위 [후]**(consulting.build_after_result 경유 — 프로덕션 구 코드의 export comparison 원천) | **❌ 미적용** | **❌** |

- `compare.build_after_analysis`의 after_coverages 재집계가 `contract_id in kept_contract_ids`
  필터만 적용 — overview 행(by_company={})은 summary None으로 소실, '?' 키도 유실.
  **Human이 본 [후] 0원의 코드 원인**(구 배포에서 이 경로 산출물이 ④ 시트에 렌더됨).
  현 HEAD에서도 이 경로를 쓰는 소비처(빈 comparison payload로 export 호출·백엔드 after
  계산)가 있으므로 실재 결함이다.

**★재발 방지 원칙(패킷 지시 — 경위 기록)**: 248 P2 검증은 `build_workbook_bytes` 직접
호출이었고 UI 동선(엔드포인트 POST 경유)·프로덕션 배포 반영 확인이 누락됐다.
→ **"산출물 검증은 사용자 동선 기준(엔드포인트 경유) + 배포 반영 확인까지"를 본 태스크
이후 표준으로 명시**(이번 검증·신규 테스트가 그 기준으로 작성됨).

### 구현 (B — [후] 이월 단일 소스 통합)

- **`aggregator.carry_coverage_row` 신설(정본)**: overview 합계 이월(+신규 제안 가산) ·
  계약 미상 키('?') 이월 · keep/cancel 필터 — 246 회송 보정 규칙의 단일 구현.
  null 셀은 유지(클라이언트 캐시·종전 compare 표기와 동일 — 211 패리티는 셀 단위 비교.
  최초 구현에서 null 제거로 211 패리티 1건 실패 → 즉시 정정). `OVERVIEW_CANCEL_WARNING`
  문구 상수화(3경로 동일 문구 보장).
- **`consulting.apply_consulting_plan`**: 인라인 이월 로직 제거 → 정본 헬퍼 호출로 교체.
- **`compare.build_after_analysis`(★결함 경로)**: 재집계 루프를 정본 헬퍼로 교체 —
  overview [후] 0원 소실·'?' 유실 해소 + overview×해지 경고 추가(consulting과 동기).
- 클라이언트 미러(buildAfterResult)는 247 보정본 그대로 — 무수정(주석으로 동기 의무 명시).
- **A항**: 레거시 exporter는 248에서 이미 삭제(호출처 0 grep) — 추가 코드 조치 없음.
  재발 방지는 신설 엔드포인트 테스트(구 5시트 생성 불가·3시트 고정)로 담보.

### 검증 (1차 — Code · 2026-07-27)

- [x] backend pytest — **710 passed, 8 skipped**(707 + 신규 3: 엔드포인트 3시트/overview [후]
      보존·표준 전=후·서버 [후] overview/'?' 회귀). 211 패리티 포함 기존 무손실.
- [x] tsc app/node · lint · npm test **89**(프런트 무수정 — build:verify는 로컬 무효·소스 게이트 기준)
- [x] ★엔드포인트 경유(UI 동선 그대로 — TestClient POST /coverage/export/excel) 실 PDF 5건:
      3시트 구조 5/5 · 40행 [전]/[후] 전수 대조 **차이 0** · 표준 4건 전=후 ·
      **E [후] 총합 1,542,990,000 보존(결함 해소 증명)** · 월납 4,675,189 · B 15계약 열 전개 ·
      PDF 경로 값 대조(HTML — 렌더러는 Windows 정책 대체 검증) 5/5.
- [x] 레거시 exporter 호출처 0(구 시트명 문자열 코드 grep 0 — 248 기삭제 확인)
- [x] PII 0(문서 실명 마스킹 정정 포함) · pipeline/supabase diff 0 ·
      diff 범위 = aggregator·compare·consulting·신규 테스트 + harness만.

### 검증 (2차 — Codex Windows · 2026-07-27)

- [x] backend pytest **710 passed, 8 skipped** 재현. 211 패리티+249 표적 테스트는 **4 passed**.
- [x] tsc app/node · lint · npm test **89 passed**. 로컬 build는 참고값 343,225 B이며
      `build:verify`가 필수 문자열 누락까지 검출해 의도대로 exit 1(합격 근거로 사용하지 않음).
- [x] 정적 검사: `carry_coverage_row`를 consulting·compare 양쪽이 호출하고 서버 [후] 이월
      복제 잔존 0, compare의 overview×해지 경고는 공용 상수로 consulting과 동일 문구.
- [x] ★실 PDF 5건을 메모리 분석 후 TestClient `POST /coverage/export/{excel|pdf}`로 재현:
      엑셀 3시트 5/5 · 40행/계약 셀 차이 0 · 표준 4건 전=후 · B 15계약 열 전개 ·
      E [후] **1,542,990,000원**·월납 **4,675,189원** 보존. PDF도 5/5 **200**,
      유효 PDF(5~6쪽)·월납 및 전 담보행 HTML 값 대조 통과.
- [x] 총액 대사 5건 0·월납/납입완료 제외 부값·238 estimated 불변. 실 PDF 5건에서 읽은
      실제 고객명과 변경 7파일의 일치 **0**, pipeline/supabase/src/package diff 0,
      실 PDF·엑셀·부산물 tracked 0, `git diff --check` 통과.

## Next (handoff 명시)
① Codex — 2차 검증(엔드포인트 경유 5건 재현) → 커밋·push → **배포 스모크 + 프로덕션 실물
   다운로드 확인**(★S0 판정상 Human 실물 5시트는 배포 스테일 — Railway 반영 확인이 필수 조치)
② Human — 프로덕션에서 E 케이스 재다운로드 → 비분양식 3시트 + [후] 값 보존 확인
③ Chat — 사양 결정 4건·카탈로그 결정지 대기

## 수정 금지
backend/pipeline/ 무접촉·246 집계 원칙 변경 금지·실 PDF stage 금지(픽스처 익명)

## Stage 목록 (Codex용)
수정 파일, 테스트, tasks/BOHUMFIT-249-*.md, handoff.md, locks.md

## 커밋 메시지 (Codex용 · 사용자 최종 지정)
fix(BOHUMFIT-249): 후 산출 단일 소스 통일(carry_coverage_row) — 서버 경로 246 보정 누락 해소
