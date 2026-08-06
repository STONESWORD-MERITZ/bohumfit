"""BOHUMFIT-272b — 계약리스트 상품명에 회사명 조각이 흡수되는 현상 제거.

★현상: 회사명이 두 줄로 쪼개지는 기관(새마을금고중앙회·신용협동조합중앙회)에서
조각 줄이 `_is_product_continuation`을 통과해 앞 상품명 끝에 붙는다.

★최우선 제약: **과잉 절삭 금지**(251에서 코드 절삭으로 3회 반려된 이력).
정본 2건 상품명은 한 글자도 변하면 안 되고, 상품명에 브랜드가 정당하게 포함된 사례를 보호해야 한다.
"""
from pathlib import Path

import pytest

from coverage.parser import _strip_trailing_insurer_fragment

ROOT = Path(__file__).resolve().parents[2]
PDF_DIR = ROOT / "보장분석" / "비교분석표"
ACTUAL_PDF = next(PDF_DIR.glob("20260729_*_보장분석.pdf"), None)
STANDARD_PDF = next(PDF_DIR.glob("*-INPUT.pdf"), None)
OVERVIEW_PDF = next((p for p in PDF_DIR.glob("*INPUT.pdf") if p != STANDARD_PDF), None)


def _products(pdf: Path) -> list[tuple[int, str | None, str | None]]:
    from coverage.aggregator import build_before
    from coverage.parser import parse_document

    before = build_before(parse_document(pdf.read_bytes()), today="2026-07-29")
    return [(c["idx"], c.get("insurer"), c.get("product")) for c in before["contract_list"]]


# ── 순수 로직: 절삭 조건 ────────────────────────────────────────────────────
def test_strips_next_contract_insurer_prefix():
    """다음 계약 회사명의 앞조각이 붙은 경우(실측 계약4)."""
    contracts = [
        {"idx": 4, "insurer": "DB손보", "product": "100세청춘보험0901 새마을금"},
        {"idx": 5, "insurer": "새마을금고", "product": "無MG BlueBird저축공제_22A"},
    ]
    _strip_trailing_insurer_fragment(contracts)
    assert contracts[0]["product"] == "100세청춘보험0901"


def test_strips_own_insurer_remainder():
    """자기 회사명 잔여가 남은 경우(실측 계약5 — insurer가 짧게 잡혀 '중앙회'가 남았다)."""
    contracts = [
        {"idx": 5, "insurer": "새마을금고", "product": "無MG BlueBird저축공제_22A 중앙회"},
        {"idx": 6, "insurer": "신용협동조합중앙회", "product": "무)어부바신협비즈종합공제2009"},
    ]
    _strip_trailing_insurer_fragment(contracts)
    assert contracts[0]["product"] == "無MG BlueBird저축공제_22A"


def test_strips_own_insurer_prefix_on_last_contract():
    """마지막 계약이라 '다음 회사명'이 없어도 자기 회사명 조각으로 판정한다(실측 계약6)."""
    contracts = [
        {"idx": 6, "insurer": "신용협동조합중앙회", "product": "무)어부바신협비즈종합공제2009 신용협동조"},
    ]
    _strip_trailing_insurer_fragment(contracts)
    assert contracts[0]["product"] == "무)어부바신협비즈종합공제2009"


# ── ★과잉 절삭 방지 ────────────────────────────────────────────────────────
def test_keeps_brand_in_the_middle():
    """★중간에 든 브랜드는 건드리지 않는다 — 끝 토큰만 대상이다."""
    contracts = [{"idx": 1, "insurer": "메리츠화재", "product": "(무) 메리츠 The간편한건강보험1804(1종)"}]
    _strip_trailing_insurer_fragment(contracts)
    assert contracts[0]["product"] == "(무) 메리츠 The간편한건강보험1804(1종)"


def test_keeps_full_insurer_name_at_the_end():
    """★끝 토큰이 회사명 **전체**면 정당한 표기로 보고 남긴다."""
    contracts = [{"idx": 1, "insurer": "메리츠화재", "product": "든든보장보험 메리츠화재"}]
    _strip_trailing_insurer_fragment(contracts)
    assert contracts[0]["product"] == "든든보장보험 메리츠화재"


def test_keeps_single_token_product():
    """단일 토큰 상품명은 손대지 않는다(제거하면 빈 이름이 된다)."""
    contracts = [{"idx": 1, "insurer": "새마을금고중앙회", "product": "새마을금"}]
    _strip_trailing_insurer_fragment(contracts)
    assert contracts[0]["product"] == "새마을금"


def test_keeps_unrelated_tail():
    """회사명과 무관한 끝 토큰은 남긴다."""
    contracts = [{"idx": 1, "insurer": "삼성화재", "product": "무배당 건강보험 1종"}]
    _strip_trailing_insurer_fragment(contracts)
    assert contracts[0]["product"] == "무배당 건강보험 1종"


def test_handles_missing_product_and_empty_list():
    _strip_trailing_insurer_fragment([])
    contracts = [{"idx": 1, "insurer": "삼성화재", "product": None}]
    _strip_trailing_insurer_fragment(contracts)
    assert contracts[0]["product"] is None


def test_strips_only_one_fragment():
    """끝 토큰 하나만 제거한다 — 연쇄 절삭으로 상품명을 갉아먹지 않는다."""
    contracts = [{"idx": 1, "insurer": "새마을금고중앙회", "product": "보험A 새마을금 중앙회"}]
    _strip_trailing_insurer_fragment(contracts)
    assert contracts[0]["product"] == "보험A 새마을금"


# ── 실 PDF 회귀 ────────────────────────────────────────────────────────────
@pytest.mark.skipif(
    ACTUAL_PDF is None,
    reason="실 PDF 없음(로컬 전용 · PII로 커밋 불가)",
)
def test_real_case_products_are_clean():
    """★실 6계약 건에서 오염 3건이 사라지고 나머지 3건은 그대로다."""
    assert ACTUAL_PDF is not None
    rows = _products(ACTUAL_PDF)
    products = {idx: product for idx, _, product in rows}
    assert len(rows) == 6
    assert products[4] == "100세청춘보험0901"
    assert products[5] == "無MG BlueBird저축공제_22A"
    assert products[6] == "무)어부바신협비즈종합공제2009"
    # 원래 정상이던 3건도 그대로
    assert products[1] == "(무) 알파Plus보장보험1604"
    assert "간편3·10·10" in (products[2] or "")
    assert "새로고침100세" in (products[3] or "")
    # 회사명 조각이 어디에도 남아 있지 않다
    for product in products.values():
        assert not (product or "").endswith(("새마을금", "중앙회", "신용협동조"))


@pytest.mark.skipif(
    STANDARD_PDF is None or OVERVIEW_PDF is None,
    reason="정본 PDF 없음(로컬 전용)",
)
def test_baseline_products_are_byte_identical():
    """★★정본 2건 상품명 30건이 **한 글자도 바뀌지 않는다**(과잉 절삭 0).

    251에서 3회 반려된 실패 패턴을 영구히 막는 가드다.
    """
    expected_standard = [
        "(무) 메리츠 The간편한건강보험1804(1종)",
        "(무) 메리츠 운전자 상해 종합보험2504",
        "무배당 삼성화재건강보험간편하게건강하게 (1601.1)1종",
        "NEW 프리미엄 건강보험Ⅱ",
    ]
    assert STANDARD_PDF is not None
    rows = _products(STANDARD_PDF)
    assert len(rows) == 15
    assert [product for _, _, product in rows][:4] == expected_standard

    expected_overview = [
        "(무)KB손보실손의료비보장보험(19.01)",
        "(무) 메리츠 운전자 상해 종합보험2604",
        "(무) 메리츠 통합간편건강보험(연만기 형)2604(통합간편심사형)",
        "성공하는 Owner 재산종합보험 무배당",
    ]
    assert OVERVIEW_PDF is not None
    rows2 = _products(OVERVIEW_PDF)
    assert len(rows2) == 15
    assert [product for _, _, product in rows2][:4] == expected_overview

    # ★브랜드가 중간에 든 이름이 살아 있다(끝 토큰만 보는 조건의 실증).
    assert any("메리츠" in (p or "") for _, _, p in rows)


# ── 보호 영역 ──────────────────────────────────────────────────────────────
def test_272b_does_not_touch_protected_modules():
    """★`pipeline/`·`filters.py`·집계/상수 모듈에 272b 흔적이 없다."""
    assert "272b" not in (ROOT / "backend" / "filters.py").read_text(encoding="utf-8")
    for name in ("aggregator.py", "constants.py", "amount.py"):
        path = ROOT / "backend" / "coverage" / name
        if path.exists():
            assert "272b" not in path.read_text(encoding="utf-8"), name
    for path in (ROOT / "backend" / "pipeline").glob("*.py"):
        assert "BOHUMFIT-272b" not in path.read_text(encoding="utf-8"), path.name
