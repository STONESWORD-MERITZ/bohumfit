"""BOHUMFIT-126: S코드(상해) 초진/재진 기반 에피소드 그룹 분리 회귀.

동일 S코드라도 초진이면 새 상해 → 별개 그룹. 재진은 직전 초진 에피소드에 귀속.
S코드 외(M·K 등) 또는 초진 정보 없음 → 기존 단일 그룹 유지(하위호환).
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.disease_aggregator import build_disease_stats

TODAY = datetime(2026, 6, 25)


def _basic(code, date, io="외래", days=1, prov="A의원", name="손목부위의 염좌"):
    r = {"_ftype": "basic", "_fname": "x.pdf", "주상병코드": code, "주상병명": name,
         "진료개시일": date, "요양기관명": prov}
    r["입내원구분"] = io
    r["내원일수"] = str(days)
    return r


def _detail(date, act, prov="A의원"):
    return {"_ftype": "detail", "_fname": "x.pdf", "진료개시일": date,
            "진료내역": act, "요양기관명": prov}


def test_s_code_two_first_visits_two_groups():
    """(a) 동일 S코드 초진 2회 → 그룹 2개."""
    records = [
        _basic("S634", "2024-01-10"), _detail("2024-01-10", "초진진찰료"),
        _basic("S634", "2024-06-20"), _detail("2024-06-20", "초진진찰료"),
    ]
    ds, *_ = build_disease_stats(records, TODAY)
    s63 = [k for k in ds if k.startswith("S63")]
    assert len(s63) == 2, f"초진 2회 → 그룹 2개 기대: {s63}"


def test_s_code_one_first_three_revisit_one_group_four_visits():
    """(b) 초진 1회 + 재진 3회 → 그룹 1개, 통원 4회."""
    records = [
        _basic("S634", "2024-01-10"), _detail("2024-01-10", "초진진찰료"),
        _basic("S634", "2024-01-17"), _detail("2024-01-17", "재진진찰료"),
        _basic("S634", "2024-01-24"), _detail("2024-01-24", "재진진찰료"),
        _basic("S634", "2024-01-31"), _detail("2024-01-31", "재진진찰료"),
    ]
    ds, *_ = build_disease_stats(records, TODAY)
    s63 = [k for k in ds if k.startswith("S63")]
    assert len(s63) == 1, f"초진 1회 → 그룹 1개 기대: {s63}"
    assert len(ds[s63[0]]["visit_events"]) == 4, (
        f"통원 4회 기대: {ds[s63[0]]['visit_events']}"
    )


def test_non_s_code_two_first_visits_one_group():
    """(c) 비S코드(M54) 초진 2회 → 그룹 1개 유지(기존 동작)."""
    records = [
        _basic("M544", "2024-01-10", name="요통"), _detail("2024-01-10", "초진진찰료"),
        _basic("M544", "2024-06-20", name="요통"), _detail("2024-06-20", "초진진찰료"),
    ]
    ds, *_ = build_disease_stats(records, TODAY)
    m54 = [k for k in ds if k.startswith("M54")]
    assert len(m54) == 1, f"비S코드는 단일 그룹 유지 기대: {m54}"


def test_s_code_no_first_visit_info_single_group():
    """초진/재진 정보 없는 S코드 → 기존 단일 그룹(하위호환)."""
    records = [_basic("S634", "2024-01-10"), _basic("S634", "2024-06-20")]
    ds, *_ = build_disease_stats(records, TODAY)
    s63 = [k for k in ds if k.startswith("S63")]
    assert len(s63) == 1 and "|" not in s63[0], f"초진정보 없으면 단일 그룹: {s63}"
