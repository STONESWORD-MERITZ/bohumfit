# BOHUMFIT-059 세부진료 수술 판정 오탐 제거 (검사·처치·주사 비수술 행위 제외)

## Owner
- Cowork (PHASE1 진단 + PHASE2 구현 + 가용 검증) → Codex (Windows 전체 pytest·실 PDF 재현·커밋·푸시) → Human(필요 시 키워드 추가)

## 증상 (이민규 병력, 운영 화면)
- K21 식도염 → 실제 복부초음파(검사)인데 "수술 1건" 오탐.
- L90 여드름 흉터 → 실제 병변내주입요법(염증주사)인데 "수술 1건" 오탐.
- 둘 다 진짜 수술 아님. 비수술 행위가 수술 매칭에 걸림. 목표: 오탐↓·누락 0.

## PHASE 1 진단 (읽기)
### 1-A 현재 수술 판정 기준 (세부진료 detail)
- `disease_aggregator.build_disease_stats` detail 분기(L357~370)에 **두 경로**:
  - **경로 A — 컬럼 기반(L361/364)**: `is_surg_by_column = bool(surg_col and surg_col.strip() and !="0")` — `처치및수술` 컬럼이 비어있지 않으면 **행위 종류 무관 수술 확정**. 검사/처치/주사 필터 **없음** → **복부초음파 오탐의 주범**.
  - **경로 B — 키워드 기반(L362/368)**: `_is_detail_surgery_match(surg_target)` = `_is_surgery_match OR _DETAIL_CONFIRMED_SURGERY_KEYWORDS OR nhis_surg_keywords`.
- `_is_surgery_match`(helpers L221) positive `surg_keywords`에 **"주입"** 포함 → **"병변내주입요법-25cm²미만"이 "주입"에 매칭** → negative 없음 → 수술. **L90 오탐의 주범**.
- 기존 제외는 `is_non_surgery_excluded`(062, exact 코드명 4건) — 키워드 행위 오탐은 못 막음.
### 1-B 행위명 분류 (실 PDF는 비번 PII로 미오픈 — 코드+증상 행위명 기반)
- 진짜 수술: 비용적출술(적출)·창상봉합술(봉합)·내시경하종양수술(수술)·점막절제술(절제) — 강수술 신호 보유.
- 검사: 복부초음파·위내시경검사·CT·MRI·조직검사·생검 — 강수술 신호 없음.
- 처치: 드레싱·소독·물리치료. 주사/주입: 병변내주입요법·관절강내주사·수액제주입로.
- **오탐 목록**: 복부초음파(검사·경로A), 병변내주입요법(주사·경로A+B). 위내시경검사 류도 경로A 동일 위험.
### 1-C 제외 설계 (블랙리스트 키워드 + 강수술 화이트리스트 우선)
- 신규 `is_non_surgery_action(name)`: 검사·처치·주사 키워드 매칭 시 True(비수술), **단 강수술 신호(절제·적출·봉합·수술 등) 있으면 False**(누락 0). 두 경로 모두에 가드.
- 대조군 충돌 검증: 비용적출술(적출)·창상봉합술(봉합)·점막절제술(절제) → 강수술 신호로 **제외 안 됨**(정탐 유지). 내시경적용종제거술(검사 없음·내시경 단독 미매칭) → 미제외(수술 유지).

## PHASE 2 구현
- `backend/pipeline/surgery_exclusions.py`(062 단일 소스 확장): `_STRONG_SURGERY_KEYWORDS`(절제·적출·봉합·수술·성형·정복·발치·색전·용종절제 등)·`_NON_SURGERY_ACTION_KEYWORDS`(검사·초음파·촬영·생검·드레싱·소독·물리치료·병변내주입·주입요법·관절강내주사·근육내/정맥내/피하주사 등)·`is_non_surgery_action()` 신설. 강수술 신호 우선(있으면 비수술 아님).
- `backend/pipeline/disease_aggregator.py`:
  - import에 `is_non_surgery_action` 추가.
  - `_is_detail_surgery_match`(L165): `is_non_surgery_action(text)` 시 False(경로 B 가드).
  - detail 분기(L361): `is_surg_by_column`에 `and not (is_non_surgery_action(surg_target) or is_non_surgery_action(surg_col))` 가드(경로 A). 컬럼·키워드 양 경로 일관 제외.
- 교차참조 SURGERY_COST_THRESHOLD 경로·confirmed-column 경로는 `_is_detail_surgery_match`/`_is_surg_by_column`을 소비하므로 가드를 **자동 상속**. `_is_surgery_match`(basic/nhis)·keywords.json·filters는 **무변경**(오탐은 detail 한정, 회귀면 최소).

## PHASE 3 검증
- 신규 `tests/test_nonsurgery_action_059.py`(7): ①복부초음파→수술0·통원유지 ②병변내주입요법→수술0 ③비용적출술→수술유지 ④창상봉합술→수술유지 ⑤검사 detail 제외돼도 통원2 유지 ⑥단위(is_non_surgery_action/_is_detail_surgery_match 비수술 True·수술 False, 강수술 우선) ⑦공백 변형 견고.
- /tmp(마운트 복구본: pdf_parser tail 재구성·surgery_exclusions 실파일 동기): **059 7/7 + 수술/집계/필터 광범위 222 passed·6 skipped**. **회귀 0**(유일 실패 `test_q2_ai_gate`는 corrupt analyzer.py 소스 grep — 059 무관 환경결함, Windows 정상).
- ⚠ 실 PDF는 **비밀번호(PII 생년월일) 미보유로 미오픈** → K21/L90 전후 1→0·최유미 대조군은 합성 픽스처로 재현(행위명 동일). Codex가 실 PDF(생년월일)로 재현 권위.

## 자체 점검
- ☑ 수술 판정 기준 전수(경로 A 컬럼·경로 B 키워드) ☑ 행위명 분류·오탐 목록 ☑ K21·L90 수술 미판정(합성) ☑ 비용적출술·창상봉합술 수술 유지 ☑ 강수술 신호 충돌 0 ☑ 통원/투약/입원 무영향 ☑ 가용 pytest 회귀 0.

## Next
- **Codex(Windows)**: 전체 pytest(기준선 331 + 신규 7)·tsc/lint/build·실 PDF(이민규 세부진료+자동차, 생년월일) 재현 — K21·L90 수술 1→0, 진짜 수술 유지 확인 → 범위 파일 stage→commit→push. 커밋: `BOHUMFIT-059: 세부진료 수술 오탐 제거(검사·처치·주사 비수술 행위 제외) — 컬럼·키워드 양경로 가드`.
- **Human**: 운영 화면에서 K21/L90 수술 0건 확인. 추가 오탐 행위명 발견 시 `_NON_SURGERY_ACTION_KEYWORDS` 보강.
