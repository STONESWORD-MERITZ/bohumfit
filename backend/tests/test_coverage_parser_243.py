# -*- coding: utf-8 -*-
"""BOHUMFIT-243 회귀 — 익명 합성 픽스처(홍길동)만 사용.

① 계약리스트에서 세로로 쪼개진 **비보험사 기관명**(공제·금고·중앙회) 복원 + 상품명 잔재 제거.
② "80%이상" 후유장해를 후유장해 대분류 집계에서 제외(2026-07-24 Human 결정 · 244 양식 정합).
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from coverage.aggregator import build_before  # noqa: E402
from coverage.constants import EXTRA_LABEL_GROUP, GROUP_ETC, classify_extra  # noqa: E402
from coverage.parser import parse_contract_list  # noqa: E402

MAN = 10_000

# ① 기관명이 윗줄("새마을금")+아랫줄("고중앙회")로 쪼개진 계약리스트(실측 구조 익명 재현).
P5_SPLIT_INSTITUTION = """홍길동 님의 전체 계약리스트 2026-07-24
 (56세 ,여자)
※ 기준담보/권장금액 : 기본형(37개)/표준형
새마을금
15 無MGONE레저상해공제_24A 2026-06-30 월납 5년 56세 100,000원
고중앙회
""".splitlines()

# 연속 표기(기존 경로) — 상품명에 회사명이 그대로 들어간 케이스는 보존되어야 한다.
P5_INLINE_INSURER = """홍길동 님의 전체 계약리스트 2026-07-24
 (56세 ,여자)
※ 기준담보/권장금액 : 기본형(37개)/표준형
7 한화생명 한화생명 제로백H종신보험 무배당 2025-02-26 월납 20년 종신 1,000,000원
""".splitlines()


# ── ① 기관명 복원 ────────────────────────────────────────────────────────────
def test_split_institution_name_restored():
    contracts = parse_contract_list(P5_SPLIT_INSTITUTION)
    c = next(x for x in contracts if x["idx"] == 15)
    assert c["insurer"] == "새마을금고중앙회"
    assert c["monthly_premium"] == 100_000
    # 상품명에 기관명 조각이 남지 않는다.
    assert "새마을금" not in (c["product"] or "")
    assert "고중앙회" not in (c["product"] or "")
    assert "無MGONE레저상해공제_24A" in (c["product"] or "")


def test_inline_insurer_in_product_preserved():
    """연속 표기 케이스는 기존 동작 불변(상품명에 회사명이 포함돼 있어도 보존)."""
    contracts = parse_contract_list(P5_INLINE_INSURER)
    c = next(x for x in contracts if x["idx"] == 7)
    assert c["insurer"] == "한화생명"
    assert "제로백H종신보험" in (c["product"] or "")


# ── ② 80%이상 후유장해 — 후유장해 집계 미포섭 ────────────────────────────────
def test_over80_disability_excluded_from_disability_group():
    """80%이상 후유장해는 후유장해 대분류에 포섭되지 않고 기타로 표시된다."""
    assert "80%이상 후유장해" not in EXTRA_LABEL_GROUP  # 매핑 없음 = 기타(기본값)
    raw = {
        "customer": {"name": "홍길동", "age": 56, "sex": "여자"},
        "contracts": [{
            "idx": 1, "insurer": "가나손보", "product": "합성", "contract_date": "2024-01-01",
            "pay_cycle": "월납", "pay_years": 20, "pay_months": 240, "maturity": "100세",
            "monthly_premium": 50_000,
        }],
        "matrix": {
            # BOHUMFIT-246: 파서 산출 키 = 정식명(상해후유장해 — 구 상해80%미만후유장해는 별칭).
            "상해후유장해": {"by_company": {"1": 5000 * MAN}},
            "질병후유장해": {"by_company": {"1": 2000 * MAN}},
        },
        "diagnosis": {}, "notes": {},
        "extra": {"80%이상 후유장해": {"agg": "sum", "by_company": {"1": 100 * MAN}}},
        "warnings": [],
    }
    before = build_before(raw, today="2026-07-24")
    by_group = {}
    for c in before["coverages"]:
        if c["enrolled"]:
            by_group.setdefault(c["group12"], []).append((c["kb_name"], c["summary"]))

    # 후유장해 집계 = 3-100%(80%미만) 담보만 = 5,000만 + 2,000만
    disability = by_group.get("후유장해", [])
    assert sorted(disability) == sorted([("상해후유장해", 5000 * MAN), ("질병후유장해", 2000 * MAN)])  # 246 정식명
    assert sum(v for _, v in disability) == 7000 * MAN
    # 80%이상은 기타로 표시(정보 보존) — 후유장해 합계에 미포함.
    assert ("80%이상 후유장해", 100 * MAN) in by_group.get(GROUP_ETC, [])


def test_over80_classifier_still_labels_separately():
    """분류 자체는 기존대로 별도 라벨을 유지한다(경계 정밀화 — 234~240 로직 무변경)."""
    got = classify_extra("2 정액 갱신형 일반상해80%이상후유장해(통합간편가입) 상해80%이상후유장해 100만")
    assert got is not None and got[0] == "80%이상 후유장해"
    # 3-100% 담보는 80%이상으로 분류되지 않는다.
    assert classify_extra("4 정액 상해후유장해(3-100%)(간편,갱신형) 상해후유장해 5,000만") is None
