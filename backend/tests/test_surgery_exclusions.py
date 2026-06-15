# BOHUMFIT-062 비수술 코드 수술 오분류 제외 — 회귀(익명/합성).
from datetime import datetime
from pipeline.helpers import _is_surgery_match
from pipeline.disease_aggregator import _is_detail_surgery_match, build_disease_stats
from pipeline.surgery_exclusions import is_non_surgery_excluded

EXCLUDED = [
    "수액제주입로를통한주사",
    "치관수복물또는보철물의 제거[1치당]-간단한것",
    "치관수복물또는보철물의 제거[1치당]-복잡한것",
    "후두내주입",
]
REAL_SURGERY = ["비용적출술", "하비갑개점막하절제술", "충수절제술", "백내장수술"]


def test_excluded_not_surgery_anyfunc():
    for n in EXCLUDED:
        assert is_non_surgery_excluded(n)
        assert _is_surgery_match(n) is False, n
        assert _is_detail_surgery_match(n) is False, n


def test_excluded_robust_to_spacing():
    assert _is_surgery_match("수액제주입로를 통한 주사") is False
    assert _is_detail_surgery_match("치관수복물또는보철물의제거[1치당]-복잡한것") is False


def test_real_surgery_still_detected():
    for n in REAL_SURGERY:
        assert (_is_surgery_match(n) or _is_detail_surgery_match(n)) is True, n


def test_excluded_detail_not_aggregated():
    # 같은날·같은 기관 basic+detail → detail 처치명이 제외 대상이면 surgery 미집계
    recs = [
        {"진료개시일": "2024-03-10", "요양기관명": "OO치과", "입내원구분": "외래", "요양일수": "1",
         "상병코드": "K029", "상병명": "치아우식", "_ftype": "basic"},
        {"진료개시일": "2024-03-10", "요양기관명": "OO치과", "입내원구분": "외래", "요양일수": "1",
         "진료내역": "치관수복물또는보철물의 제거[1치당]-간단한것", "_ftype": "detail"},
    ]
    st, *_ = build_disease_stats(recs, datetime(2026, 6, 15))
    assert all(not s.get("surgeries") and not s.get("surgery_dates") for s in st.values())
