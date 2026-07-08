# BOHUMFIT-183 — 대분류 재편 (순서·간병 이동·치매 제외·골절→상해)

Owner flow: Claude Chat -> Claude Cowork -> Codex
Current owner: **Codex (구현) — ⚠마운트 손상(constants.py null 1845B)으로 Cowork 코드 편집 불가, 아래 명세대로 Windows 원본에 구현**

## ⚠환경 블로커
`constants.py` 마운트 뷰가 byte 5262부터 null 패딩 손상(EXTRA_PATTERNS/classify_extra 영역 포함) → Cowork가 편집·import·테스트 불가. 182와 동일 사유로 Codex가 Windows 원본에 구현. (aggregator/export_excel/export_pdf/CoverageRemodel은 마운트 정상이나, constants import 실패로 통합 테스트 불가 → Codex 일괄.)

## 확정 사양 (Human)
**새 대분류 순서(12 + 기타):**
사망 → 후유장해 → 암 → 뇌/심장(통합 유지) → 수술 → 입원일당 → 실손의료비 → 상해 → 운전자 → 배상책임 → 화재 → 기타

**변경1 — 간병 이동:** `간병인/간호간병상해일당`·`간병인/간호간병질병일당` → group12 **"입원일당"** 합류. (기존 `상해입원일당`·`질병입원일당`의 group12 "입원" → **"입원일당"으로 개명**하여 4개 함께.)

**변경2 — 치매 제외(완전):** `장기요양간병비`·`경증치매진단` → 권장/진단·[전]/[최종]·rollup **모든 렌더에서 완전 제외**. (KB_COVERAGES에 유지하되 group12 sentinel `"제외"`로 표기 → aggregator가 `group12=="제외"`를 coverages·rollup에서 필터. STANDARD_COUNT=37 유지하여 match_coverage/파서 회귀 최소화. Human 재확인 포인트 — Notes 명시.)

**변경3 — 골절→상해:** `골절` 대분류를 **"상해"**로 개편. `골절진단비`·`보철치료비` group12 → "상해". + **화상**(현행 기타 EXTRA "화상" 라벨) → group "상해" 수용. **유지(기타)**: N대수술비·상급/종합병원 일당·양성종양·폴립·통원일당.

**유지:** 뇌/심장 현행 통합 표시.

## S0 실사 (Cowork, 현행 constants 파악)
현행 GROUP12 = (사망, 후유장해, 간병/치매, 암, 뇌/심장, 실손의료비, 수술, 입원, 운전자, 골절, 배상책임, 화재). KB_COVERAGES 37행 group12 매핑 확인함(간병4=간병/치매, 입원일당2=입원, 골절2=골절, 화재벌금=화재). EXTRA(기타) 라벨: 상급/종합병원 일당·상급/종합병원 수술비·N대수술비·화상·양성종양·폴립·통원일당.

## 구현 지시 (Codex)
1. `constants.py`
   - `GROUP12` → 새 순서 11개 비-기타(사망·후유장해·암·뇌/심장·수술·입원일당·실손의료비·상해·운전자·배상책임·화재) + `GROUP13 = GROUP12 + (기타,)`. ("간병/치매"·"골절"·"입원" 제거).
   - `KB_COVERAGES` group12 갱신: 간병4 → "입원일당" / 상해입원일당·질병입원일당 → "입원일당" / 골절진단비·보철치료비 → "상해" / 장기요양간병비·경증치매진단 → "제외".
   - EXTRA 라벨→group 매핑 신설 `EXTRA_LABEL_GROUP = {"화상":"상해", 그 외 라벨:"기타"}` (aggregator에서 참조). "화상"만 상해, 나머지 기타 유지.
   - ★손상 라인 정리: 현행 EXTRA_PATTERNS에 mojibake 중복 패턴(`\d+企.*呪綬`)이 마운트 뷰에 보임 — Windows 원본 확인 후 유효 중복이면 제거(무해 dead 패턴이나 정리 권장).
2. `aggregator.py`
   - coverages 생성 시 `group12=="제외"` 담보 **필터(제외)** — [전]/[최종] 모두.
   - 기타(EXTRA) coverage의 group12 = `EXTRA_LABEL_GROUP.get(label,"기타")` (화상→상해).
   - rollup/정렬 = 새 GROUP13 순서.
3. `export_excel.py`·`export_pdf.py`·`CoverageRemodel.tsx` — 대분류 정렬 배열을 새 GROUP13 순서로 교체(현행 GROUP_ORDER 상수). 치매 제외 반영(자동 — 데이터에서 빠짐).
4. 179/179b **group-assertion 테스트 갱신 필요**: `test_mapping_37_12_rep`의 GROUP12 내용·간병/치매 관련 단언 → 새 그룹 기준으로 수정. **담보 단위 집계값 단언(573,227·181,984,128·상해사망 5.5억·일반암 1억·입원일당 6만 등)은 불변.**

## S6 — 테스트 (backend/tests/test_coverage_group_183.py, 익명·합성)
- 대분류 순서 == 새 GROUP13. 간병일당2가 "입원일당" 그룹. 치매2(장기요양·경증치매)가 coverages·rollup·[전]/[최종] **미표시**. 골절2+화상이 "상해" 그룹. 담보 집계값 불변(회귀).

## 수정 금지
- parser.py 계약 파싱(→184·182) · 담보 단위 집계값(그룹핑/순서/치매표시만).

## 커밋 (Codex)
feat(BOHUMFIT-183): 대분류 재편(순서·간병 이동·치매 제외·골절→상해)
