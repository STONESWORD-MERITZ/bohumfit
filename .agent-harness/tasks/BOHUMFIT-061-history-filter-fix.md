# BOHUMFIT-061 입원/통원 집계 수정 (060 진단 확정 위에서)

## Owner
Cowork(구현+회귀테스트, 샌드박스) → Codex(Windows 검증·커밋·푸시). 마운트 git 금지·원본 PDF 커밋 금지.

## 변경 요지
- 입원 식별 단위 = **(KCD 3자리, 입원개시일, 요양기관)**. 같은날 다른 병원 = 별개 admission. **0일 입원 무시**.
- 상병코드 정규화: 양방(A)/한방(B) 접두 제거 + **KCD 3자리 그룹핑**(M54·M79 등 3자리 분리 유지). 약국($) 통원 제외.
- `_keep_basic_general_row`: 일반의 비M54 drop 제거 → **유효 상병코드면 모두 보존**(공란/$만 제외).
- 창/경계·결정론 불변.

## 구현
- `helpers.py`: `disclosure_group_code` → KCD3(`^[A-Z]\d{2}`), 공란/$ → "". `_keep_basic_general_row` → `bool(normalize_code(code))`.
- `disease_aggregator.py`: `new_disease` +`inpatient_admissions:set()`. basic·nhis 입원 블록 → `m_days>0`일 때만 입원 인정, `inpatient_admissions.add((개시일,_norm_provider_name(기관)))`, 0일 무시.
- `filters.py`: `_adm_in_range(admissions, since)` 추가, 6개 `inpatient_count=len(inp_*)` → `_adm_in_range(...)`(d3m/d10y/d5y).

## 회귀테스트 (익명 합성)
- `test_history_filter_fix.py`(신규): 입원2건(같은날 다른병원)·0일분리·M75 통원7회·L02 9회(약국 제외)·일반의 보존·정규화/KCD3.
- `test_bug012_q2_q3.py`: KCD3 반영 기대값 N760→N76(입력 AN760 유지).

## 검증
- backend pytest(샌드박스 /tmp 사본): 관련 86 passed·6 skipped. frontend tsc/lint/build은 backend 무관(영향 없음).
- Codex(Windows): `cd backend && python -m pytest -q` 전체 + tsc app/node·lint·build.

## 산출
- handoff: 변경·검증·전후 3케이스 수치. Next: Codex.
