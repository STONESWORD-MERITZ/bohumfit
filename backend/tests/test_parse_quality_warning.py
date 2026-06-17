# BOHUMFIT-054 STEP2 파싱 불완전(ftype 미인식 과다) 사용자 경고 회귀.
#
# _2 파일이 basic 소수로 조용히 깨졌듯, ftype 분류가 비정상이어도 errors=0이면 사용자가 모름.
# record_counts 기반으로 unknown 비율이 비정상 높을 때만(보수적) 경고 메시지를 낸다. 분석은 막지 않음.
from analyzer import _parse_quality_warning


# ── 정상 파싱 → 경고 없음 ─────────────────────────────────────────────────
def test_normal_no_warning():
    assert _parse_quality_warning({"basic": 38, "detail": 171, "pharma": 129}) is None
    assert _parse_quality_warning({"nhis": 22}) is None


# ── unknown 다수(깨진 케이스) → 경고 ON ───────────────────────────────────
def test_unknown_heavy_warns():
    msg = _parse_quality_warning({"unknown": 12, "basic": 2})   # 12/14 ≈ 0.86
    assert msg and "정상적으로 인식되지" in msg


# ── 경계: unknown 5건 이상 + 30% 이상만 경고(오탐 억제) ───────────────────
def test_threshold_conservative():
    assert _parse_quality_warning({"unknown": 3, "basic": 100}) is None   # 3건 <5 → 경고 안 함
    assert _parse_quality_warning({"unknown": 5, "basic": 11}) is not None  # 5/16=0.31 ≥0.3
    assert _parse_quality_warning({"unknown": 5, "basic": 12}) is None      # 5/17=0.29 <0.3


# ── 빈/None 안전 ─────────────────────────────────────────────────────────
def test_empty_safe():
    assert _parse_quality_warning({}) is None
    assert _parse_quality_warning(None) is None
