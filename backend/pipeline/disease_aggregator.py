"""disease_stats 빌드 + 약 변경 감지 + 처방 종료일 계산 — analyzer.py 에서 이동."""
from __future__ import annotations

import gc
import re
from collections import defaultdict
from datetime import datetime, timedelta

import pandas as pd

from .helpers import (
    PROCEDURE_COST_THRESHOLD,
    SURGERY_COST_THRESHOLD,
    _add_days,
    _clean_disease_name,
    _cross_key,
    _is_confirmed_surgery_cost_kw,
    _is_procedure_kw,
    _is_surgery_match,
    _sorted_strings,
    _subtract_years,
    _to_int_cost,
    disclosure_group_code,
    disclosure_group_name,
    extract_drug_info,
    get_diagnosis_code,
    get_diagnosis_name,
    get_val,
    nhis_surg_keywords,
    normalize_code,
    normalize_ingredient,
    parse_date,
    row_is_junk,
    test_keywords,
)
from .surgery_exclusions import is_non_surgery_excluded, is_non_surgery_action  # BOHUMFIT-062·059
from .nhis_history_constants import grade_surgery_suspicion, stronger_grade  # BOHUMFIT-033


def new_disease():
    return {
        "visit_dates": set(), "visit_events": [], "med_dates_basic": {}, "med_dates_pharma": {},
        "med_dates_pharma_episode": {},
        "drug_names_in_90": set(), "drug_names_before_90": set(),
        "tests_found": set(), "test_events": [], "inpatient_dates": set(), "inpatient_periods": [],
        "inpatient_admissions": set(),
        "surgeries": set(), "surgery_dates": set(), "hospitals": set(),
        "procedures": set(),
        "procedure_dates": set(),
        "surgery_suspected_names": set(),
        "surgery_suspected_dates": set(),
        "surgery_suspected_grade": "",  # BOHUMFIT-033: 공단 수술의심 최강 등급(강/약/"")
        "_daily_facts": {},
        "_inpatient_days_map": {},
        "chojin_count": 0,
        "jaejin_count": 0,
        "drug_change_in_3m": False,
        "hospital_dates": {},
        "first_date": "2099-12-31", "latest_date": "2000-01-01",
        "diag_code": "", "name": "", "has_pharma": False,
        "_pharma_seen": set(),
        # BOHUMFIT-205: 약품명 → 성분명(처방조제 '성분명' 컬럼) 원문 매핑.
        #   detect_drug_changes 가 동일 성분 브랜드 전환(제네릭 교체)을 '새 약'으로 오탐하지 않게 한다.
        "drug_ingredient_map": {},
        # BOHUMFIT-205: 약품별 마지막 확인 처방일. 3개월 구간의 일시 기록과 현재 확인 약을 재대조한다.
        "drug_last_seen_dates": {},
    }


def _record_drug_exposure(
    disease: dict,
    drug: str,
    clean_date: str,
    days_ago: int,
    ingredient: str,
) -> None:
    """Keep the narrow drug-change inputs needed for the 90-day confirmation."""
    if not drug:
        return
    if days_ago <= 90:
        disease["drug_names_in_90"].add(drug)
    else:
        disease["drug_names_before_90"].add(drug)
    if ingredient:
        disease.setdefault("drug_ingredient_map", {})[drug] = ingredient
    if clean_date:
        seen_dates = disease.setdefault("drug_last_seen_dates", {})
        if clean_date >= seen_dates.get(drug, ""):
            seen_dates[drug] = clean_date


def _norm_provider_name(value: str | None) -> str:
    return re.sub(r"[\s·ㆍ\.\-_/]", "", value or "")


def _is_pharmacy(name: str | None) -> bool:
    # BOHUMFIT-050: 요양기관명 공백 변형("약 국", "약  국")으로 약국 가드가 새던 문제 대응 —
    #   공백 제거 후 '약국' 매칭으로 일원화(통원·detail-link·표시 hospitals 전반 일관 적용).
    return "약국" in re.sub(r"\s+", "", name or "")


def _detail_action_name(row) -> str:
    code_name = get_val(row, ["코드명", "수가명", "행위명칭", "행위명"])
    if code_name:
        return code_name
    return get_val(row, ["진료내역", "처치", "처치및수술", "처치및수 술"])


def _is_detail_support_only(text: str) -> bool:
    compact = re.sub(r"\s+", "", text or "").upper()
    if not compact:
        return False
    # BOHUMFIT-130: 유치카테터/유치도뇨(관)는 '카테터' 보조재 가드가 아닌 시술(수술O)로 본다.
    if "유치" in compact:
        return False
    support_only_keywords = (
        "SNARE",
        "SMARTINJECTOR",
        "INJECTOR",
        "GUIDEWIRE",
        "CATHETER",
        "FORCEP",
        "FORCEPS",
        "BALLOON",
        "STENT",
        "CLIP",
        "SCREW",
        "PLATE",
        "PIN",
        "클립",
        "카테터",
        "스텐트",
        "스크류",
        "플레이트",
        "치석제거",
        "치근활택",
        "재활저출력레이저치료",
        "저출력레이저치료",
        "레이저치료[1일당]",
    )
    return any(kw in compact for kw in support_only_keywords)


_DETAIL_CONFIRMED_SURGERY_KEYWORDS = (
    "발치술",
    "매복치발치",
    "난발치",
    "결장경하종양수술",
    "내시경하종양수술",
    "내시경적점막절제술",
    "점막하박리절제술",
    "폴립절제술",
    "폴립 절제술",
    "용종절제술",
    "용종 절제술",
    "점막절제술",
    "점막 절제술",
    "절제술",
    "절개술",
    "절개배농",
    "배농술",
    "적출술",
    "봉합술",
    "이식술",
    "재건술",
    "고정술",
    "유합술",
    "치환술",
    "절단술",
    "성형술",
    "정복술",
    "박리술",
    "소파술",
    "근치수술",
    "근본수술",
    "내시경수술",
    "복강경",
    "흉강경",
    "관절경",
    "후궁절제술",
    "추간판제거술",
    "낭종절제",
    "종양수술",
    "치핵절제",
    "치루수술",
    "충수절제",
    "담낭절제",
    "제왕절개",
    "백내장수술",
    "인공수정체삽입술",
    "혈관성형술",
    "색전술",
    # BOHUMFIT-130: 수술O 보강 — 유치카테터(유치도뇨관)·티눈 냉각응고술. 후궁/신경 성형술은 '성형술'로 이미 포함.
    "유치카테터",
    "유치도뇨",
    "냉각응고술",
)


def _is_detail_surgery_match(text: str) -> bool:
    if not text or _is_detail_support_only(text):
        return False
    if is_non_surgery_excluded(text):  # BOHUMFIT-062: 비수술 코드명 전역 제외
        return False
    if is_non_surgery_action(text):    # BOHUMFIT-059: 검사·처치·주사 행위 제외(강수술 신호는 통과)
        return False
    compact = re.sub(r"\s+", "", text)
    return (
        _is_surgery_match(text)
        or any(kw in text or kw in compact for kw in _DETAIL_CONFIRMED_SURGERY_KEYWORDS)
        or any(kw in text for kw in nhis_surg_keywords)
    )


_S_CODE_RE = re.compile(r"^S\d")  # BOHUMFIT-126: 상해 S코드(S00~S99) 판별(그룹코드 기준)


def _pick_episode_start(starts: list[str], clean_date: str) -> str:
    """BOHUMFIT-126: clean_date 이하의 가장 최근 초진일(없으면 가장 이른 초진일)."""
    chosen = starts[0]
    for s in starts:
        if s <= clean_date:
            chosen = s
        else:
            break
    return chosen


def build_disease_stats(
    records: list[dict],
    today: datetime,
) -> tuple[dict, list[str], list[str], list[tuple[str, str]], dict[str, list[str]]]:
    """
    파싱된 records 로부터 disease_stats + AI 전달용 raw_entries 빌드.

    Returns:
        disease_stats        : dict[group_key, disease_record]
        cross_surgery_hints  : list[str]
        date_warnings        : list[str]  — 날짜 파싱 실패/미래 날짜 경고
        raw_entries          : list[(fname, line)]  — AI raw_text 생성용
        lines_by_file        : dict[fname, list[str]]
    """
    df = pd.DataFrame(records)
    if "_ftype" in df.columns:
        ftype_order = {"basic": 0, "nhis": 0, "unknown": 1, "detail": 2, "pharma": 3}
        df["_parse_order"] = df["_ftype"].map(ftype_order).fillna(9)
        df = df.sort_values("_parse_order", kind="stable").drop(columns=["_parse_order"])

    disease_stats: dict = defaultdict(new_disease)
    basic_diagnosis_names: dict[str, str] = {}
    basic_by_day_provider: dict[tuple[str, str], list[dict]] = defaultdict(list)
    cross_day_index = defaultdict(lambda: {
        "max_basic_cost": 0,
        "basic_hospitals": set(),
        "detail_proc_names": set(),
        "has_detail_surg_kw": False,
        "has_detail_proc_kw": False,
        "inpatient_flag": False,
    })

    date_parse_fail_count = 0
    date_parse_fail_samples: list[str] = []
    future_date_count = 0
    empty_date_count = 0
    # BOHUMFIT-033: 공단(nhis)은 5~10년 전용 — 5년 이내(심평원 담당)는 반영하지 않는 경계.
    _nhis_floor_str = _subtract_years(today, 5).strftime("%Y-%m-%d")

    for _, row in df.iterrows():
        ftype = str(row.get("_ftype", "unknown"))
        if ftype not in ("basic", "unknown"):
            continue
        if row_is_junk(row):
            continue
        date_str = get_val(row, ["진료개시일", "진료시작일", "진료일"])
        clean_date = parse_date(date_str)
        raw_code = get_diagnosis_code(row)
        code_str = normalize_code(raw_code)
        if not clean_date or not code_str:
            continue
        hospital = get_val(row, ["병·의원", "기관명", "요양기관명", "병·의원&약국"])
        if _is_pharmacy(hospital):   # BOHUMFIT-050: 공백 변형 약국까지 일관 제외
            continue
        # BOHUMFIT-043: 040의 진단과='일반의' 제외 게이트 제거(detail-link 인덱스 보존).
        basic_by_day_provider[(clean_date, _norm_provider_name(hospital))].append({
            "code": code_str,
            "grouped_code": disclosure_group_code(code_str),
            "name": get_diagnosis_name(row),
        })

    # ── BOHUMFIT-126: S코드(상해) 초진 발생일 수집 ────────────────────────────
    #   세부진료 '진료내역'에 초진이 있으면(또는 record가 is_first_visit=True) 새 상해 에피소드 시작.
    #   날짜+기관으로 기본진료 S코드에 연결해 코드별 초진일 목록을 만든다(재진은 새 그룹 미생성).
    _injury_starts: dict[str, list[str]] = defaultdict(list)
    for _, row in df.iterrows():
        if str(row.get("_ftype", "")) != "detail":
            continue
        _act = _detail_action_name(row)
        _is_first = bool(row.get("is_first_visit")) or ("초진" in (_act or ""))
        if not _is_first:
            continue
        _ddate = parse_date(get_val(row, ["진료개시일", "진료시작일", "진료일"]))
        _dprov = _norm_provider_name(get_val(row, ["병·의원", "기관명", "요양기관명", "병·의원&약국"]))
        if not _ddate:
            continue
        _linked = basic_by_day_provider.get((_ddate, _dprov), [])
        _gcode = _linked[0].get("grouped_code", "") if _linked else ""
        if _gcode and _S_CODE_RE.match(_gcode):
            _injury_starts[_gcode].append(_ddate)
    for _g in list(_injury_starts):
        _injury_starts[_g] = sorted(set(_injury_starts[_g]))

    # ── disease_stats 구축 루프 ───────────────────────────────────
    for _, row in df.iterrows():
        if row_is_junk(row):
            continue
        ftype    = str(row.get("_ftype", "unknown"))

        linked_basic = None
        if ftype == "detail":
            detail_date = parse_date(get_val(row, ["진료개시일", "진료시작일", "진료일"]))
            detail_provider = _norm_provider_name(get_val(row, ["병·의원", "기관명", "요양기관명", "병·의원&약국"]))
            matches = basic_by_day_provider.get((detail_date, detail_provider), [])
            if matches:
                linked_basic = matches[0]

        if ftype == "detail" and linked_basic:
            raw_code = linked_basic["code"]
        elif ftype in ("detail", "pharma"):
            raw_code = ""
        else:
            raw_code = get_diagnosis_code(row)
        code_str = normalize_code(raw_code)
        grouped_code_str = disclosure_group_code(code_str)

        if ftype == "detail":
            name_str = _detail_action_name(row)
        elif ftype == "pharma":
            name_str = get_val(row, ["약품명", "의약품명"])
        else:
            name_str = get_diagnosis_name(row) or get_val(row, ["약품명", "진료내역",
                                                               "행위명칭", "행위명", "처치및수술", "처치및수 술"])

        in_out   = get_val(row, ["입내원구분", "입원외래구분", "입원", "외래", "구분"])
        hospital = get_val(row, ["병·의원", "기관명", "요양기관명", "병·의원&약국"])
        date_str = get_val(row, ["진료개시일", "진료시작일", "진료일", "조제일자", "처방일"])
        # BOHUMFIT-124: 자동차보험(한방 포함) 기본진료 PDF는 입원일수를 '진료일수' 컬럼에 둔다.
        #   기존 키(내원/투약/요양일수)만으로는 m_days=0 → 입원이 0일로 무시됐다(한방 침구과 입원 누락).
        #   '진료일수'를 마지막 후보로 추가(정상 심평원 '내원일수'·처방 '총투약일수' 매칭에는 영향 없음).
        m_days_raw = get_val(row, ["내원일수", "투약일수", "요양일수", "진료일수"])
        m_days = int(re.findall(r"\d+", m_days_raw)[0]) if re.findall(r"\d+", m_days_raw) else 0
        cost_raw = get_val(row, ["총진료비", "진료비", "총 진료비", "본인부담총액", "급여비용총액"])
        cost_val = _to_int_cost(cost_raw)

        # BOHUMFIT-043: 040의 진단과='일반의' 메인 집계 제외 게이트 제거(행 보존 — 입원·수술·투약·detail 정상).
        if grouped_code_str:
            group_key = grouped_code_str
        elif ftype == "pharma":
            name_norm    = re.sub(r"[\s\d\.\-\[\]]", "", name_str)[:12]
            month_bucket = parse_date(date_str)[:7] if parse_date(date_str) else ""
            group_key = f"PHARMA|{name_norm}|{month_bucket}" if name_norm else ""
        else:
            group_key = ""
        if not group_key:
            continue

        clean_date = parse_date(date_str)
        # BOHUMFIT-126: S코드(상해) 에피소드 분리 — 초진일이 있는 S코드는 group_key에 해당 에피소드
        #   초진일을 붙여 초진마다 별개 그룹을 만든다(재진/이후 진료는 직전 초진 에피소드에 귀속).
        #   초진 정보가 없는 S코드·비S코드는 기존 group_key 유지(하위호환).
        if grouped_code_str and clean_date and grouped_code_str in _injury_starts:
            group_key = f"{grouped_code_str}|{_pick_episode_start(_injury_starts[grouped_code_str], clean_date)}"
        if not clean_date:
            if (date_str or "").strip():
                # 값은 있으나 날짜로 인식 불가
                date_parse_fail_count += 1
                if len(date_parse_fail_samples) < 5:
                    date_parse_fail_samples.append(date_str[:30])
            else:
                # 진료일자 칸이 비어 있는 행 — 기간 판정에서 조용히 빠지므로 집계
                empty_date_count += 1

        s = disease_stats[group_key]

        if grouped_code_str and ftype in ("basic", "unknown", "nhis"):
            diagnosis_name = get_diagnosis_name(row) or (name_str if ftype == "nhis" else "")
            diagnosis_name = disclosure_group_name(grouped_code_str, diagnosis_name)
            if diagnosis_name:
                basic_diagnosis_names.setdefault(grouped_code_str, diagnosis_name)

        if grouped_code_str and not s["diag_code"]:
            s["diag_code"] = grouped_code_str
        if grouped_code_str:
            canonical_name = basic_diagnosis_names.get(grouped_code_str) or disclosure_group_name(grouped_code_str, "")
            if canonical_name and (not s["name"] or s["name"] == grouped_code_str):
                s["name"] = canonical_name

        if clean_date:
            dt = datetime.strptime(clean_date, "%Y-%m-%d")
            days_ago = (today - dt).days

            if days_ago < 0:
                future_date_count += 1
                continue

            if ftype in ("basic", "unknown"):
                if "약국" in in_out:
                    continue
                is_inpatient = "입원" in in_out or "입원" in name_str
                if is_inpatient:
                    if m_days > 0:  # BOHUMFIT-061: 0일 입원은 입원 이력에서 무시
                        s["inpatient_dates"].add(clean_date)
                        s["inpatient_admissions"].add((clean_date, _norm_provider_name(hospital)))
                        prev_inp = s["_inpatient_days_map"].get(clean_date, 0)
                        s["_inpatient_days_map"][clean_date] = max(prev_inp, m_days)
                        s.setdefault("inpatient_periods", []).append({
                            "start": clean_date,
                            "end": _add_days(clean_date, m_days),
                            "days": m_days,
                            # BOHUMFIT-213: 표시용 근거(어디서) — 판정 로직 미사용.
                            "hospital": (hospital or "").strip(),
                        })
                        if _add_days(clean_date, m_days) > s["latest_date"]:
                            s["latest_date"] = _add_days(clean_date, m_days)
                else:
                    # BOHUMFIT-043/050: 요양기관명이 약국(공백 변형 포함)이면 통원에서만 제외.
                    #   행 자체는 보존 — 입원·세부수술 링크·투약(med_dates_basic/pharma) 경로 불변.
                    # BOHUMFIT-050: 통원 카운트 단위 = 내원 '행'(visit_events 리스트, 같은날 중복 허용).
                    #   visit_dates(집합)는 pharma cross-ref 앵커 전용으로 분리 유지(카운트에 미사용).
                    if not _is_pharmacy(hospital):
                        s["visit_dates"].add(clean_date)                 # pharma 앵커용(집합)
                        s.setdefault("visit_events", []).append(clean_date)  # 통원 카운트용(행)
                if m_days > 0:
                    prev = s["med_dates_basic"].get(clean_date, 0)
                    if m_days > prev:
                        s["med_dates_basic"][clean_date] = m_days
                if hospital and not _is_pharmacy(hospital):
                    s["hospital_dates"].setdefault(clean_date, hospital)
                day_fact = s["_daily_facts"].setdefault(clean_date, {"max_basic_cost": 0, "detail_proc_names": set()})
                day_fact["max_basic_cost"] = max(day_fact["max_basic_cost"], cost_val)
            elif ftype == "detail":
                act_name = _detail_action_name(row)
                surg_col = get_val(row, ["처치및수술", "처치및수 술", "처치/수술"])
                surg_target = act_name if act_name else name_str
                # BOHUMFIT-059: 처치및수술 컬럼이 비어있지 않아도 검사·처치·주사 행위면 수술 미판정
                #   (복부초음파·병변내주입요법 등 오탐 제거). 강수술 신호는 is_non_surgery_action 이 통과시킴.
                _non_surg_action = is_non_surgery_action(surg_target) or is_non_surgery_action(surg_col)
                is_surg_by_column = (
                    bool(surg_col and surg_col.strip() and surg_col.strip() != "0")
                    and not _non_surg_action
                )
                is_surg_by_keyword = _is_detail_surgery_match(surg_target)

                if is_surg_by_column:
                    surg_label = surg_col.strip() if len(surg_col.strip()) > 2 else (surg_target or "처치및수술")
                    s["surgeries"].add(surg_label)
                    s["surgery_dates"].add(clean_date)
                elif is_surg_by_keyword:
                    s["surgeries"].add(surg_target)
                    s["surgery_dates"].add(clean_date)

                day_fact = s["_daily_facts"].setdefault(clean_date, {"max_basic_cost": 0, "detail_proc_names": set()})
                if surg_target:
                    day_fact["detail_proc_names"].add(surg_target)
                day_fact["_is_surg_by_column"] = day_fact.get("_is_surg_by_column", False) or is_surg_by_column
                for kw in test_keywords:
                    if kw in surg_target:
                        s["tests_found"].add(surg_target)
                        if clean_date and surg_target:
                            s.setdefault("test_events", []).append({
                                "date": clean_date,
                                "name": surg_target,
                                "hospital": hospital,
                                "source": "detail",
                            })
                        break
                _chk = act_name or name_str
                if "초진" in _chk:
                    s["chojin_count"] += 1
                elif "재진" in _chk:
                    s["jaejin_count"] += 1
            elif ftype == "pharma":
                # 처방/조제 구분 — 헤더 정규화 후 컬럼명 "처방/조제"까지 인식하도록 키 확장
                # "처방조제"·"조제" 등 약국 조제 행은 스킵; "외래"(병원 처방)는 통과
                _gubun = get_val(row, ["처방/조제", "처방조제구분", "처방조제", "처방구분", "구분", "분류"])
                _gubun_clean = (_gubun or "").replace(" ", "").strip()
                if _gubun_clean and _gubun_clean != "외래" and "조제" in _gubun_clean:
                    continue

                # 추가 안전망: 진짜 중복 행만 차단.
                # 키에 병원명·투약일수 포함 — 같은 날 같은 약이라도 병원이
                # 다르거나 투약일수가 다르면 별개 처방으로 보아 보존한다.
                # (감사: _pharma_seen 키 보강 — 정상 처방 오스킵 방지)
                _seen_key = (
                    clean_date,
                    (name_str or "").strip(),
                    (hospital or "").strip(),
                    m_days,
                )
                if _seen_key in s["_pharma_seen"]:
                    continue
                s["_pharma_seen"].add(_seen_key)

                # BOHUMFIT-205: 처방조제 '성분명' 확보 — 동일 성분 브랜드 전환 오탐 방지용.
                _ingredient_str = (get_val(row, ["성분명", "성분"]) or "").strip()

                _target_groups = []
                for _ck, _cs in disease_stats.items():
                    if not _cs.get("diag_code") or _ck.startswith("PHARMA|"):
                        continue
                    if clean_date in _cs.get("visit_dates", set()) or \
                       clean_date in _cs.get("inpatient_dates", set()):
                        _target_groups.append(_ck)

                if _target_groups:
                    for _tg in _target_groups:
                        _ts = disease_stats[_tg]
                        _ts["has_pharma"] = True
                        if m_days > 0:
                            _prev = _ts["med_dates_pharma"].get(clean_date, 0)
                            if m_days > _prev:
                                _ts["med_dates_pharma"][clean_date] = m_days
                            _episode_key = hospital.strip() or "_unknown"
                            _episode_map = _ts.setdefault("med_dates_pharma_episode", {}).setdefault(clean_date, {})
                            _episode_map[_episode_key] = max(_episode_map.get(_episode_key, 0), m_days)
                        _drug = name_str.strip()
                        if _drug:
                            _record_drug_exposure(
                                _ts, _drug, clean_date, days_ago, _ingredient_str,
                            )
                    continue

                s["has_pharma"] = True
                if m_days > 0:
                    prev = s["med_dates_pharma"].get(clean_date, 0)
                    if m_days > prev:
                        s["med_dates_pharma"][clean_date] = m_days
                    _episode_key = hospital.strip() or "_unknown"
                    _episode_map = s.setdefault("med_dates_pharma_episode", {}).setdefault(clean_date, {})
                    _episode_map[_episode_key] = max(_episode_map.get(_episode_key, 0), m_days)
                drug = name_str.strip()
                if drug:
                    _record_drug_exposure(
                        s, drug, clean_date, days_ago, _ingredient_str,
                    )
            elif ftype == "nhis":
                # BOHUMFIT-033: 공단 요양급여내역 = 5~10년 입원·수술'의심' 전용.
                #  - 5년 이내(심평원 담당)는 반영하지 않는다(경계: clean_date >= 5년 → 스킵).
                #  - 수술은 자동 확정 금지: 진료비·입내원구분·키워드로 '의심(강/약)' 등급만 부여.
                #  - 심평원(basic/detail) 확정 수술 경로는 건드리지 않는다.
                if not clean_date or clean_date >= _nhis_floor_str:
                    pass  # 5년 이내 공단 레코드 무시(역할 한정)
                else:
                    if in_out == "입원":
                        if m_days > 0:  # BOHUMFIT-061: 0일 입원 무시
                            s["inpatient_dates"].add(clean_date)
                            s["inpatient_admissions"].add((clean_date, _norm_provider_name(hospital)))
                            prev_inp = s["_inpatient_days_map"].get(clean_date, 0)
                            s["_inpatient_days_map"][clean_date] = max(prev_inp, m_days)
                            s.setdefault("inpatient_periods", []).append({
                                "start": clean_date,
                                "end": _add_days(clean_date, m_days),
                                "days": m_days,
                                # BOHUMFIT-213: 표시용 근거(어디서) — 판정 로직 미사용.
                                "hospital": (hospital or "").strip(),
                            })
                            if _add_days(clean_date, m_days) > s["latest_date"]:
                                s["latest_date"] = _add_days(clean_date, m_days)
                    elif in_out == "약국":
                        s["has_pharma"] = True
                    # 외래는 통원으로 세지 않는다(공단=입원·수술의심 전용).

                    # 수술 '의심' 등급(자동 확정 금지) — nhis 분기 한정.
                    _has_surg_kw = _is_surgery_match(name_str) or any(kw in name_str for kw in nhis_surg_keywords)
                    _grade = grade_surgery_suspicion(
                        in_out, cost_val, _has_surg_kw, is_non_surgery_excluded(name_str),
                    )
                    if _grade:
                        s["surgery_suspected_names"].add(name_str)
                        if clean_date:
                            s["surgery_suspected_dates"].add(clean_date)
                        s["surgery_suspected_grade"] = stronger_grade(
                            s.get("surgery_suspected_grade", ""), _grade,
                        )
                    for kw in test_keywords:
                        if kw in name_str: s["tests_found"].add(name_str); break

            if ftype in ("basic", "unknown"):
                if _is_surgery_match(name_str):
                    s["surgeries"].add(name_str)
                    if clean_date: s["surgery_dates"].add(clean_date)
                for kw in test_keywords:
                    if kw in name_str: s["tests_found"].add(name_str); break

            if clean_date > s["latest_date"]: s["latest_date"] = clean_date
            if clean_date < s["first_date"]:  s["first_date"]  = clean_date

            # BOHUMFIT-061: disease_stats 키와 동일한 KCD3 그룹으로 교차 인덱스를 만든다.
            ckey = _cross_key(grouped_code_str, name_str)
            if ckey:
                idx = cross_day_index[(ckey, clean_date)]
                if ftype in ("basic", "unknown"):
                    idx["max_basic_cost"] = max(idx["max_basic_cost"], cost_val)
                    if hospital:
                        idx["basic_hospitals"].add(hospital)
                    if "입원" in in_out or "입원" in name_str:
                        idx["inpatient_flag"] = True
                elif ftype == "detail":
                    act_name_idx = _detail_action_name(row)
                    target_idx = act_name_idx if act_name_idx else name_str
                    if target_idx:
                        idx["detail_proc_names"].add(target_idx)
                    if _is_detail_surgery_match(target_idx):
                        idx["has_detail_surg_kw"] = True
                    if _is_procedure_kw(target_idx):
                        idx["has_detail_proc_kw"] = True

        if hospital and not _is_pharmacy(hospital) and ftype != "pharma":   # BOHUMFIT-050
            s["hospitals"].add(hospital)
        if name_str and ftype not in ("detail", "pharma"):
            canonical_name = basic_diagnosis_names.get(grouped_code_str) or disclosure_group_name(code_str, _clean_disease_name(name_str))
            if canonical_name and (not s["name"] or s["name"] == grouped_code_str):
                s["name"] = canonical_name

    # ── 기본/세부 동일일자 교차 수술/시술 판정 ────────────────────
    cross_surgery_hints: list[str] = []
    for _ck, _s in disease_stats.items():
        _dc = (_s.get("diag_code") or "").strip()
        _name = _s.get("name", "")
        ckey = _cross_key(_dc, _name) if (_dc or _name) else ""
        if not ckey:
            continue
        for d, day_fact in _s.get("_daily_facts", {}).items():
            idx = cross_day_index.get((ckey, d))
            if not idx:
                continue
            max_cost = idx.get("max_basic_cost", 0)
            has_detail_proc    = bool(idx.get("detail_proc_names"))
            has_detail_surg_kw = bool(idx.get("has_detail_surg_kw"))
            has_detail_proc_kw = bool(idx.get("has_detail_proc_kw"))
            is_col_confirmed   = day_fact.get("_is_surg_by_column", False)

            if is_col_confirmed:
                if d not in _s["surgery_dates"]:
                    _s["surgery_dates"].add(d)
                    if idx["detail_proc_names"]:
                        _s["surgeries"].update(idx["detail_proc_names"])
                cross_surgery_hints.append(
                    f"{d} {_dc or ckey} {'|'.join(_sorted_strings(idx.get('detail_proc_names', set()))[:2]) or _name} "
                    f"컬럼확정(처치및수술+기본진료비 {max_cost:,}원)"
                )
            elif max_cost >= SURGERY_COST_THRESHOLD:
                if has_detail_surg_kw:
                    if d not in _s["surgery_dates"]:
                        _s["surgery_dates"].add(d)
                    if idx["detail_proc_names"]:
                        confirmed_proc_names = []
                        for pn in idx["detail_proc_names"]:
                            if _is_detail_support_only(pn):
                                continue
                            if _is_confirmed_surgery_cost_kw(pn) or _is_detail_surgery_match(pn):
                                confirmed_proc_names.append(pn)
                                _s["surgeries"].add(pn)
                        if not (_s["surgeries"] & set(idx["detail_proc_names"])):
                            _s["surgeries"].update(idx["detail_proc_names"])
                        _hint_name = next(iter(_sorted_strings(confirmed_proc_names)), next(iter(_sorted_strings(idx["detail_proc_names"]))))
                    else:
                        _hint_name = _name or _dc or "수술"
                    cross_surgery_hints.append(
                        f"{d} {_dc or ckey} {_hint_name} 교차확정(수술키워드+기본진료비 {max_cost:,}원)"
                    )
                elif has_detail_proc:
                    _hint_name = next(iter(_sorted_strings(idx["detail_proc_names"])), _name or "수술 의심")
                    _s["surgery_suspected_names"].add(_hint_name)
                    _s["surgery_suspected_dates"].add(d)
                    cross_surgery_hints.append(
                        f"{d} {_dc or ckey} {_hint_name} 수술의심(키워드없음+기본진료비 {max_cost:,}원) ★설계사확인"
                    )
                else:
                    _hint_name = _name or _dc or "고액진료"
                    _s["surgery_suspected_names"].add(_hint_name)
                    _s["surgery_suspected_dates"].add(d)
                    cross_surgery_hints.append(
                        f"{d} {_dc or ckey} {_hint_name} 수술의심(기본진료비 {max_cost:,}원) ★원자료확인"
                    )
            elif max_cost >= PROCEDURE_COST_THRESHOLD:
                if has_detail_proc_kw:
                    for pn in (idx.get("detail_proc_names") or set()):
                        if _is_procedure_kw(pn):
                            _s["procedures"].add(pn)
                    _s["procedure_dates"].add(d)
                elif has_detail_surg_kw:
                    _hint_name = next(iter(_sorted_strings(idx["detail_proc_names"]))) if idx["detail_proc_names"] else (_name or _dc or "진료")
                    cross_surgery_hints.append(
                        f"{d} {_dc or ckey} {_hint_name} 교차후보(수술키워드+기본진료비 {max_cost:,}원) ★AI판단필요"
                    )

    # ── 날짜 파싱 실패/미래일자 경고 ─────────────────────────────
    date_warnings: list[str] = []
    if date_parse_fail_count > 0:
        sample_text = ", ".join(date_parse_fail_samples[:3])
        date_warnings.append(
            f"⚠️ 날짜 인식 실패 {date_parse_fail_count}건 (예: {sample_text}) — "
            f"해당 레코드의 기간 판정이 누락될 수 있습니다."
        )
    # BOHUMFIT-138(항목5): 미래 날짜 레코드는 그대로 제외(로직 유지)하되, 사용자 경고 메시지는 표시하지 않는다.
    #   (future_date_count 카운트·days_ago<0 continue 제외 로직은 불변. 안내 문구만 생성 생략.)
    _ = future_date_count
    if empty_date_count > 0:
        date_warnings.append(
            f"⚠️ 진료일자 없는 레코드 {empty_date_count}건 — 날짜 칸이 비어 있어 "
            f"기간(3개월·1년·5년·10년) 판정에서 제외됐습니다. 원본 PDF에서 직접 확인해 주세요."
        )

    # ── AI 전달용 raw_entries 빌드 (같은 df 재사용) ──────────────
    raw_entries: list[tuple[str, str]] = []
    seen_code_dates: set = set()
    _d10y_dt = _subtract_years(today, 10)   # BOHUMFIT-004: 달력 기준 10년

    for _, row in df.iterrows():
        if row_is_junk(row): continue
        ftype    = str(row.get("_ftype", ""))
        dept     = get_val(row, ["진단과"])
        if ftype in ("basic", "unknown") and dept.replace(" ", "") == "일반의":
            continue
        date_str = get_val(row, ["진료개시일", "진료시작일", "진료일", "조제일자", "처방일"])
        code_raw = "" if ftype in ("detail", "pharma") else get_diagnosis_code(row)
        code_str = normalize_code(code_raw)
        if ftype == "detail":
            name_str = _detail_action_name(row)
        elif ftype == "pharma":
            name_str = get_val(row, ["약품명", "의약품명"])
        else:
            name_str = (
                get_diagnosis_name(row)
                or get_val(row, ["진료내역", "행위명"])
            )
        hospital = get_val(row, ["병·의원", "기관명", "요양기관명", "병·의원&약국"])
        in_out   = get_val(row, ["입내원구분", "입원외래구분", "입원", "외래", "구분"])
        m_days   = get_val(row, ["내원일수", "투약일수", "요양일수", "진료일수"])  # BOHUMFIT-124: 자동차 PDF '진료일수'
        cost_raw = get_val(row, ["총진료비", "진료비", "총 진료비"])

        if not date_str and not name_str: continue
        if ftype == "pharma" and not m_days: continue

        if ftype == "detail":
            act_name_raw = _detail_action_name(row)
            display_name = name_str[:20]
            act_norm = re.sub(r"[\s\d]", "", (act_name_raw or ""))[:15]
            dedup_key = (code_str, date_str, ftype, act_norm)
        else:
            display_name = name_str[:20]
            name_norm_dedup = re.sub(r"[\s\d]", "", name_str)[:15]
            dedup_key = (code_str or name_norm_dedup, date_str, ftype, "")
        if dedup_key in seen_code_dates:
            continue
        seen_code_dates.add(dedup_key)

        fname_row = str(row.get("_fname", "") or "")
        inpatient_flag = "입원" if "입원" in in_out else ""
        line_date = parse_date(date_str) or date_str

        act_suffix = ""
        if ftype == "detail":
            _act = _detail_action_name(row)
            if _act:
                act_suffix = f" 행위:{_act[:25]}"
        line_core = (
            f"{line_date} [{ftype}] {code_str} {display_name}{act_suffix} {hospital[:10]}"
            + (f" 투약{m_days}일" if m_days and m_days != "0" else "")
            + (f" 진료비{cost_raw}" if cost_raw else "")
            + (f" {inpatient_flag}" if inpatient_flag else "")
        )
        raw_entries.append((fname_row, line_core))

    del df
    gc.collect()

    lines_by_file: dict[str, list[str]] = defaultdict(list)
    for fname_row, tl in raw_entries:
        if fname_row:
            lines_by_file[fname_row].append(tl)

    return disease_stats, cross_surgery_hints, date_warnings, raw_entries, dict(lines_by_file)  # BOHUMFIT-043


def _medication_token(drug: str, ingredient_map: dict) -> tuple[str, float]:
    """Return a conservative medication identity for the current-confirmation check."""
    base, dose = extract_drug_info(drug)
    ingredient = normalize_ingredient(ingredient_map.get(drug, ""))
    identity = f"ingredient:{ingredient}" if ingredient else f"name:{base}"
    return identity, dose


def _current_confirmation_matches_before(disease: dict, drugs_before_90: set) -> bool:
    """True only when the latest confirmed prescription set exactly matches pre-90-day drugs.

    A temporary record inside the 90-day window must not make an unchanged current regimen
    a disclosure candidate. Missing or ambiguous latest data stays reportable by design.
    """
    seen_dates = disease.get("drug_last_seen_dates", {}) or {}
    valid_dates = [
        seen_date
        for seen_date in seen_dates.values()
        if isinstance(seen_date, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", seen_date)
    ]
    if not valid_dates:
        return False

    latest_date = max(valid_dates)
    current_drugs = {
        drug
        for drug, seen_date in seen_dates.items()
        if seen_date == latest_date and drug
    }
    if not current_drugs:
        return False

    ingredient_map = disease.get("drug_ingredient_map", {}) or {}
    current_tokens = {_medication_token(drug, ingredient_map) for drug in current_drugs}
    before_tokens = {_medication_token(drug, ingredient_map) for drug in drugs_before_90}
    return current_tokens == before_tokens


def detect_drug_changes(disease_stats: dict, today: datetime) -> list[dict]:
    """3개월 이내 처방약 변경 감지."""
    drug_change_summary: list[dict] = []

    for group_key, s in disease_stats.items():
        drugs_in_90     = s.get("drug_names_in_90", set())
        drugs_before_90 = s.get("drug_names_before_90", set())
        if not drugs_in_90 or not drugs_before_90:
            continue

        info_in_90     = {extract_drug_info(d)[0]: extract_drug_info(d)[1] for d in drugs_in_90}
        info_before_90 = {extract_drug_info(d)[0]: extract_drug_info(d)[1] for d in drugs_before_90}
        norm_in_90     = set(info_in_90.keys())
        norm_before_90 = set(info_before_90.keys())

        stopped_drugs   = norm_before_90 - norm_in_90
        new_drugs       = norm_in_90 - norm_before_90
        continued_drugs = norm_in_90 & norm_before_90
        dose_increased = []
        dose_decreased = []

        # BOHUMFIT-205: 동일 성분(성분명 기준) 브랜드 전환은 약 변경이 아니다.
        #   심평원 처방조제의 '성분명'으로 브랜드 키를 성분 키에 매핑해,
        #   3개월 이내 '새 약'이 실은 이전 복용약과 같은 성분(제네릭·상품명 교체)이면
        #   new/stopped 에서 제외하고 계속 복용으로 본다.
        #   (예: 디스펩틴정→모사프리엠정 = 모사프리드시트르산염수화물 동일 → 변경 아님)
        #   성분명이 없는 데이터(기본진료 유래 등)는 기존 브랜드 키 판정 그대로 둔다.
        _ing_map = s.get("drug_ingredient_map", {}) or {}
        if _ing_map and (new_drugs or stopped_drugs):
            def _ings_by_base(drugs: set) -> dict[str, set]:
                out: dict[str, set] = {}
                for _d in drugs:
                    _ing = normalize_ingredient(_ing_map.get(_d, ""))
                    if _ing:
                        out.setdefault(extract_drug_info(_d)[0], set()).add(_ing)
                return out
            _ings_in     = _ings_by_base(drugs_in_90)
            _ings_before = _ings_by_base(drugs_before_90)
            _ings_in_all     = {i for v in _ings_in.values() for i in v}
            _ings_before_all = {i for v in _ings_before.values() for i in v}

            _same_ingredient_new = set()
            for nd in new_drugs:
                if not (_ings_in.get(nd) and _ings_in[nd] <= _ings_before_all):
                    continue
                _same_ingredient_new.add(nd)
                _matched_before_bases = [
                    bd for bd, bd_ingredients in _ings_before.items()
                    if _ings_in[nd] & bd_ingredients
                ]
                _before_doses = [info_before_90.get(bd, 0) for bd in _matched_before_bases]
                _before_dose = max(_before_doses, default=0)
                _after_dose = info_in_90.get(nd, 0)
                # Same ingredient does not mean same regimen: retain a brand change that
                # also increases the confirmed dose as an escalation disclosure candidate.
                # Salt/hydrate notation can express the same active dose as e.g. 5mg vs
                # 5.29mg. Treat sub-10% variance as the same regimen; material increases
                # remain disclosure candidates.
                if _before_dose > 0 and _after_dose > _before_dose * 1.1:
                    dose_increased.append(f"{nd} ({_before_dose}→{_after_dose})")
                elif _before_dose > 0 and _after_dose < _before_dose / 1.1:
                    dose_decreased.append(f"{nd} ({_before_dose}→{_after_dose})")
            if _same_ingredient_new:
                new_drugs = new_drugs - _same_ingredient_new
                continued_drugs = continued_drugs | _same_ingredient_new
            # 반대 방향: 이전 브랜드가 사라졌어도 같은 성분을 계속 복용 중이면 '중단' 아님.
            stopped_drugs = {
                sd for sd in stopped_drugs
                if not (_ings_before.get(sd) and _ings_before[sd] <= _ings_in_all)
            }

        for drug_name in continued_drugs:
            dose_before = info_before_90.get(drug_name, 0)
            dose_after  = info_in_90.get(drug_name, 0)
            if dose_before > 0 and dose_after > 0:
                if dose_after > dose_before:
                    dose_increased.append(f"{drug_name} ({dose_before}→{dose_after})")
                elif dose_after < dose_before:
                    dose_decreased.append(f"{drug_name} ({dose_before}→{dose_after})")

        has_change = bool(new_drugs or dose_increased)
        # BOHUMFIT-205: 90일 안의 일시 처방으로 후보가 생겼어도, 가장 최근 확인 처방이
        # 90일 이전 복용약과 성분/용량까지 같으면 실제 약변경이 아니므로 고지 대상에서 제외한다.
        # 최신 확인 정보가 없거나 새 성분·증량이면 False가 되어 기존 민감도를 유지한다.
        if has_change and _current_confirmation_matches_before(s, drugs_before_90):
            continue
        if has_change or stopped_drugs:
            if new_drugs and stopped_drugs:
                change_type = "약 종류 변경"
            elif new_drugs:
                change_type = "새 약 추가"
            elif dose_increased:
                change_type = "용량 증가"
            else:
                change_type = "약 중단"

            if new_drugs or dose_increased:
                drug_change_summary.append({
                    "group":          group_key,
                    "name":           s.get("name", group_key),
                    "continued":      sorted(continued_drugs)[:3],
                    "stopped":        sorted(stopped_drugs)[:3],
                    "new":            sorted(new_drugs)[:3],
                    "dose_increased": sorted(dose_increased)[:3],
                    "dose_decreased": sorted(dose_decreased)[:3],
                    "change_type":    change_type,
                })
                disease_stats[group_key]["drug_change_in_3m"] = True

    return drug_change_summary


def compute_prescription_end_dates(
    disease_stats: dict,
    today: datetime,
) -> tuple[list[dict], datetime | None]:
    """3개월 이내 처방 종료일 계산.

    Returns:
        prescription_end_details : list[dict]
        earliest_available_date  : datetime | None
    """
    earliest_available_date = None
    prescription_end_details: list[dict] = []

    for group_key, s in disease_stats.items():
        med_dict = s["med_dates_pharma"] if s["has_pharma"] and s["med_dates_pharma"] else s["med_dates_basic"]
        if not med_dict:
            continue
        for presc_date_str, m_days_val in med_dict.items():
            if not presc_date_str or m_days_val <= 0:
                continue
            try:
                presc_dt = datetime.strptime(presc_date_str, "%Y-%m-%d")
            except ValueError:
                continue
            days_ago = (today - presc_dt).days
            if days_ago > 90:
                continue
            end_dt       = presc_dt + timedelta(days=m_days_val - 1)
            available_dt = end_dt + timedelta(days=1)
            prescription_end_details.append({
                "name":       s.get("name", group_key),
                "presc_date": presc_date_str,
                "m_days":     m_days_val,
                "end_date":   end_dt.strftime("%Y-%m-%d"),
                "available":  available_dt.strftime("%Y-%m-%d"),
                "already_ok": available_dt <= today,
            })
            if earliest_available_date is None or available_dt > earliest_available_date:
                earliest_available_date = available_dt

    return prescription_end_details, earliest_available_date
