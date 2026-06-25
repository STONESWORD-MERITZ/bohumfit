"""BOHUMFIT-125: 진료기간 종료일은 창과 무관한 실제 최종진료일로 표시(건강체/간편 통일).

버그: 동일 질병 S63이 건강체 Q4(범위창 상한 d5y)에서는 종료일이 창에 잘려
2018-06-20~2018-06-21로, 간편 Q2(상한 없음)에서는 2018-06-20~2021-07-20로 달랐다.
확정 스펙: 창 판정(고지 대상 여부)은 현행 유지, 진료기간 표시 종료일은 실제 최종진료일.
(스펙 3번 '최초진단일 창 밖이면 고지 제외'는 고지 질문 의미와 충돌하여 사용자 결정으로 미적용.)
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.disease_aggregator import build_disease_stats
from pipeline.result_builder import build_summary_reports
from filters import build_code_based_items, PRODUCT_HEALTH, PRODUCT_EASY

TODAY = datetime(2026, 6, 25)


def _rec(io, days, date, col="진료일수"):
    # 자동차/한방 기본진료 PDF 컬럼 모사(입원/외래·진료일수). S634 → 그룹 S63.
    r = {
        "_ftype": "basic", "_fname": "x.pdf",
        "주상병코드": "S634", "주상병명": "손목부위의 염좌 및 긴장",
        "진단과": "정형외과", "병·의원&약국": "A병원", "진료시작일": date,
    }
    r["입원/외래"] = io
    r[col] = str(days)
    return r


def _build():
    # 입원 2018-06-20(5~10년 창) + 통원 2021-07-20(5년 창·실제 최종진료일)
    records = [_rec("입원", 2, "2018-06-20"), _rec("외래", 1, "2021-07-20", "내원일수")]
    ds, *_ = build_disease_stats(records, TODAY)
    std, easy, _f, _m = build_summary_reports(
        ds,
        build_code_based_items(ds, TODAY, PRODUCT_HEALTH),
        build_code_based_items(ds, TODAY, PRODUCT_EASY),
        {}, PRODUCT_HEALTH, TODAY,
    )
    return std, easy


def _s63(reports, qfrag):
    return [r for qt, rows in reports.items() for r in rows
            if r["code"] == "S63" and qfrag in qt]


def test_period_end_is_actual_last_even_when_window_clips():
    """(a) first_date 창 안 + last_date가 범위창(Q4 상한) 밖이어도 종료일=실제 최종진료일."""
    std, _ = _build()
    q4 = _s63(std, "4번질문")
    assert q4, "건강체 Q4에 S63가 표시되지 않음"
    assert q4[0]["first_date"] == "2018-06-20"
    assert q4[0]["latest_date"] == "2021-07-20", (
        f"종료일이 창에 잘림(실제 최종진료일 2021-07-20 기대): {q4[0]['latest_date']}"
    )


def test_health_and_easy_show_same_period():
    """(c) 동일 질병 S63 진료기간이 건강체/간편에서 동일."""
    std, easy = _build()
    h = _s63(std, "4번질문")[0]
    e = _s63(easy, "2번질문")[0]
    assert (h["first_date"], h["latest_date"]) == ("2018-06-20", "2021-07-20")
    assert (e["first_date"], e["latest_date"]) == ("2018-06-20", "2021-07-20")
    assert (h["first_date"], h["latest_date"]) == (e["first_date"], e["latest_date"])
