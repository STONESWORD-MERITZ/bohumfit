# BOHUMFIT-047 _build_pool q_raw None 방어 회귀 — 익명 합성 픽스처.
#
# 운영 크래시: AI flagged_item 의 duty_question 이 None 이면 result_builder._build_pool 의
#   re.split(r"[,/\s]+", q_raw) 가 TypeError(expected string ... got 'NoneType') 로 전체 분석을
#   죽였다(비결정적 flagged 수·Q3 누락 고착). 한 항목 결함이 전체를 죽이지 않도록 방어한다.
from datetime import datetime

from pipeline.result_builder import build_summary_reports
from pipeline.disease_aggregator import new_disease

TODAY = datetime(2026, 6, 15)
PRODUCT = "건강체/표준체 (일반심사)"
Q2 = "[2번질문] 1년 이내 진단 (추가검사·재검사 의심 소견)"
Q3 = "[3번질문] 5년 이내 입원·수술·통원·투약"


def _stats_with_visit(code, name, dates):
    s = new_disease()
    s["diag_code"] = code
    s["name"] = name
    for d in dates:
        s["visit_dates"].add(d)
        s["visit_events"].append(d)
    s["first_date"] = min(dates)
    s["latest_date"] = max(dates)
    return {code: s}


def _code_item(code, name, q, rule_id, date, **kw):
    it = {"code": code, "disease": name, "duty_question": q, "_rule_id": rule_id,
          "_source": "code", "date": date, "reason": f"{rule_id}", "hospital": "OO의원",
          "weight": 1, "visit_count": kw.get("visit_count", 0), "med_days": kw.get("med_days", 0)}
    it.update(kw)
    return it


# ── ① q_raw=None 인 AI 항목이 섞여도 크래시 없이 나머지 정상 처리 ──────────
def test_ai_item_with_none_q_does_not_crash():
    ds = _stats_with_visit("M75", "근막통증", [f"2025-{m:02d}-05" for m in range(1, 8)])
    code_items = [_code_item("M75", "근막통증", "Q3", "R-H-Q3-VISIT-7",
                             "2025-07-05", visit_count=7)]
    # AI 항목: duty_question 이 None / 누락 / 빈문자열 — 어느 것도 크래시하면 안 됨.
    ai_result = {"flagged_items": [
        {"code": "K20", "disease": "역류성식도염", "duty_question": None, "_source": "ai", "date": "2025-06-01"},
        {"code": "K21", "disease": "위염", "_source": "ai", "date": "2025-06-01"},  # 키 누락
        {"code": "K22", "disease": "식도질환", "duty_question": "", "_source": "ai", "date": "2025-06-01"},
    ]}
    std, _e, _f, _m = build_summary_reports(ds, code_items, [], ai_result, PRODUCT, TODAY)
    # 크래시 없이 결정론 Q3 항목은 그대로 유지.
    assert Q3 in std and any(r["code"] == "M75" for r in std[Q3])


# ── ② 정상 q="Q2" AI 항목은 그대로 유지(방어가 정상 항목을 버리지 않음) ──────
def test_valid_ai_q2_item_preserved():
    ds = _stats_with_visit("J32", "부비동염", ["2026-03-01"])  # Q2 1년 창 이내
    ai_result = {"flagged_items": [
        {"code": "J32", "disease": "부비동염", "duty_question": "Q2", "_source": "ai",
         "date": "2026-03-01", "q2_suspicion": "추가검사 의심"},
        {"code": "J33", "disease": "비용종", "duty_question": None, "_source": "ai", "date": "2026-03-01"},
    ]}
    std, _e, _f, _m = build_summary_reports(ds, [], [], ai_result, PRODUCT, TODAY)
    assert Q2 in std and any(r["code"] == "J32" for r in std[Q2])


# ── ③ 결정론 항목 q=None 이면 skip(경고)하되 전체는 살아있음 ───────────────
def test_code_item_with_none_q_skipped_not_crash():
    ds = _stats_with_visit("M75", "근막통증", [f"2025-{m:02d}-05" for m in range(1, 8)])
    good = _code_item("M75", "근막통증", "Q3", "R-H-Q3-VISIT-7", "2025-07-05", visit_count=7)
    bad  = _code_item("K30", "소화불량", None, "R-H-BROKEN", "2025-06-01")  # q=None 결정론
    std, _e, _f, _m = build_summary_reports(ds, [good, bad], [], {}, PRODUCT, TODAY)
    assert Q3 in std and any(r["code"] == "M75" for r in std[Q3])
    assert all(r["code"] != "K30" for rows in std.values() for r in rows)  # 결함 항목은 빠짐


# ── ④ 결정성: 동일 입력 반복 → 동일 결과 ───────────────────────────────────
def test_determinism_with_none_items():
    ds = _stats_with_visit("M75", "근막통증", [f"2025-{m:02d}-05" for m in range(1, 8)])
    ci = [_code_item("M75", "근막통증", "Q3", "R-H-Q3-VISIT-7", "2025-07-05", visit_count=7)]
    ai = {"flagged_items": [{"code": "K20", "disease": "x", "duty_question": None, "_source": "ai", "date": "2025-06-01"}]}

    def snap():
        std, _e, _f, _m = build_summary_reports(ds, ci, [], ai, PRODUCT, TODAY)
        return sorted((s, r["code"]) for s, rows in std.items() for r in rows)

    assert snap() == snap()
