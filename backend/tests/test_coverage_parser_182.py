from __future__ import annotations

from coverage import parser


def _matrix_pages() -> list[list[str]]:
    return [
        [
            "상품별 가입현황",
            "구분 (1) (2)",
            "상해사망 5억5,000만원 5억5,000만원 -",
            "일반암 1억원 1억원 -",
        ]
    ]


def test_company_wrap_uses_known_insurer_not_product_prefix() -> None:
    lines = [
        "전체 계약리스트",
        "1       메리츠화",
        "재 (무) The좋은보험 2001",
        "2020-01-01 월납 20년 90세 10,000원",
    ]

    contracts = parser.parse_contract_list(lines)

    assert contracts[0]["insurer"] == "메리츠화재"
    assert contracts[0]["product"] == "(무) The좋은보험 2001"


def test_no_premium_contract_is_counted_and_labeled_missing(monkeypatch) -> None:
    pages = [
        [
            "전체 계약리스트 계약리스트",
            "1 메리츠화재 (무)알파보험 2020-01-01 월납 20년 90세 10,000원",
            "2 DB손보 BOP보험 2021-02-02 월납 100세 보험료미제공",
        ],
        *_matrix_pages(),
        [
            "전체 담보 진단 현황 진단",
            "상해사망 5억5,000만원 5억5,000만원 - 충분",
            "일반암 1억원 1억원 - 충분",
        ],
    ]
    monkeypatch.setattr(parser, "_extract_pages", lambda _pdf_bytes: pages)

    raw = parser.parse_document(b"%PDF-synthetic")

    assert raw["warnings"] == []
    assert [c["idx"] for c in raw["contracts"]] == [1, 2]
    assert raw["contracts"][1]["insurer"] == "DB손보"
    assert raw["contracts"][1]["monthly_premium"] is None
    assert {int(k) for row in raw["matrix"].values() for k in row["by_company"]} == {1, 2}


def test_moon_baseline_values_are_not_changed() -> None:
    contracts = [
        {"idx": 1, "monthly_premium": 573_227, "pay_months": 240},
        {"idx": 2, "monthly_premium": None, "pay_months": None},
        {"idx": 3, "monthly_premium": 44_409_648, "pay_months": 1},
    ]
    paid = sum((c["monthly_premium"] or 0) * (c["pay_months"] or 0) for c in contracts)

    assert contracts[0]["monthly_premium"] == 573_227
    assert paid == 181_984_128
    assert parser.parse_matrix(_matrix_pages())["상해사망"]["summary"] == 550_000_000
    assert parser.parse_matrix(_matrix_pages())["일반암"]["summary"] == 100_000_000
