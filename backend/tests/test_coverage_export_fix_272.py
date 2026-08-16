"""BOHUMFIT-272 — 보장분석 산출물 결함 수정.

★결함 A(최우선): 엑셀 종합비교 '후' 열에 '전' 값이 찍히던 참조 오류.
  실사용 동선의 [후] payload는 클라이언트가 `{...analysis.before}` 스프레드로 만들어
  `stage_totals`가 [전] 값 그대로 남는다(해지가 반영되는 것은 coverages뿐).
  254가 `_yn_flags`에 같은 처방을 했는데 `_stage_map`만 빠져 있었다.
★결함 C: 총납입 정의 2종(계약별 실납입 / 20년 환산)에 라벨을 붙여 서로 모순돼 보이지 않게 한다.
"""
import io
from pathlib import Path

import openpyxl
import pytest

from coverage.aggregator import build_before, build_final, compute_stage_totals
from coverage.compare import build_after_analysis
from coverage.export_excel import MONTHS_20Y, STAGE_ROWS, build_workbook_bytes, _stage_map

ROOT = Path(__file__).resolve().parents[2]
PDF_DIR = ROOT / "보장분석" / "비교분석표"
STANDARD_PDF = next(PDF_DIR.glob("*-INPUT.pdf"), None)


# ── 결함 A: 참조 소스 ──────────────────────────────────────────────────────
def test_stage_map_always_recomputes_from_coverages():
    """★payload의 `stage_totals`가 오염돼 있어도 coverages에서 재파생한다."""
    before_like = {
        # 해지가 반영된 [후] 담보 행
        "coverages": [
            {"kb_name": "암진단금", "summary": 10_000_000, "enrolled": True, "agg": "sum", "by_company": {}},
        ],
        # ★[전] 값이 그대로 남아 있는 상황(클라이언트 스프레드 재현)
        "stage_totals": {"뇌초기": 999_999_999},
    }
    stages = _stage_map(before_like)
    # BOHUMFIT-290: 종합 블록 키는 케스케이드 체인(뇌초기…)이다 — 구 "암" 키는 사라졌다.
    assert stages.get("뇌초기") != 999_999_999
    assert stages == compute_stage_totals(before_like["coverages"])


def test_stage_map_falls_back_when_no_coverages():
    """담보 행이 아예 없으면 기존 값이라도 쓴다(구 payload 하위호환)."""
    assert _stage_map({"coverages": [], "stage_totals": {"암": 123}}) == {"암": 123}
    assert _stage_map({}) == {}


@pytest.mark.skipif(
    STANDARD_PDF is None,
    reason="실 PDF 정본 없음(로컬 전용 · PII로 커밋 불가)",
)
def test_excel_stage_matches_pdf_source_when_before_differs_from_after():
    """★전≠후 케이스에서 엑셀 종합비교 == PDF가 쓰는 소스(재계산 값).

    수정 전에는 오염된 `stage_totals` 때문에 7행 전부 전=후로 찍혔다(실측 재현).
    """
    from coverage.parser import parse_document

    pdf = STANDARD_PDF
    assert pdf is not None
    raw = parse_document(pdf.read_bytes())
    before = build_before(raw, today="2026-07-29")
    final = build_final(before, raw.get("diagnosis") or {})
    analysis = {"before": before, "final": final, "warnings": []}

    ids = [c["idx"] for c in before["contract_list"]]
    result = build_after_analysis(
        analysis,
        {"existing": [{"contract_idx": i, "disposition": "cancel"} for i in ids[:3]], "proposals": []},
    )

    after_before = result["after"]["before"]
    expected = compute_stage_totals(after_before["coverages"])  # PDF가 쓰는 것과 같은 소스
    # 전≠후가 실제로 성립하는 시나리오여야 이 테스트가 의미를 갖는다.
    assert any(expected.get(k, 0) != before["stage_totals"].get(k, 0) for k in STAGE_ROWS)

    # ★클라이언트 스프레드 오염을 주입한 상태로 엑셀을 만든다.
    after_before["stage_totals"] = dict(before["stage_totals"])
    result["after"]["before"] = after_before

    ws = openpyxl.load_workbook(io.BytesIO(build_workbook_bytes(result)))["최종비교분석표"]
    rows = {
        ws.cell(row=r, column=8).value: r
        for r in range(1, ws.max_row + 1)
        if ws.cell(row=r, column=8).value in STAGE_ROWS
    }
    assert len(rows) == len(STAGE_ROWS)

    same_count = 0
    for key in STAGE_ROWS:
        row = rows[key]
        excel_before = ws.cell(row=row, column=9).value or 0
        excel_after = ws.cell(row=row, column=11).value or 0
        if key not in expected:
            # BOHUMFIT-290 최소 어댑터: 케스케이드에 대응 체인이 없는 구 키(암·심장말기)는 빈 셀(→ 0으로 읽힘).
            assert excel_after == 0 and excel_before == 0, key
            continue
        assert abs(excel_after - round(expected.get(key, 0) / 10_000)) <= 1, key
        if excel_before == excel_after:
            same_count += 1
    # 해지 3건이 단계 합계를 실제로 낮췄으므로 전=후인 행이 남아 있으면 안 된다.
    #   ★290: 대응 체인이 없어 "-"로 찍힌 구 키(암·심장말기) 2행은 전=후("-")가 정상이므로 제외한다.
    dash_rows = sum(1 for key in STAGE_ROWS if key not in expected)
    assert same_count == dash_rows


# ── 결함 C: 총납입 라벨 ────────────────────────────────────────────────────
def test_pdf_labels_total_payment_definition():
    """PDF 총납입 카드가 **무엇을 뜻하는지** 밝힌다(계약별 납입기간 반영)."""
    src = (ROOT / "backend" / "coverage" / "export_pdf.py").read_text(encoding="utf-8")
    assert src.count("총납입보험료(계약별 납입기간 반영)") == 2
    # 정의 없는 옛 라벨이 남아 있지 않다.
    assert '<div class="k">총납입보험료</div>' not in src
    assert '<div class="k">후 총납입</div>' not in src


def test_excel_keeps_20y_label_and_formula():
    """엑셀 20년 지표는 라벨·산식 그대로다(261 확정분 — 값 변경 금지)."""
    src = (ROOT / "backend" / "coverage" / "export_excel.py").read_text(encoding="utf-8")
    assert "20년 납부 시 총납입 차액" in src
    assert MONTHS_20Y == 240


def test_two_total_payment_concepts_are_distinguishable():
    """두 개념이 **서로 다른 라벨**을 갖는다 — 같은 이름으로 충돌하지 않는다."""
    excel = (ROOT / "backend" / "coverage" / "export_excel.py").read_text(encoding="utf-8")
    pdf = (ROOT / "backend" / "coverage" / "export_pdf.py").read_text(encoding="utf-8")
    assert "20년 납부 시 총납입 차액" in excel
    assert "총납입보험료(계약별 납입기간 반영)" in pdf
    # 20년 환산 라벨이 PDF에 잘못 들어가 있지 않다(개념 혼선 방지).
    assert "20년 납부 시" not in pdf


# ── 보호 영역 ──────────────────────────────────────────────────────────────
def test_272_does_not_touch_protected_modules():
    """★`pipeline/`·`filters.py`에 272 흔적이 없다."""
    assert "272" not in (ROOT / "backend" / "filters.py").read_text(encoding="utf-8")
    for path in (ROOT / "backend" / "pipeline").glob("*.py"):
        assert "BOHUMFIT-272" not in path.read_text(encoding="utf-8"), path.name


def test_form_schema_unchanged():
    """12 대분류·40행 스키마(FORM_ITEMS 35 + YN 5)는 그대로다 — 행 추가·삭제 금지."""
    from coverage.export_excel import FORM_ITEMS, YN_ROWS

    assert len(FORM_ITEMS) == 35
    assert len(YN_ROWS) == 5
    assert FORM_ITEMS[0] == "일반사망" and FORM_ITEMS[-1] == "깁스치료비"
