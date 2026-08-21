# -*- coding: utf-8 -*-
"""BOHUMFIT-302b — 통합치료비 표시 구조 확장(52→55행) 계약.

★고정하는 계약 (Human 확정)
  ① 스키마 **55행** = 52 + `뇌 혈전용해`·`심장 혈전용해`·`암 통합치료비 (연간 총 지급 한도)` · 대분류 11 불변
  ② 회색 헤더 = **`sum_excluded` 3행** — 암 통합치료비 한도(신설) · 순환계 치료비(심장→뇌 이동) · 80% 후유장해(기존)
     ★값은 보존하되 **대분류·총액 합계에 더하지 않는다**(80% 행과 같은 처리 · 243)
  ③ 위치: 암 통합치료비 한도 = 암 진단비 **윗** · 순환계 치료비 = 뇌혈관질환 **윗** · 혈전용해 2행 = 심장질환 수술비 **아래**
  ④ 혈전용해치료 → 신규 2행에 **각각 같은 금액** · 순환계 수술 → 뇌혈관·심장질환 수술비 각각
  ⑤ 암 통합치료비 본체 → 비고행이 아니라 **회색 헤더 행**(담보 여러 건이면 합산)
  ⑥ **제외**: 순환계 나머지 내역(CRRT·인공호흡기·저체온·부분체외순환·중환자실·검사·재활)은 표·비고 어디에도 없다
  ⑦ ★`route_item` 표기 매칭 **무변경** — 혈전용해는 순환계 분배 분기에서만 처리한다(302 판정 준수)

★PII: 익명 합성 픽스처만.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from coverage.aggregator import build_before, group_rollup_v2  # noqa: E402
from coverage.constants import (  # noqa: E402
    GROUP12_V2,
    KB_COVERAGES_V2,
    STANDARD_COUNT_V2,
)
from coverage.integrated_treatment import (  # noqa: E402
    distribution_entries,
    extract_integrated_treatments,
    route_item,
)
from coverage.v2_mapping import ROW_INDEX, resolve  # noqa: E402

MAN = 10_000


def _entry(kb_name, amount, group12, agg, source, raw=None):
    return {"kb_name": kb_name, "amount": amount, "kb_group": group12, "group12": group12,
            "agg": agg, "source": source, "raw": raw}


CIRC = [
    "169 갱신형 특정순환계질환 통합치료비",
    "- MRI촬영(급여) : 5만원 (연간 1회한)",
    "- 혈전용해치료 : 2,500만원 (연간 1회한)",
    "- 지속적신대체요법(CRRT)(급여) : 500만원",
    "- 종합병원 중환자실치료 : 2,000만원",
    "- 수술 : 수술 1회당 2,000만원",
    "1억원 28,655",
]


# ── ① 스키마 55행 ───────────────────────────────────────────────────────────
def test_schema_is_fifty_five_rows_with_stable_groups():
    assert STANDARD_COUNT_V2 == 55 and len(KB_COVERAGES_V2) == 55
    assert len(GROUP12_V2) == 11
    ids = {r.row_id for r in KB_COVERAGES_V2}
    assert {"thrombolysis_cerebral", "thrombolysis_cardiac", "cancer_integrated_limit"} <= ids


# ── ② 회색 헤더 = sum_excluded 3행 ──────────────────────────────────────────
def test_gray_headers_are_exactly_three_sum_excluded_rows():
    excluded = [r.row_id for r in KB_COVERAGES_V2 if r.sum_excluded]
    assert excluded == ["cancer_integrated_limit", "circulatory_treatment", "disability_80"]


def test_gray_rows_are_not_added_to_group_or_total():
    """★핵심 검산 — 회색 행 금액은 대분류 합계에도 총액에도 안 들어간다."""
    rows = [
        {"row_id": "cancer_integrated_limit", "group12": "암", "summary": 130_000_000, "sum_excluded": True},
        {"row_id": "cancer_general", "group12": "암", "summary": 30_000_000},
        {"row_id": "circulatory_treatment", "group12": "뇌", "summary": 50_000_000, "sum_excluded": True},
        {"row_id": "cerebral_disease", "group12": "뇌", "summary": 20_000_000},
    ]
    roll = group_rollup_v2(rows)
    assert roll["암"] == 30_000_000      # 1.3억(회색) 제외
    assert roll["뇌"] == 20_000_000      # 5,000만(회색) 제외


# ── ③ 위치 ─────────────────────────────────────────────────────────────────
def test_new_row_positions():
    assert ROW_INDEX["cancer_integrated_limit"] == ROW_INDEX["cancer_general"] - 1
    assert ROW_INDEX["circulatory_treatment"] == ROW_INDEX["cerebral_disease"] - 1
    assert ROW_INDEX["thrombolysis_cerebral"] == ROW_INDEX["surgery_cardiac"] + 1
    assert ROW_INDEX["thrombolysis_cardiac"] == ROW_INDEX["surgery_cardiac"] + 2


def test_circulatory_moved_from_heart_to_brain_group():
    row = next(r for r in KB_COVERAGES_V2 if r.row_id == "circulatory_treatment")
    assert row.group == "뇌" and row.sum_excluded is True


# ── ④ 혈전용해·수술 분배 ────────────────────────────────────────────────────
def test_thrombolysis_lands_on_two_new_rows_with_same_amount():
    """★뮤테이션(혈전용해 분배 제거) 검출점."""
    riders = extract_integrated_treatments(CIRC)
    got = {(e["kb_name"], e["amount"]) for e in distribution_entries(riders, _entry)}
    assert ("뇌혈전용해", 2500 * MAN) in got
    assert ("심장혈전용해", 2500 * MAN) in got
    assert ("뇌혈관수술", 2000 * MAN) in got and ("심혈관수술", 2000 * MAN) in got
    assert ("순환계 치료비", 10000 * MAN) in got


def test_thrombolysis_labels_resolve_to_the_new_rows():
    assert resolve("뇌혈전용해") == ("row", "thrombolysis_cerebral", None)
    assert resolve("심장혈전용해") == ("row", "thrombolysis_cardiac", None)


def test_route_item_is_untouched_for_thrombolysis():
    """★302 판정 준수 — 표기 매칭은 확장하지 않았다(분배 분기에서만 처리)."""
    assert route_item("혈전용해치료") is None


# ── ⑤ 암 본체 → 회색 헤더 ───────────────────────────────────────────────────
def test_cancer_body_lands_on_gray_header_not_appendix():
    lines = [
        "44 갱신형 암 통합치료비(실속형)",
        "3천만원 12,610",
        "암 통합치료비(실속형)특약 안내사항",
        "▶암(유사암제외) 수술 암(유사암제외) 수술 1회당 500만원",
        "▶유사암 수술 유사암 수술 1회당 100만원",
        "연간 총 지급액 한도 3천만원",
    ]
    riders = extract_integrated_treatments(lines)
    got = {e["kb_name"]: e["amount"] for e in distribution_entries(riders, _entry)}
    assert got["암 통합치료비 한도"] == 3000 * MAN
    assert resolve("암 통합치료비 한도") == ("row", "cancer_integrated_limit", None)
    assert not any("연간 총 지급 한도" in k for k in got)  # 구 비고 라벨 폐기


# ── ⑥ 제외 항목 ────────────────────────────────────────────────────────────
def test_excluded_circulatory_items_appear_nowhere():
    riders = extract_integrated_treatments(CIRC)
    entries = distribution_entries(riders, _entry)
    names = {e["kb_name"] for e in entries}
    for banned in ("MRI촬영(급여)", "지속적신대체요법(CRRT)(급여)", "종합병원 중환자실치료"):
        assert banned not in names
    unrouted = {i["name"] for i in riders[0]["unrouted"]}
    assert "혈전용해치료" not in unrouted and "수술" not in unrouted   # 착지했으므로 unrouted 아님
    assert "MRI촬영(급여)" in unrouted                                  # 제외분은 기록만


def test_gray_rows_survive_build_before_with_flag():
    raw = {
        "customer": {"name": "테스트", "age": 40, "sex": "여자"},
        "contracts": [{"idx": 1, "insurer": "가나손보", "product": "합성", "contract_date": "2024-01-01",
                       "pay_cycle": "월납", "pay_years": 20, "pay_months": 240, "maturity": "100세",
                       "monthly_premium": 10_000}],
        "matrix": {}, "diagnosis": {}, "notes": {},
        "extra": {"암 통합치료비 한도": {"agg": "sum", "by_company": {"1": 130_000_000}},
                  "순환계 치료비": {"agg": "sum", "by_company": {"1": 50_000_000}}},
        "warnings": [],
    }
    before = build_before(raw, today="2026-07-29")
    rows = {c["row_id"]: c for c in before["coverages"] if c.get("row_id")}
    assert rows["cancer_integrated_limit"]["summary"] == 130_000_000
    assert rows["cancer_integrated_limit"]["sum_excluded"] is True
    assert rows["circulatory_treatment"]["sum_excluded"] is True
    total = sum(c.get("summary") or 0 for c in before["coverages"]
                if c.get("enrolled") and not c.get("sum_excluded"))
    assert total == 0  # 회색 2행뿐이므로 합계 0 — 총액에 안 들어간다
