# BOHUMFIT-062 비수술 코드 수술 오분류 제외 — 회귀(익명/합성).
from datetime import datetime
from pipeline.helpers import _is_surgery_match
from pipeline.disease_aggregator import _is_detail_surgery_match, build_disease_stats
from pipeline.surgery_exclusions import is_non_surgery_excluded, is_non_surgery_action

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


# ── BOHUMFIT-104: 부목/캐스트(깁스) 처치 수술 오분류 제외 ──────────────────────
CAST_NON_SURGERY = [
    "부목-단하지[하퇴로부터 족부까지]",
    "부목-장하지",
    "STARFIX LIGHT",
    "캐스트",
    "깁스",
    "석고붕대",
    "스플린트",
]


def test_cast_splint_not_surgery():
    """부목·캐스트(깁스)·STARFIX 처치는 수술 아님(강수술 신호 없음)."""
    for n in CAST_NON_SURGERY:
        assert is_non_surgery_action(n) is True, n
        assert _is_detail_surgery_match(n) is False, n
        assert _is_surgery_match(n) is False, n


def test_real_reduction_surgery_still_detected():
    """진짜 정복술/고정술은 강수술 신호로 유지(부목이 함께 있어도 수술로 본다)."""
    for n in ["관혈적정복술", "도수정복술", "골절고정술", "부목고정 후 관혈적정복술"]:
        assert is_non_surgery_action(n) is False, n  # 강수술 신호 → 비수술로 빠지지 않음


def test_cast_category_detail_not_aggregated_as_surgery():
    """재현: 처치및수술 컬럼='캐스트', 진료내역='부목-단하지…' → 수술 미집계."""
    recs = [
        {"진료개시일": "2024-06-07", "요양기관명": "본정형외과의원", "입내원구분": "외래", "요양일수": "1",
         "상병코드": "S825", "상병명": "하퇴의 골절", "_ftype": "basic"},
        {"진료개시일": "2024-06-07", "요양기관명": "본정형외과의원", "입내원구분": "외래", "요양일수": "1",
         "처치및수술": "캐스트", "진료내역": "부목-단하지[하퇴로부터 족부까지]", "_ftype": "detail"},
    ]
    st, *_ = build_disease_stats(recs, datetime(2026, 6, 15))
    assert all(not s.get("surgeries") and not s.get("surgery_dates") for s in st.values())


# ── BOHUMFIT-106: 이학요법(물리치료) 계열 수술 오분류 제외 ──────────────────────
PHYSIO_NON_SURGERY = [
    "한냉치료(냉동치료)",
    "이학요법료/이학요법(양방)",
    "표층열치료", "심층열치료", "온열치료", "초단파치료", "적외선치료",
    "간섭파전류치료(ICT)", "전기자극치료", "재활저출력레이저치료",
    "도수치료", "운동치료", "견인치료",
    "좌욕", "산소흡입", "도뇨", "창상처치", "냉찜질",
]


def test_physiotherapy_not_surgery():
    """이학요법(한냉/온열/도수/견인 등) 처치는 수술 아님(강수술 신호 없음)."""
    for n in PHYSIO_NON_SURGERY:
        assert is_non_surgery_action(n) is True, n
        assert _is_detail_surgery_match(n) is False, n
        assert _is_surgery_match(n) is False, n


def test_real_surgery_not_masked_by_physio_keywords():
    """진짜 수술(냉동수술·냉동절제술·레이저절제술)은 강수술 신호로 그대로 유지."""
    for n in ["냉동수술", "냉동절제술", "레이저절제술", "관절경하활막절제술"]:
        assert is_non_surgery_action(n) is False, n  # 강수술 신호 → 비수술로 빠지지 않음


def test_cryotherapy_category_detail_not_aggregated_as_surgery():
    """재현: 처치및수술='한냉치료(냉동치료)', 진료내역='이학요법료/이학요법(양방)' → 수술 미집계."""
    recs = [
        {"진료개시일": "2024-06-07", "요양기관명": "본정형외과의원", "입내원구분": "외래", "요양일수": "1",
         "상병코드": "S93", "상병명": "발목의 염좌", "_ftype": "basic"},
        {"진료개시일": "2024-06-07", "요양기관명": "본정형외과의원", "입내원구분": "외래", "요양일수": "1",
         "처치및수술": "한냉치료(냉동치료)", "진료내역": "이학요법료/이학요법(양방)", "_ftype": "detail"},
    ]
    st, *_ = build_disease_stats(recs, datetime(2026, 6, 15))
    assert all(not s.get("surgeries") and not s.get("surgery_dates") for s in st.values())
