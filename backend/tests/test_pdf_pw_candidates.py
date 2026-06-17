# BOHUMFIT-053 PDF 비번 8/6자리 자동 해제 후보 로직 회귀.
#
# 발급기간별 비번 자리수 상이(0~5년=8자리, 5~10년=6자리 YYMMDD). 사용자는 8자리만 입력해도
# 6자리 PDF가 자동 재시도로 풀려야 한다. 빈 비번·6자리 직접 입력·하이픈 입력도 안전 동작.
from pipeline.pdf_parser import _pw_candidates


# ── ① 8자리 입력 → 8자리 그대로 + 뒤 6자리(YYMMDD) 자동 포함 ─────────────
def test_8digit_includes_6digit_fallback():
    c = _pw_candidates("19950222")
    assert "19950222" in c and "950222" in c
    assert c.index("19950222") < c.index("950222")   # 8자리 먼저 시도
    assert c[0] == ""                                 # 비번 불요 PDF 우선


# ── ② 6자리 직접 입력 → 6자리 + 8자리 보강 ───────────────────────────────
def test_6digit_input_adds_8digit():
    c = _pw_candidates("950222")
    assert "950222" in c and "19950222" in c          # 95 → 19xx


def test_6digit_recent_year_prefix_20():
    c = _pw_candidates("050222")                       # 05 → 2005
    assert "20050222" in c


# ── ③ 하이픈 포함 입력 → 숫자만 + 6자리 폴백 ─────────────────────────────
def test_hyphenated_input_normalized():
    c = _pw_candidates("1995-02-22")
    assert "19950222" in c and "950222" in c


# ── ④ 빈 비번(비번 불요 PDF) → 빈 문자열만 ───────────────────────────────
def test_empty_input():
    assert _pw_candidates("") == [""]
    assert _pw_candidates(None) == [""]


# ── ⑤ 중복 제거 + 순서 안정(빈값→입력→숫자→자리수변환) ───────────────────
def test_dedup_and_order():
    c = _pw_candidates("19950222")
    assert len(c) == len(set(c))                       # 중복 없음
    assert c[0] == ""
