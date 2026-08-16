# -*- coding: utf-8 -*-
"""BOHUMFIT-252 회귀 → 291(S3) 49행 양식 이식 — 회사별 열 전개(전/후) + 2단 헤더 + [후] 신규 골격.

익명 합성 픽스처. ★값·집계 불변 계약: 렌더 계층만 검증 — by_company/summary 값이
시트 셀에 그대로(만원) 옮겨지고, 회사별 열 합 = 합계 열(대사 0)임을 고정한다.
★291: 시트 `컨설팅 전`/`컨설팅 후`(회사당 2열·7행 시작). 단언 의미는 252 그대로다.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from coverage.aggregator import build_before
from coverage.compare import build_after_analysis
from coverage.excel_style import EMERALD, WHITE
from tests.excel_v2_layout import (
    COL_SUM,
    ROW_COMPANY,
    ROW_PREMIUM,
    ROW_PRODUCT,
    SHEET_AFTER,
    SHEET_BEFORE,
    SHEET_FINAL,
    company_cells,
    company_col,
    header_labels,
    row_of,
    sum_cell,
    workbook,
)

MAN = 10_000


def _analysis(companies: int = 2) -> dict:
    """계약 2개·담보별 by_company 채움(만원 정수 배수 — 반올림 편차 0 설계)."""
    contracts = [
        {
            "idx": i, "insurer": f"합성손보{i}", "product": f"합성상품{i}호",
            "contract_date": f"202{i}-01-01", "pay_cycle": "월납", "pay_years": 20,
            "pay_months": 240, "maturity": "100세", "monthly_premium": 10_000 * i,
        }
        for i in range(1, companies + 1)
    ]
    raw = {
        "customer": {"name": "홍길동", "age": 50, "sex": "남자"},
        "contracts": contracts,
        "matrix": {
            "질병사망": {"by_company": {"1": 3000 * MAN, "2": 2000 * MAN}},
            "암진단금": {"by_company": {"1": 1000 * MAN}},
            "질병후유장해": {"by_company": {"2": 500 * MAN}},
        },
        "diagnosis": {}, "notes": {},
        "extra": {},
        "warnings": [],
    }
    before = build_before(raw, today="2026-07-27")
    return {"before": before, "final": {"premium": before["premium"], "coverages": [], "rollup_by_group12": []}}


def _overview_analysis() -> dict:
    raw = {
        "customer": {"name": "홍길동", "age": 50, "sex": "남자"},
        "contracts": [{
            "idx": i, "insurer": f"합성손보{i}", "product": f"합성상품{i}호",
            "contract_date": "2024-01-01", "pay_cycle": "월납", "pay_years": 20,
            "pay_months": 240, "maturity": "100세", "monthly_premium": 10_000,
        } for i in range(1, 3)],
        "matrix": {
            "상해사망": {"summary": 30000 * MAN, "by_company": {}, "overview": True},
            "암진단금": {"summary": 10000 * MAN, "by_company": {}, "overview": True},
        },
        "diagnosis": {}, "notes": {}, "extra": {}, "warnings": [],
    }
    before = build_before(raw, today="2026-07-27")
    return {"before": before, "final": {"premium": before["premium"], "coverages": [], "rollup_by_group12": []}}


ROWS = {"질병사망": "death_disease", "암진단금": "cancer_general", "질병후유장해": "disability_disease_3",
        "상해사망": "death_injury", "항암약물방사선": None}


def test_two_tier_header_company_and_product():
    """252 A → 291: 2행=회사명(에메랄드+흰 글자)·4행=상품명·6행=월납 — 회사당 2열."""
    result = build_after_analysis(_analysis(), {"existing": [], "proposals": []})
    ws = workbook(result)[SHEET_BEFORE]
    assert ws.cell(row=ROW_COMPANY, column=company_col(0)).value == "합성손보1"
    assert ws.cell(row=ROW_COMPANY, column=company_col(1)).value == "합성손보2"
    assert ws.cell(row=ROW_PRODUCT, column=company_col(0)).value == "합성상품1호"
    assert ws.cell(row=ROW_PRODUCT, column=company_col(1)).value == "합성상품2호"
    assert ws.cell(row=ROW_COMPANY, column=company_col(0)).fill.fgColor.rgb == EMERALD
    assert ws.cell(row=ROW_COMPANY, column=company_col(0)).font.color.rgb == WHITE
    assert ws.cell(row=ROW_PREMIUM, column=company_col(0)).value == 10_000
    assert ws.cell(row=ROW_PREMIUM, column=company_col(1)).value == 20_000
    assert ws.cell(row=ROW_PREMIUM, column=COL_SUM).value == 30_000  # 월납 합계


def test_company_columns_match_payload_and_sum_to_total():
    """★회사별 열 값 = payload by_company(만원) · 회사별 합 = 합계 열(전·후 대사 0)."""
    result = build_after_analysis(_analysis(), {"existing": [], "proposals": []})
    wb = workbook(result)
    n = 2
    for sheet, payload in ((SHEET_BEFORE, result["before"]), (SHEET_AFTER, result["after"]["before"])):
        ws = wb[sheet]
        rows = {c["row_id"]: c for c in payload["coverages"] if c.get("row_id")}
        for name, row_id in ROWS.items():
            if not row_id:
                continue
            row = row_of(row_id)
            data = rows[row_id]
            for idx in range(n):
                key = str(idx + 1)
                expect = (data.get("by_company") or {}).get(key)
                assert ws.cell(row=row, column=company_col(idx)).value == (None if expect is None else round(expect / MAN))
            assert sum(company_cells(ws, row, n)) == sum_cell(ws, row)


def test_after_new_contract_skeleton_column():
    """252 B: 제안 미착수 — [후] 말미에 '신규 설계 반영 대상' 골격 열(값 전부 공란)."""
    result = build_after_analysis(_analysis(), {"existing": [], "proposals": []})
    ws = workbook(result)[SHEET_AFTER]
    col_new = company_col(2)
    assert ws.cell(row=ROW_COMPANY, column=col_new).value == "신규 설계 반영 대상"
    for row_id in ("death_disease", "cancer_general", "disability_disease_3", "tier_surgery_1"):
        assert ws.cell(row=row_of(row_id), column=col_new).value is None
        assert ws.cell(row=row_of(row_id), column=col_new + 1).value is None
    assert ws.cell(row=ROW_PREMIUM, column=col_new).value is None


def test_no_skeleton_when_proposal_contract_present():
    """제안 계약(신규제안)이 [후]에 이미 있으면 골격 열을 만들지 않는다."""
    result = build_after_analysis(_analysis(), {"existing": [], "proposals": []})
    result["after"]["before"]["contract_list"] = list(result["after"]["before"]["contract_list"]) + [{
        "idx": "P1", "insurer": "신규제안", "product": "신규설계", "contract_date": None,
        "pay_cycle": "월납", "pay_years": 20, "pay_months": 240, "maturity": "100세",
        "monthly_premium": 30_000, "remark": "신규제안", "consulting_status": "신규제안",
    }]
    ws = workbook(result)[SHEET_AFTER]
    labels = header_labels(ws)
    assert "신규 설계 반영 대상" not in labels
    assert "신규제안" in labels  # 제안 계약이 일반 회사 열로 전개


def test_overview_no_company_columns_and_no_skeleton():
    """246 계약 유지: overview 문서 — 회사 열·골격 열 미생성, 합계 열만."""
    result = build_after_analysis(_overview_analysis(), {"existing": [], "proposals": []})
    wb = workbook(result)
    for sheet in (SHEET_BEFORE, SHEET_AFTER):
        ws = wb[sheet]
        labels = header_labels(ws)
        assert "신규 설계 반영 대상" not in labels and "합성손보1" not in labels
        assert ws.cell(row=row_of("death_injury"), column=COL_SUM).value == 30000
        assert ws.cell(row=row_of("cancer_general"), column=COL_SUM).value == 10000


# ── 252 재개: '?'(계약 미상) 버킷 조건부 "계약 미확인" 열 ─────────────────────────
def _analysis_with_unknown_bucket() -> dict:
    """V2 정식 행(질병사망)에 '?' 버킷이 남는 합성 — 동일 보험료 모호 문서 재현.
    (구 픽스처는 extras 라벨 `항암약물방사선`을 썼는데 그 라벨은 291 이후 비고행이라 가드 대상이 아니다.)"""
    raw = {
        "customer": {"name": "홍길동", "age": 50, "sex": "남자"},
        "contracts": [{
            "idx": 1, "insurer": "합성손보1", "product": "합성상품1호",
            "contract_date": "2024-01-01", "pay_cycle": "월납", "pay_years": 20,
            "pay_months": 240, "maturity": "100세", "monthly_premium": 10_000,
        }],
        "matrix": {"질병사망": {"by_company": {"1": 3000 * MAN, "?": 200 * MAN}}},
        "diagnosis": {}, "notes": {}, "extra": {}, "warnings": [],
    }
    before = build_before(raw, today="2026-07-27")
    return {"before": before, "final": {"premium": before["premium"], "coverages": [], "rollup_by_group12": []}}


def test_unknown_bucket_renders_explicit_column_and_reconciles():
    """'?' 잔존 시 "계약 미확인" 열 명시 출력 — 회사열+미확인 = 합계([전]·[후] 이월 포함)."""
    result = build_after_analysis(_analysis_with_unknown_bucket(), {"existing": [], "proposals": []})
    wb = workbook(result)
    row = row_of("death_disease")
    for sheet in (SHEET_BEFORE, SHEET_AFTER):
        ws = wb[sheet]
        col_unk = company_col(1)  # 회사 1열(2칸) 뒤
        assert ws.cell(row=ROW_COMPANY, column=col_unk).value == "계약 미확인"
        assert ws.cell(row=row, column=col_unk).value == 200            # '?' 200만원 → 만원
        assert ws.cell(row=row, column=company_col(0)).value == 3000    # 실계약 열
        assert sum(company_cells(ws, row, 2)) == sum_cell(ws, row) == 3200
        assert ws.cell(row=ROW_PREMIUM, column=col_unk).value is None  # 보험료 개념 없음
    # 신규 골격 열은 미확인 열 뒤로 밀림([후]).
    assert wb[SHEET_AFTER].cell(row=ROW_COMPANY, column=company_col(2)).value == "신규 설계 반영 대상"


def test_no_unknown_column_when_bucket_absent():
    """'?' 없으면 미확인 열 미출력(현행 유지) — 실 5케이스 잔존 0(253) 상태의 기본형."""
    result = build_after_analysis(_analysis(), {"existing": [], "proposals": []})
    ws = workbook(result)[SHEET_BEFORE]
    assert "계약 미확인" not in header_labels(ws)


def test_final_sheet_design_headers():
    """252 C → 291: `최종` 헤더(기존/점검 후/기대효과)=에메랄드+흰 글자."""
    result = build_after_analysis(_analysis(), {"existing": [], "proposals": []})
    ws = workbook(result)[SHEET_FINAL]
    for col, text in ((6, "기존"), (8, "점검 후"), (10, "기대효과")):
        cell = ws.cell(row=2, column=col)
        assert cell.value == text
        assert cell.fill.fgColor.rgb == EMERALD and cell.font.color.rgb == WHITE
