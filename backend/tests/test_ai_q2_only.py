# BOHUMFIT-038 AI 역할 Q2 한정 + Q5 중대질병 결정론 코드매칭 회귀 — 익명 합성(PII 없음).
from datetime import datetime, timedelta

from filters import build_code_based_items, PRODUCT_HEALTH
from pipeline.disease_aggregator import new_disease
from pipeline.result_builder import build_summary_reports

TODAY = datetime(2026, 6, 15)
REF = datetime(2026, 6, 15)
Q2_TITLE = "[2번질문] 1년 이내 진단 (추가검사·재검사 의심 소견)"
Q4_TITLE = "[4번질문] 5년 초과 10년 이내 입원·수술"
Q5_TITLE = "[5번질문] 5년 이내 10대질환"


def _ymd(n):
    return (TODAY - timedelta(days=n)).strftime("%Y-%m-%d")


def mk(code, name, visits=None, inpatient=None):
    s = new_disease()
    s["diag_code"] = code
    s["name"] = name
    for d in (visits or []):
        s["visit_dates"].add(d); s["visit_events"].append(d)
    for d in (inpatient or []):
        s["inpatient_dates"].add(d); s["inpatient_admissions"].add((d, "OO병원")); s["_inpatient_days_map"][d] = 5
    alld = sorted((visits or []) + (inpatient or []))
    s["first_date"] = alld[0] if alld else "2099-12-31"
    s["latest_date"] = alld[-1] if alld else "2000-01-01"
    return s


def _std(ds, health_items, ai_flagged):
    std, easy, fl, mg = build_summary_reports(
        ds, health_items, [], {"flagged_items": ai_flagged}, "건강체", TODAY)
    return std


def _codes_in(std, title):
    return {r["code"] for r in std.get(title, [])}


# ── ★ AI가 중대질병을 Q4로 내도 누수 0 (E78, 목록 밖) ────────────────────
def test_ai_q4_major_disease_dropped():
    ds = {"E78": mk("E78", "고지혈증", visits=[_ymd(100)])}
    ai = [{"code": "E78", "disease": "고지혈증", "duty_question": "Q4",
           "reason": "중대질병 확정진단", "_source": "ai", "date": _ymd(100)}]
    std = _std(ds, [], ai)
    assert "E78" not in _codes_in(std, Q4_TITLE)   # Q4(입원·수술)에 안 뜸
    assert "E78" not in _codes_in(std, Q5_TITLE)   # Q5에도 안 뜸(목록 밖)
    assert all("E78" not in _codes_in(std, t) for t in std)  # 어떤 질문에도 없음


# ── ★ AI가 임의 코드를 Q5/Q3로 내도 누수 0 ───────────────────────────────
def test_ai_non_q2_dropped_general():
    ds = {"I10": mk("I10", "고혈압", visits=[_ymd(50)])}
    ai = [{"code": "I10", "disease": "고혈압", "duty_question": "Q5", "reason": "중대질병",
           "_source": "ai", "date": _ymd(50)}]
    std = _std(ds, [], ai)
    # AI발 I10(Q5)은 머지 안 됨(아래 결정론 Q5와 구분 위해 health_items 비움)
    assert "I10" not in _codes_in(std, Q5_TITLE)


# ── BOHUMFIT-168: 소견만 있는 AI Q2(추가검사·재검사)는 결과에서 제거 ──────
def test_ai_q2_suspicion_only_removed():
    """BOHUMFIT-168: 소견만 있고 다른 근거 없는 AI Q2 항목은 결과에서 완전 제거.
    (구 BOHUMFIT-038 test_ai_q2_kept — Q2 소견 표시 스펙 폐지)."""
    ds = {"K29": mk("K29", "위염", visits=[_ymd(60)])}
    ai = [{"code": "K29", "disease": "위염", "duty_question": "Q2",
           "reason": "1년이내 확정진단", "q2_suspicion": "위내시경 재검 권고",
           "_source": "ai", "date": _ymd(60)}]
    std = _std(ds, [], ai)
    assert "K29" not in _codes_in(std, Q2_TITLE)    # 소견만 → 결과에서 제거(168)


# ── ★ Q5 중대질병 = 결정론 코드매칭만(I10→Q5, E78→Q5 미표시) ─────────────
def test_q5_deterministic_codematch_only():
    ds = {"I10": mk("I10", "고혈압", visits=[_ymd(100)]),
          "E78": mk("E78", "고지혈증", visits=[_ymd(100)])}
    items = build_code_based_items(ds, REF, PRODUCT_HEALTH)   # 결정론(AI 없음)
    std = _std(ds, items, [])
    q5 = _codes_in(std, Q5_TITLE)
    assert "I10" in q5            # 목록 코드 → Q5
    assert "E78" not in q5        # 목록 밖 → Q5 미표시(과분류 차단)


# ── 결정성 ───────────────────────────────────────────────────────────────
def test_determinism():
    ds = {"E78": mk("E78", "고지혈증", visits=[_ymd(100)])}
    ai = [{"code": "E78", "disease": "고지혈증", "duty_question": "Q4",
           "reason": "중대질병", "_source": "ai", "date": _ymd(100)}]
    a = {k: sorted(_codes_in(_std(ds, [], ai), k)) for k in [Q2_TITLE, Q4_TITLE, Q5_TITLE]}
    b = {k: sorted(_codes_in(_std(ds, [], ai), k)) for k in [Q2_TITLE, Q4_TITLE, Q5_TITLE]}
    assert a == b
