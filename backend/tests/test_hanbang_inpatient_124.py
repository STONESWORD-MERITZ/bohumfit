"""BOHUMFIT-124: 자동차보험(한방 포함) 기본진료 PDF의 '진료일수' 컬럼 입원일수 집계 회귀.

자동차 기본진료 PDF는 입원일수를 '내원일수'가 아닌 '진료일수' 컬럼에 둔다.
기존엔 m_days=0 → 입원이 0일로 무시돼 한방(침구과) 입원이 누락됐다.
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.disease_aggregator import build_disease_stats


def _inp_row(code, name, dept, days, date="2026-03-10"):
    # 자동차 기본진료 PDF 컬럼명 그대로(입원/외래·진료일수).
    return {
        "_ftype": "basic",
        "_fname": "auto.pdf",
        "주상병코드": code,
        "주상병명": name,
        "진단과": dept,
        "입원/외래": "입원",
        "진료일수": str(days),
        "진료시작일": date,
        "병·의원&약국": "○○한방병원",
    }


def test_hanbang_inpatient_counted_from_jindays():
    """한방(BS134) 침구과 입원 3일이 '진료일수' 컬럼에서 집계돼야 한다."""
    today = datetime(2026, 6, 25)
    records = [
        _inp_row("AS134", "(양방)경추의 염좌및긴장", "가정의학과", 0),  # 0일 입원은 무시
        _inp_row("BS134", "(한방)경추의 염좌및긴장", "침구과", 3),       # 3일 입원
    ]
    ds, *_ = build_disease_stats(records, today)
    # 양방 A·한방 B 접두는 normalize_code에서 제거 → 둘 다 S134 → 그룹 S13
    s = ds.get("S13")
    assert s is not None, f"S13 그룹 누락: keys={list(ds.keys())}"
    assert s["inpatient_dates"], "한방 입원이 입원일수로 집계되지 않음(진료일수 미인식)"
    assert sum(s["_inpatient_days_map"].values()) == 3, (
        f"입원일수 합계 3 기대, 실제 {sum(s['_inpatient_days_map'].values())}"
    )


def test_zero_day_inpatient_still_ignored():
    """진료일수=0 입원 단독은 여전히 무시(BOHUMFIT-061 0일 입원 무시 유지)."""
    today = datetime(2026, 6, 25)
    records = [_inp_row("AS134", "(양방)경추의 염좌및긴장", "정형외과", 0)]
    ds, *_ = build_disease_stats(records, today)
    s = ds.get("S13")
    if s is not None:
        assert not s["inpatient_dates"], "0일 입원이 잘못 집계됨"


def test_normal_hira_naewon_days_unaffected():
    """일반 심평원 '내원일수' 컬럼 통원은 영향 없이 그대로 동작."""
    today = datetime(2026, 6, 25)
    rec = {
        "_ftype": "basic", "_fname": "hira.pdf",
        "주상병코드": "J00", "주상병명": "급성비인두염", "진단과": "이비인후과",
        "입내원구분": "외래", "내원일수": "1", "진료개시일": "2026-03-10",
        "요양기관명": "○○의원",
    }
    ds, *_ = build_disease_stats([rec], today)
    s = ds.get("J00")
    assert s is not None and not s["inpatient_dates"], "외래가 입원으로 오집계"
    assert s["med_dates_basic"].get("2026-03-10") == 1
