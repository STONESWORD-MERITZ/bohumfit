"""BOHUMFIT-183 — 투약 배지 산식 표기 보강(표시 전용).

★핵심 가드: ①산식(`filters._sum_daily_max_presc`)이 바뀌지 않았을 것
②PDF 각주·카카오 축약문이 **투약이 있을 때만** 나올 것 ③프런트 상수와 문자열이 완전히 같을 것.
"""
import re
from datetime import date, datetime
from pathlib import Path

import pytest

from filters import _sum_daily_max_presc
from main import _build_kakao_message
from pipeline.report_pdf import MED_SUM_FORMULA_NOTE, MED_SUM_FORMULA_NOTE_SHORT

ROOT = Path(__file__).resolve().parents[2]


# ── ★산식 무변경 ───────────────────────────────────────────────────────────
def test_daily_max_sum_formula_unchanged():
    """날짜별 최대 처방일수의 누적 합 — 030→031/032에서 의도적으로 채택된 설계 그대로."""
    # ★실측한 실제 구조: 날짜 → (기관별 dict | 스칼라). 리스트가 아니다.
    med = {
        "2024-01-10": {"약국A": 30, "약국B": 7},  # 같은 날 복수 처방 → 최장 1건(30)만
        "2024-02-05": 14,                          # 스칼라도 지원
        "2024-03-01": {"약국A": 10, "약국B": 10},  # 동값 복수 → 1건만
    }
    # 내부 `_parse_ymd`가 datetime을 만드므로 기준도 datetime이어야 한다(실측으로 확인).
    since = datetime(2020, 1, 1)
    assert _sum_daily_max_presc(med, since) == 30 + 14 + 10
    # 창(window) 밖 날짜는 합산되지 않는다 — 창 규칙도 그대로임을 함께 고정.
    assert _sum_daily_max_presc(med, datetime(2024, 2, 1)) == 14 + 10


def test_filters_module_has_no_183_edit():
    """★`filters.py`에 183 흔적이 없어야 한다(산식 파일 무변경 계약)."""
    src = (ROOT / "backend" / "filters.py").read_text(encoding="utf-8")
    assert "183" not in src
    assert "MED_SUM_FORMULA" not in src


# ── 문구 계약 ──────────────────────────────────────────────────────────────
def test_note_matches_frontend_constant():
    """★프런트 `disclosureWindow.ts`의 상수와 **문자열이 완전히 같아야** 한다.

    언어가 달라 한 곳에 둘 수 없으므로(251 선례) 동일성을 여기서 고정한다.
    """
    ts = (ROOT / "src" / "lib" / "disclosureWindow.ts").read_text(encoding="utf-8")
    m = re.search(r'export const MED_SUM_FORMULA_NOTE = "([^"]+)"', ts)
    assert m, "프런트 상수를 찾지 못했다"
    assert m.group(1) == MED_SUM_FORMULA_NOTE


def test_note_wording_is_the_confirmed_one():
    """확정 문구 그대로(임의 변경 금지)."""
    assert MED_SUM_FORMULA_NOTE == "동일 날짜에 여러 처방이 있으면 가장 긴 처방일수 1건만 반영한 합계입니다."
    assert MED_SUM_FORMULA_NOTE_SHORT == "※ 같은 날 복수 처방은 최장 1건만 반영"


# ── 카카오 복사문 ──────────────────────────────────────────────────────────
def _reports(med_days: int) -> dict:
    return {
        "3번 질문: 5년 이내 입원/수술/7회이상통원/30일이상투약": [
            {
                "name": "고혈압",
                "code": "I10",
                "med_days": med_days,
                "visit": 3,
                "inpatient": 0,
                "detail": f"투약 {med_days}일" if med_days else "통원 3회",
            }
        ]
    }


def test_kakao_appends_short_note_when_med_present():
    msg = _build_kakao_message("건강체", date(2026, 8, 2), _reports(1002))
    assert MED_SUM_FORMULA_NOTE_SHORT in msg
    # ★말미에 1줄만 — 기존 구조·순서는 그대로다.
    assert msg.count(MED_SUM_FORMULA_NOTE_SHORT) == 1
    assert msg.index(MED_SUM_FORMULA_NOTE_SHORT) > msg.index("고혈압")


def test_kakao_omits_note_when_no_med():
    msg = _build_kakao_message("건강체", date(2026, 8, 2), _reports(0))
    assert MED_SUM_FORMULA_NOTE_SHORT not in msg


def test_kakao_omits_note_when_no_items():
    msg = _build_kakao_message("건강체", date(2026, 8, 2), {})
    assert "고지 대상 없음" in msg
    assert MED_SUM_FORMULA_NOTE_SHORT not in msg


def test_kakao_header_unchanged():
    """기존 메시지 머리·구조가 바뀌지 않았다."""
    msg = _build_kakao_message("건강체", date(2026, 8, 2), _reports(1002))
    assert msg.startswith("[건강체 고지 사항]\n기준일: 2026-08-02\n\n")


# ── 리포트 PDF 템플릿 ──────────────────────────────────────────────────────
def test_pdf_template_shows_note_only_with_med():
    """각주는 `total_med_sum`이 있을 때만 렌더되도록 조건이 걸려 있다."""
    html = (ROOT / "backend" / "templates" / "report_disclosure.html").read_text(encoding="utf-8")
    assert "med_formula_note" in html
    block = html[html.index("med_formula_note") - 220 : html.index("med_formula_note")]
    assert "total_med_sum is not none" in block


@pytest.mark.parametrize("total_med_sum, expected", [(1002, True), (None, False)])
def test_pdf_context_carries_note(total_med_sum, expected):
    """렌더 컨텍스트에 상수가 실려 나가고, 투약이 없으면 각주 조건이 거짓이 된다."""
    from pipeline.report_pdf import render_disclosure_html

    payload = {
        "standard_reports": {},
        "easy_reports": {},
        "all_disease_summary": [],
        "total_med_sum": total_med_sum,
    }
    html = render_disclosure_html(payload, __import__("datetime").datetime(2026, 8, 2))
    assert (MED_SUM_FORMULA_NOTE in html) is expected
