"""summary_reports 빌드 — analyzer.py 에서 이동."""
from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)

from filters import _q3_med_since, _sum_daily_max_presc, INSURANCE_ONLY_Q5_CODES  # BOHUMFIT-031/032/039
from .helpers import (
    _dts_in_range,
    _dts_in_window,
    _inpatient_end_dates_in_range,
    _inpatient_periods_in_range,
    _max_presc,
    _parse_ymd,
    _sorted_strings,
    _subtract_years,
    _visit_count_in_range,
    format_kcd_code,
    normalize_code,
)

# 비-질병 항목 차단용 (merge 단계 이중 안전망)
_KCD_MERGE_RE = re.compile(r"^[A-Z]\d{2,4}[A-Z0-9]?$")
_NON_DISEASE_NAME_PATTERNS_MERGE = (
    "진찰료", "재진", "초진",
    "조제료", "약국관리료", "약제비",
    "응급및회송료", "외래환자의약품관리료",
    "주사료", "주사기료",
    "검사료", "방사선료", "마취료", "이학요법료",
    "처치및수술", "처치 및수술", "처치및 수 술",
    "재료대", "행위료", "기본진료료", "방문당",
)


def _make_merged_item(item: dict, q: str, code_override: str = "") -> dict:
    return {
        "dates":          [item.get("date", "")],
        "code":           code_override or item.get("code", "-"),
        "name":           item.get("disease", ""),
        "duty_question":  q,
        "reason":         item.get("reason", ""),
        "is_inpatient":   item.get("is_inpatient", False),
        "inpatient_days": item.get("inpatient_days", 0),
        "inpatient_count": item.get("inpatient_count", 0),
        "visit_count":    item.get("visit_count", 0),
        "first_diagnosis_date": item.get("first_diagnosis_date", ""),
        "is_surgery":     item.get("is_surgery", False),
        "surgery_name":   item.get("surgery_name"),
        "surgery_dates":  [item.get("date", "")] if item.get("is_surgery") else [],
        "med_days":       item.get("med_days", 0),
        "weight":         item.get("weight", "mid"),
        "hospitals":      [item.get("hospital", "")],
        "q2_suspicion":   item.get("q2_suspicion", ""),
    }


def _merge_item_into(m: dict, item: dict) -> None:
    if item.get("date"):
        m["dates"].append(item.get("date", ""))
    if item.get("reason") and item["reason"] not in m.get("reason", ""):
        m["reason"] = (m.get("reason", "") + " / " + item["reason"]).strip(" /")
    if item.get("is_surgery"):
        m["is_surgery"] = True
        if item.get("date"):
            m["surgery_dates"].append(item.get("date", ""))
        if item.get("surgery_name"):
            m["surgery_name"] = item.get("surgery_name")
    m["inpatient_days"] = max(m["inpatient_days"], item.get("inpatient_days", 0))
    m["inpatient_count"] = max(m["inpatient_count"], item.get("inpatient_count", 0))
    m["visit_count"] = max(m["visit_count"], item.get("visit_count", 0))
    if item.get("first_diagnosis_date") and item["first_diagnosis_date"] < m.get("first_diagnosis_date", "2099-12-31"):
        m["first_diagnosis_date"] = item["first_diagnosis_date"]
    m["med_days"] = max(m["med_days"], item.get("med_days", 0))
    weight_order = {"critical": 4, "high": 3, "mid": 2, "low": 1}
    if weight_order.get(item.get("weight", "low"), 0) > weight_order.get(m["weight"], 0):
        m["weight"] = item.get("weight", "mid")
    if item.get("hospital") and item["hospital"] not in m["hospitals"]:
        m["hospitals"].append(item["hospital"])
    if item.get("q2_suspicion"):
        if item["q2_suspicion"] not in m.get("q2_suspicion", ""):
            m["q2_suspicion"] = (m.get("q2_suspicion", "") + " / " + item["q2_suspicion"]).strip(" /")


def _merged_item_sort_key(entry) -> tuple:
    (code, q), item = entry
    dates = _sorted_strings(item.get("dates", []))
    return (q, code, dates[0] if dates else "", item.get("name", ""))


def _build_reports_for_product(merged_items, disease_stats, product_type, d3m, d1y, d10y, d5y,
                               is_easy: bool = False, q3_med_since=None):
    """merged_items + disease_stats → (summary_reports, flagged_codes).

    BOHUMFIT-BUG-012: 탭별 질문 창(_q_since)·라벨(q_labels)을 분리한다.
    - 건강체: Q1→3개월, Q2→1년(진단·의심 소견), Q3→10년(입원·수술·통원·투약), Q4→5년(10대질환)
    - 간편  : Q1→3개월, Q2→10년(입원·수술), Q3→5년(6대질환)
    간편 Q2 에 건강체 Q2 의 1년 창·의심 소견 라벨을 적용하던 결함(BOHUMFIT-BUG-012)을 끊는다.
    product_type 은 시그니처 호환을 위해 유지하되 라우팅은 is_easy 로 한다.
    """
    _ = product_type

    if is_easy:
        _q_since = {"Q1": d3m, "Q2": d10y, "Q3": d5y}
        _q_until = {}
        q_labels = {
            "Q1": "[1번질문] 3개월 이내 진단·입원·수술·투약",
            "Q2": "[2번질문] 10년 이내 입원·수술",
            "Q3": "[3번질문] 5년 이내 6대질환",
        }
    else:
        # BOHUMFIT-034: Q3=5년, Q4 신설=5년 초과~10년 입원·수술(범위창), 기존 Q4 중대질환→Q5.
        _q_since = {"Q1": d3m, "Q2": d1y, "Q3": d5y, "Q4": d10y, "Q5": d5y}
        _q_until = {"Q4": d5y}   # Q4 상한: 5년 미만 제외 → [d10y, d5y)
        q_labels = {
            "Q1": "[1번질문] 3개월 이내 진단·입원·수술·투약",
            "Q2": "[2번질문] 1년 이내 진단 (추가검사·재검사 의심 소견)",
            "Q3": "[3번질문] 5년 이내 입원·수술·통원·투약",
            "Q4": "[4번질문] 5년 초과 10년 이내 입원·수술",
            "Q5": "[5번질문] 5년 이내 10대질환",
        }

    summary_reports = defaultdict(list)
    flagged_codes   = set()
    seen_pairs      = set()

    for merge_key, m in sorted(merged_items.items(), key=_merged_item_sort_key):
        code_key = m["code"]
        q_orig   = m["duty_question"]
        q = q_orig

        if q not in q_labels:
            continue

        pair = (code_key, q)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)

        q_title  = q_labels[q]
        since_dt = _q_since.get(q, d10y)
        until_dt = _q_until.get(q)   # BOHUMFIT-034: Q4 범위창 상한(없으면 >=since)
        def _win(dates, _since=since_dt, _until=until_dt):
            return _dts_in_window(dates, _since, _until) if _until else _dts_in_range(dates, _since)
        _ds      = disease_stats.get(code_key)

        if _ds:
            _inpatient_end_dates = _inpatient_end_dates_in_range(_ds, since_dt)
            _all_dates   = (
                _ds.get("visit_dates", set())
                | _ds.get("inpatient_dates", set())
                | _inpatient_end_dates
                | _ds.get("surgery_dates", set())
            )
            _in_range    = _win(_all_dates)
            first_date   = _in_range[0]  if _in_range else ""
            # BOHUMFIT-125: 진료기간 '종료일'은 창과 무관한 실제 최종진료일로 표시한다.
            #   기존 _in_range[-1]은 창 필터(특히 Q4 범위창 상한 d5y)에 잘려, 같은 질병이라도
            #   건강체 Q4(상한有)와 간편(상한無)의 진료기간 종료일이 달라지는 버그가 있었다.
            #   확정 스펙: 창 판정은 그대로(고지 대상 여부), 표시 종료일은 last_date 원본.
            _all_actual = (
                _ds.get("visit_dates", set())
                | _ds.get("inpatient_dates", set())
                | _inpatient_end_dates_in_range(_ds, datetime.min)
                | _ds.get("surgery_dates", set())
            )
            _actual_sorted = sorted(d for d in _all_actual if d and d != "2099-12-31")
            latest_date  = _actual_sorted[-1] if _actual_sorted else (_in_range[-1] if _in_range else first_date)
            _fd = _ds.get("first_date", "2099-12-31")
            first_diagnosis_date = _fd if _fd and _fd != "2099-12-31" else first_date

            _ds_inp_dates      = _win(_ds.get("inpatient_dates", set()))
            _ds_inp_periods    = _inpatient_periods_in_range(_ds, since_dt)
            if until_dt:  # BOHUMFIT-034: Q4 상한 적용(5년 초과~10년 입원만)
                _ds_inp_periods = [pp for pp in _ds_inp_periods
                                   if (_pp := _parse_ymd(pp.get("start", ""))) and _pp < until_dt]
            _ds_inp_map        = _ds.get("_inpatient_days_map", {})
            ds_inpatient_days  = sum(_ds_inp_map.get(d, 1) for d in _ds_inp_dates) if _ds_inp_dates else 0
            ds_inpatient_count = len(_ds_inp_dates)
            ds_visit_count     = len(_win(_ds.get("visit_events") or _ds.get("visit_dates", set())))
            # BOHUMFIT-031: 배지 투약일수를 헤더 판정과 동일 집계·동일 원천·동일 창으로 정합.
            # 헤더(filters Q3)는 med_dates_pharma_episode 를 _sum_daily_max_presc(날짜별
            # 최대의 누적 합계)로, since_dt(질문 창)에 맞춰 산출한다(Q3 건강체=10년).
            # 기존 _max_presc(단일 일자 최대)는 누적 합계와 불일치했음(BOHUMFIT-030 진단).
            # 동일 함수를 그대로 호출해 배지=헤더를 보장한다.
            _med_src           = _ds.get("med_dates_pharma_episode") or _ds.get("med_dates_pharma", {})
            # BOHUMFIT-032: 건강체 Q3 '투약 30일' 판정창은 고정 1825일. 헤더(filters)와 동일 창·집계로
            # 배지=헤더를 유지한다. 입원·통원 표시창(since_dt=10년)은 불변.
            _med_since         = q3_med_since if (not is_easy and q == "Q3" and q3_med_since is not None) else since_dt
            ds_med_days        = _sum_daily_max_presc(_med_src, _med_since)
        else:
            dates_sorted       = sorted([d for d in m["dates"] if d])
            first_date         = dates_sorted[0]  if dates_sorted else ""
            latest_date        = dates_sorted[-1] if dates_sorted else ""
            first_diagnosis_date = first_date
            ds_inpatient_days  = m["inpatient_days"]
            ds_inpatient_count = m.get("inpatient_count", 0)
            ds_visit_count     = m.get("visit_count", 0)
            ds_med_days        = m["med_days"]
            _ds_inp_dates      = []
            _ds_inp_periods    = []

        _chojin          = _ds["chojin_count"]  if _ds else 0
        _jaejin          = _ds["jaejin_count"]  if _ds else 0
        _procedures      = _sorted_strings(_ds.get("procedures", set()) or []) if _ds else []
        _proc_dates      = sorted(_ds.get("procedure_dates", set()) or []) if _ds else []
        _surg_susp       = _sorted_strings(_ds.get("surgery_suspected_names", set()) or []) if _ds else []
        _surg_susp_dates = sorted(_ds.get("surgery_suspected_dates", set()) or []) if _ds else []

        _at_res = _ds.get("_additional_test_result") if _ds else None
        _to_res = _ds.get("_treatment_ongoing_result") if _ds else None

        if _at_res is not None:
            _add_test_hit    = bool(_at_res.get("is_additional_test"))
            _add_test_reason = _at_res.get("reason", "")
            _additional_tests = [_at_res.get("test_type", "재검사")] if _add_test_hit else []
        else:
            _add_test_hit    = False
            _add_test_reason = ""
            _additional_tests = [t[:50] for t in _sorted_strings(_ds.get("tests_found", set()) or [])[:8]] if _ds else []

        if _to_res is not None:
            _tx_ongoing        = bool(_to_res.get("is_ongoing"))
            _tx_ongoing_reason = _to_res.get("reason", "")
        else:
            _tx_ongoing        = None
            _tx_ongoing_reason = ""

        flagged_codes.add(code_key)
        summary_reports[q_title].append({
            "first_date":              first_date,
            "latest_date":             latest_date,
            "first_diagnosis_date":    first_diagnosis_date,
            "code":                    m["code"],
            "display_code":            format_kcd_code(m["code"]),
            "name":                    m["name"] or (_ds.get("name", "") if _ds else ""),
            "visit":                   ds_visit_count,
            "chojin_count":            _chojin,
            "jaejin_count":            _jaejin,
            "total_clinic_visit":      _chojin + _jaejin if (_chojin + _jaejin) > 0 else ds_visit_count,
            "med_days":                ds_med_days,
            "med_days_30plus":         ds_med_days >= 30,
            "inpatient":               ds_inpatient_days,
            "inpatient_count":         ds_inpatient_count,
            "inpatient_dates":         _ds_inp_dates if _ds and _ds_inp_dates else [],
            "inpatient_periods":       _ds_inp_periods if _ds and _ds_inp_periods else [],
            "surgeries":               {m["surgery_name"]} if m["is_surgery"] and m["surgery_name"] else ({"수술"} if m["is_surgery"] else set()),
            "surgery_dates":           sorted(set(m["surgery_dates"])),
            "surgery_count":           len(set(m["surgery_dates"])) if m["is_surgery"] else 0,
            "procedures":              _procedures,
            "procedure_dates":         _proc_dates,
            "surgery_suspected":       _surg_susp,
            "surgery_suspected_dates": _surg_susp_dates,
            # BOHUMFIT-033/034: 공단 수술의심 등급은 5~10년 입원·수술 질문에서만 노출.
            # BOHUMFIT-066: 일반(건강체) Q4 ↔ 간편 Q2(10년 입원·수술)를 동기화 — 양쪽 동일 등급(강/약) 표시.
            "surgery_suspected_grade": _ds.get("surgery_suspected_grade", "") if (_ds and ((not is_easy and q == "Q4") or (is_easy and q == "Q2"))) else "",
            "additional_tests":        _additional_tests,
            "additional_test_hit":     _add_test_hit,
            "additional_test_reason":  _add_test_reason,
            # BOHUMFIT-128: Q2 추가검사·재검사 의심(고지 대상 아님·설계사 확인용) 표식.
            #   고지 복사 텍스트 제외 + 프런트 [B] '설계사 확인 필요 항목' 분리에 사용.
            "exam_check_only":         (q == "Q2") and bool(_add_test_hit or _add_test_reason or m.get("q2_suspicion", "")),
            "q2_suspicion":            m.get("q2_suspicion", ""),
            "treatment_ongoing":       _tx_ongoing,
            "treatment_ongoing_reason": _tx_ongoing_reason,
            "drug_change_in_3m":       _ds.get("drug_change_in_3m", False) if _ds else False,
            "hospitals":               m["hospitals"],
            "first_hospital":          (_ds.get("hospital_dates", {}).get(first_diagnosis_date, "")
                                        or _ds.get("hospital_dates", {}).get(first_date, "")) if _ds else "",
            "last_hospital":           _ds.get("hospital_dates", {}).get(latest_date, "") if _ds else "",
            "detail":                  m["reason"],
        })

    # BOHUMFIT-039: 직장·항문(K60·K61·K62·K64)이 Q5에만 잡히고 Q1~Q4에 항목이 없으면
    #  '실손의료비 가입 시에만 고지 필요' 안내 플래그(일반 고지 대상 아님). 간편엔 Q5 없음 → 미적용.
    _q5_title = q_labels.get("Q5")
    if _q5_title and summary_reports.get(_q5_title):
        _non_q5_codes = {r["code"] for qt, rows in summary_reports.items()
                         if qt != _q5_title for r in rows}
        for _r in summary_reports[_q5_title]:
            if any(str(_r.get("code", "")).startswith(_p) for _p in INSURANCE_ONLY_Q5_CODES) \
                    and _r["code"] not in _non_q5_codes:
                _r["insurance_only"] = True

    return summary_reports, flagged_codes


def _build_all_disease_summary(disease_stats):
    """disease_stats 전체를 날짜순으로 정리한 리스트 반환."""
    result = []
    for code_key, s in sorted(disease_stats.items(), key=lambda kv: (kv[1].get("first_date", ""), kv[0])):
        if code_key.startswith("PHARMA|"):
            continue
        all_dates = sorted(
            s.get("visit_dates", set())
            | s.get("inpatient_dates", set())
            | _inpatient_end_dates_in_range(s, datetime.min)
            | s.get("surgery_dates", set())
        )
        first_date  = all_dates[0]  if all_dates else (s.get("first_date", "") or "")
        latest_date = all_dates[-1] if all_dates else (s.get("latest_date", "") or "")
        if first_date and first_date == "2099-12-31":
            first_date = ""

        inp_map   = s.get("_inpatient_days_map", {})
        inp_dates = sorted(s.get("inpatient_dates", set()))
        inpatient_days = sum(inp_map.get(d, 1) for d in inp_dates) if inp_dates else 0

        result.append({
            "code":            s.get("diag_code") or code_key.split("|")[0],
            "display_code":    format_kcd_code(s.get("diag_code") or code_key.split("|")[0]),
            "name":            s.get("name", ""),
            "first_date":      first_date,
            "latest_date":     latest_date,
            "visit_count":     len(s.get("visit_events") or s.get("visit_dates", set())),
            "inpatient_count": len(inp_dates),
            "inpatient_days":  inpatient_days,
            "inpatient_periods": _inpatient_periods_in_range(s, datetime.min),
            "surgery_count":   len(s.get("surgery_dates", set())),
            "med_days":        _max_presc(s.get("med_dates_pharma", {}), datetime.min),
            "hospitals":       sorted(s.get("hospitals", set())),
        })

    result.sort(key=lambda x: x.get("latest_date") or "0000", reverse=True)
    return result


def build_summary_reports(
    disease_stats: dict,
    code_based_items_health: list[dict],
    code_based_items_easy: list[dict],
    ai_result: dict,
    product_type: str,
    today: datetime,
) -> tuple[dict, dict, set, dict]:
    """
    merged_items 빌드 + (표준/간편) summary_reports 생성.

    Returns:
        std_reports    : dict[str, list]
        easy_reports   : dict[str, list]
        flagged_codes  : set[str]
        merged_items   : dict[(code, q), item]
    """
    from datetime import timedelta

    _d3m_dt  = today - timedelta(days=90)
    _d1y_dt  = today - timedelta(days=365)
    _d5y_dt  = _subtract_years(today, 5)    # BOHUMFIT-004: 달력 기준 5년
    _d10y_dt = _subtract_years(today, 10)   # BOHUMFIT-004: 달력 기준 10년

    # BOHUMFIT-BUG-010: health/easy 풀을 분리해 각각 merged_items 빌드.
    # health 풀은 _health_items + ai_result.flagged_items, easy 풀은 _easy_items 만.
    _ = product_type  # 시그니처 호환

    def _build_pool(items_list: list[dict], include_ai: bool, q_since_map: dict) -> dict:
        pool_merged: dict = {}
        pool_claimed: set = set()
        source_list = list(items_list)
        if include_ai:
            source_list = source_list + list(ai_result.get("flagged_items", []))
        for item in source_list:
            _it_code = (item.get("code") or "").strip().upper()
            _it_name = (item.get("disease") or "").strip()
            if not _KCD_MERGE_RE.match(_it_code):
                continue
            if _it_name and any(pat in _it_name for pat in _NON_DISEASE_NAME_PATTERNS_MERGE):
                continue
            source   = item.get("_source", "ai")
            # BOHUMFIT-047: duty_question 이 None/비문자열/빈값이면 re.split 가 TypeError
            #   (expected string or bytes-like object, got 'NoneType') 로 전체 분석을 크래시시켰다.
            #   한 항목 결함이 전체를 죽이지 않도록 방어: AI(비결정론)는 q 불명이면 폐기(038 정신 —
            #   AI는 Q2만, q 불명이면 버림), 결정론(source=code)도 q 불명이면 경고 로그 후 폐기
            #   (정상 결정론 항목엔 q 가 항상 있어 발생하지 않음).
            q_raw    = item.get("duty_question")
            if not isinstance(q_raw, str) or not q_raw.strip():
                if source == "code":
                    logger.warning(
                        "BOHUMFIT-047: 결정론 항목 duty_question 누락/비문자열 — skip (code=%s, q=%r)",
                        item.get("code"), q_raw,
                    )
                continue
            raw_code_key = item.get("code", item.get("disease", "unknown"))
            code_key = normalize_code(raw_code_key) or raw_code_key
            q_list_ = [q.strip() for q in re.split(r"[,/\s]+", q_raw) if re.match(r"Q\d+", q.strip())]
            if not q_list_:
                q_list_ = [q_raw.strip()]
            for q in q_list_:
                if q not in ("Q1", "Q2", "Q3", "Q4", "Q5"):  # BOHUMFIT-034: Q5 추가
                    continue
                # BOHUMFIT-038: AI(비결정론) 항목은 Q2(추가검사·재검사 의심)에만 부여 허용.
                # 중대질병·입원·수술 등 Q1/Q3/Q4/Q5는 결정론(filters/033) 전용 — AI 누수 차단.
                if source != "code" and q != "Q2":
                    continue
                item_dt = _parse_ymd(item.get("date", ""))
                since_dt = q_since_map.get(q)
                if since_dt and (not item_dt or item_dt < since_dt):
                    continue
                merge_key = (code_key, q)
                if source == "code":
                    pool_claimed.add(merge_key)
                    if merge_key not in pool_merged:
                        pool_merged[merge_key] = _make_merged_item(item, q, code_key)
                    else:
                        _merge_item_into(pool_merged[merge_key], item)
                    continue
                if merge_key in pool_claimed:
                    continue
                if merge_key not in pool_merged:
                    pool_merged[merge_key] = _make_merged_item(item, q, code_key)
                else:
                    _merge_item_into(pool_merged[merge_key], item)
        return pool_merged

    # BOHUMFIT-BUG-012: 탭별 질문 창 분리 — 간편 Q2=10년, 건강체 Q2=1년.
    # BOHUMFIT-034: Q3=5년, Q4 신설=5년 초과~10년(하한 d10y), Q5=기존 중대질환 5년.
    _health_since = {"Q1": _d3m_dt, "Q2": _d1y_dt, "Q3": _d5y_dt, "Q4": _d10y_dt, "Q5": _d5y_dt}
    _easy_since   = {"Q1": _d3m_dt, "Q2": _d10y_dt, "Q3": _d5y_dt}

    merged_health = _build_pool(code_based_items_health, True,  _health_since)   # BOHUMFIT-047
    merged_easy   = _build_pool(code_based_items_easy,   False, _easy_since)
    _health_q3_med_since = _q3_med_since(today)

    std_reports, std_flagged = _build_reports_for_product(
        merged_health, disease_stats,
        "건강체/표준체 (일반심사)",
        _d3m_dt, _d1y_dt, _d10y_dt, _d5y_dt,
        is_easy=False,
        q3_med_since=_health_q3_med_since,
    )
    easy_reports, easy_flagged = _build_reports_for_product(
        merged_easy, disease_stats,
        "간편심사 (유병자 3-10-5 기준)",
        _d3m_dt, _d1y_dt, _d10y_dt, _d5y_dt,
        is_easy=True,
    )

    flagged_codes = std_flagged | easy_flagged
    # 호환: merged_items 는 두 풀의 union (외부 호출처가 사용하면 안 손상되도록)
    merged_items = {**merged_health, **merged_easy}
    return std_reports, easy_reports, flagged_codes, merged_items
