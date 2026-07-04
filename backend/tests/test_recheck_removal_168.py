"""BOHUMFIT-168: 추가검사/재검사 소견(exam_check_only) 항목을 분석 결과에서 완전 제거.

- (a) 소견만 있는 항목            → 결과에서 제외
- (b) 소견 + 실제 치료/수술 병존   → 병력 유지, 소견 관련 필드만 비움
- (c) 소견 없는 기존 항목          → 불변
"""
import copy
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.result_builder import _strip_exam_check_only_reports

Q2 = "[2번질문] 1년 이내 진단 (추가검사·재검사 의심 소견)"
Q3 = "[3번질문] 5년 이내 입원·수술·통원·투약"


def _item(**kw):
    base = {
        "code": "J30", "name": "알레르기비염",
        "exam_check_only": False,
        "inpatient": 0, "inpatient_count": 0,
        "surgeries": set(), "surgery_count": 0, "surgery_suspected": [],
        "med_days": 0, "treatment_ongoing": None,
        "q2_suspicion": "", "additional_test_hit": False,
        "additional_test_reason": "", "additional_tests": [],
        "visit": 2, "first_date": "2025-05-01", "latest_date": "2025-06-01",
    }
    base.update(kw)
    return base


def test_a_exam_only_removed_general_kept():
    """(a) 소견만 있는 항목은 제외, 소견 무관 일반 항목은 유지."""
    reports = {Q2: [
        _item(code="J30", name="알레르기비염", exam_check_only=True,
              q2_suspicion="재검사 의심", additional_test_hit=True,
              additional_test_reason="추적검사 권유"),
        _item(code="K05", name="치주염", exam_check_only=False, med_days=5),
    ]}
    out = _strip_exam_check_only_reports(reports)
    names = [i["name"] for i in out[Q2]]
    assert "알레르기비염" not in names, "소견만 있는 항목은 결과에서 제외돼야 함"
    assert "치주염" in names, "소견 무관 일반 항목은 유지돼야 함"


def test_b_exam_with_treatment_kept_fields_cleared():
    """(b) 소견 + 실제 치료(투약·치료지속) 병존 → 병력 유지, 소견 필드만 비움."""
    reports = {Q2: [
        _item(code="E11", name="당뇨병", exam_check_only=True,
              q2_suspicion="재검사 의심", additional_test_hit=True,
              additional_test_reason="추적검사", additional_tests=["재검사"],
              med_days=60, treatment_ongoing=True),
    ]}
    out = _strip_exam_check_only_reports(reports)
    kept = out[Q2]
    assert len(kept) == 1 and kept[0]["name"] == "당뇨병", "실제 근거 병존 항목은 유지돼야 함"
    it = kept[0]
    assert it["exam_check_only"] is False
    assert it["q2_suspicion"] == ""
    assert it["additional_test_hit"] is False
    assert it["additional_test_reason"] == ""
    assert it["additional_tests"] == []
    # 실제 근거 필드는 보존
    assert it["med_days"] == 60 and it["treatment_ongoing"] is True


def test_b2_exam_with_surgery_kept():
    """(b) 변형: 소견 + 수술 병존 → 항목 유지, 소견 필드 제거, 수술 근거 보존."""
    reports = {Q2: [
        _item(code="M51", name="추간판탈출", exam_check_only=True,
              q2_suspicion="재검사 의심", surgeries={"수술"}, surgery_count=1),
    ]}
    out = _strip_exam_check_only_reports(reports)
    assert len(out[Q2]) == 1
    it = out[Q2][0]
    assert it["exam_check_only"] is False and it["q2_suspicion"] == ""
    assert it["surgeries"] == {"수술"} and it["surgery_count"] == 1


def test_c_no_exam_unchanged():
    """(c) 소견 없는 기존 케이스는 완전히 불변(항목·필드 모두)."""
    reports = {
        Q2: [_item(code="K05", name="치주염", exam_check_only=False, med_days=10)],
        Q3: [_item(code="I10", name="고혈압", exam_check_only=False, med_days=90)],
    }
    before = copy.deepcopy(reports)
    out = _strip_exam_check_only_reports(reports)
    assert [i["name"] for i in out[Q2]] == [i["name"] for i in before[Q2]]
    assert [i["name"] for i in out[Q3]] == [i["name"] for i in before[Q3]]
    assert out[Q3][0]["med_days"] == 90 and out[Q3][0]["exam_check_only"] is False
