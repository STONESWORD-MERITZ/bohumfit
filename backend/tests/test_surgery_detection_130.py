"""BOHUMFIT-130: 수술 감지 강화 회귀.

수술X(제외): 약물/비수술적 소작술·신경차단술. 수술O(포함): 유치카테터(유치도뇨관)·냉각응고술·성형술.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.surgery_exclusions import is_non_surgery_excluded, is_non_surgery_action
from pipeline.disease_aggregator import _is_detail_surgery_match


# ── (a) 수술X 확정 항목: 수술로 집계되지 않아야 한다 ──────────────────────────
def test_cauterization_and_nerve_block_excluded():
    for name in [
        "자궁경부약물소작술", "갑개소작술", "비인강소작술", "인후두소작술",
        "신경차단술", "신경차단",
    ]:
        assert is_non_surgery_excluded(name), f"{name} 수술 제외 실패"
        assert not _is_detail_surgery_match(name), f"{name} 수술로 오감지"


# ── (b) 수술O 확정 항목: 수술로 정상 집계돼야 한다 ───────────────────────────
def test_indwelling_catheter_and_others_detected():
    for name in [
        "유치카테터", "유치도뇨관", "티눈 냉각응고술", "후궁성형술", "신경성형술",
    ]:
        assert not is_non_surgery_excluded(name), f"{name} 잘못 제외됨"
        assert _is_detail_surgery_match(name), f"{name} 수술 미감지"


# ── (c) 기존 확실한 수술은 여전히 정상 감지 ──────────────────────────────────
def test_known_surgeries_still_detected():
    for name in ["도수정복술", "관혈적정복술", "창상봉합술", "충수절제술", "백내장수술"]:
        assert _is_detail_surgery_match(name), f"{name} 기존 수술 감지 실패"


# ── (d) 기존 비수술 처치는 여전히 제외(104·106 회귀 불변) ────────────────────
def test_known_non_surgery_still_excluded():
    for name in ["단순도뇨", "한냉치료", "부목-단하지", "물리치료", "관절강내주사"]:
        assert is_non_surgery_excluded(name), f"{name} 비수술 제외 실패"
        assert not _is_detail_surgery_match(name), f"{name} 수술로 오감지"


# ── 보강: 강수술 신호가 함께 있으면 소작이라도 수술 유지(누락 0) ─────────────
def test_strong_signal_overrides_cauterization():
    # '절제'(강신호)가 있으면 '소작' 제외에 걸리지 않는다.
    assert not is_non_surgery_action("종양소작절제술"), "강신호(절제) override 실패"
