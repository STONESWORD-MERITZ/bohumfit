# -*- coding: utf-8 -*-
"""BOHUMFIT-296 — 비고 정규 행 이관 · N대수술비 신설 49→52행 · 2열 라벨 정리 계약.

★고정하는 계약 (Human 확정)
  ① 스키마 52행(49 + N대수술비 최대 보상금액·3대비급여실손·교통사고처리지원금(6주미만)) · 대분류 11 불변
  ② N대수술비: 정규 행(수 술)으로 이관 · N값 무관 · 여러 건이면 **최대 보상금액(max)**
  ③ 3대비급여실손·교통사고처리지원금(6주미만): 비고 → 정규 행(실비 상단·운전자 형사합의금 하단)
  ④ 2열 병기 (좌 | 우) 라벨 셀·헤더 행 제거 — 행명이 이미 `(질병 I 상해)` 순서 표현 · 간병인 질병|상해 유지
  ⑤ 종수술비(합성)는 **삭제하지 않았다** — 값이 1~5종에 반영 안 돼 삭제 시 손실(Step 6 선결 확인 · 비고 유지)
  ⑥ 대분류 합계 정합 · 이관 전후 이중 계상 0

★PII: 익명 합성 픽스처(290 `_raw` 선례).
"""
from __future__ import annotations

import io
from pathlib import Path

import pytest

from coverage.aggregator import build_before, build_final, group_rollup_v2
from coverage.compare import build_after_analysis
from coverage.constants import APPENDIX_ITEMS_V2, GROUP12_V2, KB_COVERAGES_V2, STANDARD_COUNT_V2
from coverage.v2_mapping import ROW_INDEX, resolve

MAN = 10_000

# BOHUMFIT-296b: 익명 정본 A~D의 Q6 전후 검산 정본.
# 실 PDF가 없는 CI에서는 합성 계약만 실행하고, 로컬 정본 폴더가 있으면 같은 테스트 안에서
# 원시 N대수술비 행 수·sum→max 차이·이관 값 보존을 전수 재검산한다(테스트 수 기준선 불변).
_Q6_REAL_EXPECTED = {
    "A": {"contracts": 15, "rows": 59, "legacy_total": 614_860_000, "total": 614_860_000,
          "monthly": 681_312, "n_events": 1, "n_values": [32], "n_sum": 2_000_000, "n_max": 2_000_000,
          "nonpay": 0, "six_weeks": 0},
    "B": {"contracts": 15, "rows": 58, "legacy_total": 1_468_790_000, "total": 1_467_790_000,
          "monthly": 4_675_189, "n_events": 8, "n_values": [124], "n_sum": 2_000_000, "n_max": 1_000_000,
          "nonpay": 9_000_000, "six_weeks": 10_000_000},
    "C": {"contracts": 5, "rows": 55, "legacy_total": 410_660_000, "total": 398_960_000,
          "monthly": 181_802, "n_events": 5, "n_values": [119], "n_sum": 21_700_000, "n_max": 10_000_000,
          "nonpay": 0, "six_weeks": 0},
    "D": {"contracts": 6, "rows": 57, "legacy_total": 480_440_000, "total": 476_440_000,
          "monthly": 488_294, "n_events": 9, "n_values": [2, 142], "n_sum": 5_000_000, "n_max": 1_000_000,
          "nonpay": 0, "six_weeks": 0},
}


def _raw(matrix=None, extra=None, contracts=1):
    return {
        "customer": {"name": "테스트", "age": 40, "sex": "여자"},
        "contracts": [
            {"idx": i, "insurer": f"손보{i}", "product": f"상품{i}", "contract_date": "2024-01-01",
             "pay_cycle": "월납", "pay_years": 20, "pay_months": 240, "maturity": "100세",
             "monthly_premium": 10_000 * i}
            for i in range(1, contracts + 1)
        ],
        "matrix": matrix or {}, "diagnosis": {}, "notes": {}, "extra": extra or {}, "warnings": [],
    }


def _by_id(before):
    return {c["row_id"]: c for c in before["coverages"] if c.get("row_id")}


def _real_q6_paths():
    """PII 파일명을 코드에 남기지 않고 정본 A~D를 찾는다. 폴더 부재 환경은 None."""
    from coverage.parser import KBFormatError, parse_document

    root = Path(__file__).resolve().parents[2] / "보장분석"
    comparison = root / "비교분석표"
    if not comparison.is_dir():
        return None
    standard = sorted(comparison.glob("*-INPUT.pdf"))
    overview = [p for p in sorted(comparison.glob("*INPUT.pdf")) if not p.name.endswith("-INPUT.pdf")]

    def _valid_dated(pattern: str, contracts: int):
        matches = []
        for path in sorted(root.rglob(pattern)):
            try:
                raw = parse_document(path.read_bytes())
            except KBFormatError:
                continue
            if len(raw.get("contracts") or []) == contracts:
                matches.append(path)
        assert len(matches) == 1, f"익명 Q6 정본 {pattern} 식별 수가 1이 아님: {len(matches)}"
        return matches[0]

    assert len(standard) == 1 and len(overview) == 1
    return {
        "A": standard[0],
        "B": overview[0],
        "C": _valid_dated("*20260805*.pdf", 5),
        "D": _valid_dated("*20260729*.pdf", 6),
    }


def _assert_real_q6_recheck():
    """296b: A~D 실제 행을 세어 기존 'C·D 단건' 수기 오판의 재발을 막는다."""
    from coverage.constants import classify_extra, extract_n_surgery
    from coverage.parser import _extract_pages, _last_amount, classify_page, parse_document

    paths = _real_q6_paths()
    if paths is None:  # 실 PDF는 PII라 레포/CI에 둘 수 없다.
        return

    for label, path in paths.items():
        expected = _Q6_REAL_EXPECTED[label]
        pdf_bytes = path.read_bytes()
        raw = parse_document(pdf_bytes)
        before = build_before(raw, today="2026-07-29")
        rows = _by_id(before)
        enrolled = [row for row in before["coverages"] if row.get("enrolled")]

        events = []
        for page in _extract_pages(pdf_bytes):
            if classify_page(page) != "detail":
                continue
            for line in page:
                classified = classify_extra(line)
                if not classified or classified[0] != "N대수술비":
                    continue
                amount = _last_amount(line)
                if amount is not None:
                    events.append((extract_n_surgery(line), amount))

        n_row = rows["major_n_surgery"]["summary"] or 0
        nonpay = rows["actual_3major_nonpay"]["summary"] or 0
        six_weeks = rows["driver_settlement_6w"]["summary"] or 0
        total = sum(row.get("summary") or 0 for row in enrolled)
        n_sum = sum(amount for _n, amount in events)

        assert len(before["contract_list"]) == expected["contracts"]
        assert len(before["coverages"]) == expected["rows"]
        assert before["premium"]["monthly_total"] == expected["monthly"]
        assert len(events) == expected["n_events"]
        assert sorted({n for n, _amount in events}) == expected["n_values"]
        assert n_sum == expected["n_sum"]
        assert max(amount for _n, amount in events) == n_row == expected["n_max"]
        assert nonpay == expected["nonpay"] and six_weeks == expected["six_weeks"]
        assert total == expected["total"]
        # ★이관 2행은 값 보존, 총액 변화는 오직 원시 N행 sum−max와 정확히 같다.
        assert expected["legacy_total"] - total == n_sum - n_row
        assert total - n_row - nonpay - six_weeks == (
            expected["legacy_total"] - n_sum - expected["nonpay"] - expected["six_weeks"]
        )


# ── ① 스키마 ────────────────────────────────────────────────────────────────
def test_schema_is_fifty_two_rows_with_stable_groups():
    assert STANDARD_COUNT_V2 == 52 and len(KB_COVERAGES_V2) == 52
    assert len(GROUP12_V2) == 11
    ids = {r.row_id for r in KB_COVERAGES_V2}
    assert {"major_n_surgery", "actual_3major_nonpay", "driver_settlement_6w"} <= ids


def test_new_row_positions():
    """N대수술비: 종수술 5종 하단·뇌혈관 상단 / 3대비급여: 실비 상단 / 6주미만: 형사합의금 하단."""
    assert ROW_INDEX["major_n_surgery"] == ROW_INDEX["tier_surgery_5"] + 1 == ROW_INDEX["surgery_cerebral"] - 1
    assert ROW_INDEX["actual_3major_nonpay"] == ROW_INDEX["actual_inpatient"] - 1
    assert ROW_INDEX["driver_settlement_6w"] == ROW_INDEX["driver_settlement"] + 1


# ── ②③ 이관·매칭 ────────────────────────────────────────────────────────────
def test_relocated_remarks_route_to_regular_rows_not_appendix():
    assert resolve("3대비급여실손") == ("row", "actual_3major_nonpay", None)
    assert resolve("교통사고처리지원금(6주미만)") == ("row", "driver_settlement_6w", None)
    assert resolve("N대수술비") == ("row", "major_n_surgery", None)
    assert "3대비급여실손" not in APPENDIX_ITEMS_V2
    # ★고액암·경증치매진단은 비고 유지(Human 확정)
    assert "고액암" in APPENDIX_ITEMS_V2 and "경증치매진단" in APPENDIX_ITEMS_V2


def test_n_surgery_takes_max_not_sum():
    """★여러 건이면 최대 보상금액(max) — 합산 아님."""
    from coverage.parser import parse_detail_pages
    detail = [
        "홍길동 님의 상품별 가입담보상세", "가나손보 | 가입일자 : 2024-01-01 |", "합성 건강보험",
        "홍길동/홍길동 월납/20년/100세만기", "2024-01-01~2124-01-01 50,000원",
        "1 정액 131대질병수술비(간편가입) 특정질병수술 500만",
        "2 정액 121대질병수술비(갱신형) 특정질병수술 300만",
    ]
    _notes, extra = parse_detail_pages([detail], [{"idx": 1, "monthly_premium": 50_000}])
    assert extra["N대수술비"]["by_company"]["1"] == 500 * MAN  # max(500, 300)
    before = build_before(_raw(extra=extra), today="2026-08-18")
    assert _by_id(before)["major_n_surgery"]["summary"] == 500 * MAN


def test_relocation_preserves_value_and_group_total():
    """③⑥ 이관은 값을 보존하고 대분류 합계에 정확히 반영된다(이중 계상 0)."""
    before = build_before(_raw(extra={
        "3대비급여실손": {"agg": "rep", "by_company": {"1": 900 * MAN}},
        "교통사고처리지원금(6주미만)": {"agg": "sum", "by_company": {"1": 1000 * MAN}},
        "N대수술비": {"agg": "rep", "by_company": {"1": 200 * MAN}},
    }), today="2026-08-18")
    rows = _by_id(before)
    assert rows["actual_3major_nonpay"]["summary"] == 900 * MAN
    assert rows["driver_settlement_6w"]["summary"] == 1000 * MAN
    assert rows["major_n_surgery"]["summary"] == 200 * MAN
    # 대분류 합계 = 소속 행 합(이관분이 정확히 들어갔다)
    roll = group_rollup_v2(before["coverages"])
    assert roll["실 비"] >= 900 * MAN and roll["운전자"] >= 1000 * MAN and roll["수 술"] >= 200 * MAN
    # 비고에 이관 대상이 남지 않았다
    app = {c["kb_name"] for c in before["coverages"] if not c.get("row_id")}
    assert not ({"3대비급여실손", "교통사고처리지원금(6주미만)"} & app)
    _assert_real_q6_recheck()


# ── ⑤ 종수술비 — 삭제하지 않았다(값이 1~5종에 없음) ──────────────────────────
def test_jong_synthetic_label_kept_when_not_in_tiers():
    """★Step 6 선결: 종수술비(합성) 값이 1~5종에 반영 안 됐으면 **삭제 금지**(비고 보존)."""
    before = build_before(_raw(extra={"종수술비": {"agg": "sum", "by_company": {"1": 300 * MAN}}}),
                          today="2026-08-18")
    rows = _by_id(before)
    assert all(rows[f"tier_surgery_{t}"]["summary"] is None for t in range(1, 6))  # 1~5종 비어 있다
    app = next((c for c in before["coverages"] if c["kb_name"] == "종수술비"), None)
    assert app is not None and app["summary"] == 300 * MAN  # 비고에 보존(삭제 안 함)


# ── ④ 2열 라벨 제거 ─────────────────────────────────────────────────────────
def test_dual_header_removed_from_export():
    from coverage.export_excel import DATA_ROW0, build_workbook_bytes, track_row_of
    import openpyxl

    analysis = build_after_analysis(
        {"before": (b := build_before(_raw(contracts=1), today="2026-08-18")),
         "final": build_final(b, {}), "warnings": []},
        {"existing": [], "proposals": []},
    )
    wb = openpyxl.load_workbook(io.BytesIO(build_workbook_bytes(analysis)))
    for sheet in ("컨설팅 전", "컨설팅 후"):
        ws = wb[sheet]
        # 헤더 행 없음 → 컨설팅 전/후도 DATA_ROW0 + 순서(최종 시트와 동일)
        assert track_row_of("tier_surgery_1") == DATA_ROW0 + ROW_INDEX["tier_surgery_1"]
        for r in range(DATA_ROW0, DATA_ROW0 + len(KB_COVERAGES_V2)):
            assert ws.cell(row=r, column=3).value != "2열 병기 (좌 | 우)"
