# -*- coding: utf-8 -*-
"""BOHUMFIT-251 회귀 — 고지 문안 원문 충실화(익명 합성 픽스처 · 실명 0).

정*규 실측 구조의 익명 재현: ① 원문 코드 보존(절삭 금지 — 표시 시 양·한방 접두만 제거)
② 수술 건별 전개(세부진료 행 단위) ③ 동일 일자 복수 진단 병기 ④ 셀 개행 공백 아티팩트 정리.
판정 로직(061 그룹핑·수술 확정 임계)은 불변 — 표시 필드만 검증한다.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import main
from pipeline.disease_aggregator import build_disease_stats
from pipeline.helpers import display_clean_text, display_raw_code

TODAY = datetime(2026, 7, 27)

_PARITY_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "disclosure_memo_parity_251.json")


# ── 표시 헬퍼 단위 ──────────────────────────────────────────────
def test_display_raw_code_strips_only_medium_prefix():
    assert display_raw_code("AL050") == "L050"       # 양방 접두 제거
    assert display_raw_code("BK610") == "K610"       # 한방 접두 제거
    assert display_raw_code("L0221") == "L0221"      # 접두 없는 원문 그대로
    assert display_raw_code("AL0292") == "L0292"
    # 절삭·정규화는 하지 않는다(L05로 줄이지 않음).
    assert display_raw_code("AL02211") == "L02211"


def test_display_clean_text_joins_hangul_wrap_artifacts_only():
    assert display_clean_text("농 양이있는 모소낭") == "농양이있는모소낭"
    assert display_clean_text("대구파티마병 원") == "대구파티마병원"
    assert display_clean_text("수술팩(Ⅱ)(마취시간 1시 간초과)") == "수술팩(Ⅱ)(마취시간 1시간초과)"
    # 영문·숫자 경계 공백은 보존(원문 왜곡 방지).
    assert display_clean_text("절개술 1cm이상~2cm 미만") == "절개술 1cm이상~2cm 미만"


# ── 집계 통합(합성 행 — 정*규 구조의 익명 재현) ────────────────────
def _basic(date, code, name, in_out="외래", days=1, cost="18,000", hosp="가나병 원"):
    return {
        "_ftype": "basic", "_fname": "합성.pdf",
        "진료시작일": date, "주상병코드": code, "주상병명": name,
        "병·의원&약국": hosp, "입원/외래": in_out, "내원일수": str(days),
        "총진료비(건강보험적용분)": cost,
    }


def _detail(date, act_name, code="", hosp="가나병 원"):
    row = {
        "_ftype": "detail", "_fname": "합성세부.pdf",
        "진료시작일": date, "병·의원&약국": hosp,
        "진료내역": "처치및수술 (양방)", "코드명": act_name,
    }
    if code:
        row["주상병코드"] = code
    return row


def _stats():
    records = [
        # 2023-02-05: 모소낭 입원 4일(고액) + 동일 일자 항문농양 외래 — ③ 병기 표적.
        _basic("2023-02-05", "AL050", "(양방)농 양이있는 모소낭", in_out="입원", days=4, cost="1,000,000"),
        _basic("2023-02-05", "AK610", "(양방)항 문농양"),
        # 2022-11-08: 다른 병명(몸통의종기) — 그룹 대표명과 날짜별 원문 병명 분리 표적.
        _basic("2022-11-08", "AL0221", "(양방)몸 통의종기", cost="600,000"),
        # 세부진료 수술 행(주상병코드 병기형 — 건별 전개 원천).
        _detail("2023-02-05", "절개술(안면과경부이외, 제1범위,1cm이상~2cm 미만)", code="AL050"),
        _detail("2022-11-08", "절개술(안면과경부이외, 제1범위,1cm미만)", code="AL0221"),
    ]
    stats, *_rest = build_disease_stats(records, TODAY)
    return stats


def test_raw_codes_preserved_without_truncation():
    stats = _stats()
    l05 = next(s for k, s in stats.items() if s.get("diag_code") == "L05")
    # 내부 그룹 키는 061 설계대로 3자리 유지, 원문 코드는 별도 보존(절삭 0).
    assert "AL050" in l05["raw_codes"]
    l02 = next(s for k, s in stats.items() if s.get("diag_code") == "L02")
    assert "AL0221" in l02["raw_codes"]


def test_surgery_records_per_event_with_original_fields():
    stats = _stats()
    l05 = next(s for k, s in stats.items() if s.get("diag_code") == "L05")
    records = l05.get("surgery_records") or []
    assert records, "수술 건별 기록이 비어 있음(확정 경로 회귀)"
    rec = next(r for r in records if r["date"] == "2023-02-05")
    assert rec["code"] == "L050"                      # 표시 접두 제거·절삭 없음
    assert rec["name"] == "농양이있는모소낭"            # 날짜별 원문 병명 + 아티팩트 정리
    assert "절개술" in rec["surgery_name"]
    assert rec["context"] == "입원4일"
    assert rec["hospital"] == "가나병원"               # 병원명 아티팩트 정리
    # ③ 동일 일자 복수 진단 병기 — 항문농양(K610) 표기.
    assert any("K610" in co and "항문농양" in co for co in rec.get("co_diagnoses") or [])


def test_date_specific_diagnosis_name_not_group_name():
    stats = _stats()
    l02 = next(s for k, s in stats.items() if s.get("diag_code") == "L02")
    records = l02.get("surgery_records") or []
    rec = next((r for r in records if r["date"] == "2022-11-08"), None)
    assert rec is not None
    assert rec["name"] == "몸통의종기"                 # 그룹 대표명이 아닌 그 날짜의 원문 병명
    assert rec["code"] == "L0221"


# ── 회송 보정(교차 오염 제거 — Codex 요구 회귀) ─────────────────────────────────
def _stats_full(records):
    stats, *_rest = build_disease_stats(records, TODAY)
    unassigned = _rest[-1]
    return stats, unassigned


def test_cross_hospital_no_contamination():
    """★동일 날짜 + 병원A(그룹X 수술) + 병원B(그룹Y 수술 없음) — Y 문안에 X 수술 미기재."""
    records = [
        _basic("2024-05-05", "AX100", "(양방)가나질환", cost="700,000", hosp="가나병 원"),
        _basic("2024-05-05", "AY200", "(양방)다라질환", cost="700,000", hosp="다라의 원"),
        _detail("2024-05-05", "절개술(제1범위,1cm미만)", hosp="가나병 원"),
    ]
    stats, unassigned = _stats_full(records)
    x = next(s for s in stats.values() if s.get("diag_code") == "X10")
    y = next(s for s in stats.values() if s.get("diag_code") == "Y20")
    x_records = x.get("surgery_records") or []
    y_records = y.get("surgery_records") or []
    assert any("절개술" in r["surgery_name"] for r in x_records)     # 그룹X에만 기재
    assert not any("절개술" in r["surgery_name"] for r in y_records)  # ★그룹Y 오염 0
    assert y.get("surgery_dates") == set() or not y_records
    # co 병기도 (날짜, 병원) 이벤트 키 — 타 병원 진단은 병기되지 않는다.
    for r in x_records:
        assert not any("Y200" in co for co in r.get("co_diagnoses") or [])
    assert unassigned == []  # 링크 성립 — 미특정 없음


def test_same_day_same_hospital_different_types_follows_pipeline_link():
    """동일 날짜·동일 병원·형태 상이(입원 L05 + 외래 K61 — 정*규형): 판정과 동일한
    링크 규칙(첫 기본행 귀속)을 따르고, 타 진단은 co_diagnoses로 병기(사실성 보존)."""
    records = [
        _basic("2023-02-05", "AL050", "(양방)농 양이있는 모소낭", in_out="입원", days=4,
               cost="1,000,000", hosp="가나병 원"),
        _basic("2023-02-05", "AK610", "(양방)항 문농양", hosp="가나병 원"),
        _detail("2023-02-05", "절개술(제1범위,1cm이상~2cm 미만)", hosp="가나병 원"),
    ]
    stats, unassigned = _stats_full(records)
    l05 = next(s for s in stats.values() if s.get("diag_code") == "L05")
    k61 = next(s for s in stats.values() if s.get("diag_code") == "K61")
    l05_records = l05.get("surgery_records") or []
    assert any("절개술" in r["surgery_name"] for r in l05_records)   # 첫 기본행(L05) 귀속
    assert not (k61.get("surgery_records") or [])                    # ★K61 오염 0
    rec = next(r for r in l05_records if r["date"] == "2023-02-05")
    assert any("K610" in co and "항문농양" in co for co in rec["co_diagnoses"])  # 병기 유지
    assert unassigned == []


def test_unlinked_detail_surgery_goes_to_unassigned_block():
    """링크 불성립(같은 날짜·병원의 기본행 없음) 수술행 — 오귀속 대신 그룹 미특정 블록."""
    records = [
        _basic("2024-05-05", "AX100", "(양방)가나질환", cost="700,000", hosp="가나병 원"),
        # 다른 병원의 세부 수술행 — 어떤 기본행과도 (날짜+병원) 링크 불가.
        _detail("2024-05-05", "절제술(림프절)", hosp="무연고병 원"),
    ]
    stats, unassigned = _stats_full(records)
    for s in stats.values():
        for r in s.get("surgery_records") or []:
            assert "절제술" not in r["surgery_name"]                  # ★어느 그룹에도 미기재
    assert len(unassigned) == 1
    assert unassigned[0]["surgery_name"].startswith("절제술")
    assert unassigned[0]["hospital"] == "무연고병원"                  # 아티팩트 공백 정리
    assert unassigned[0]["date"] == "2024-05-05"


# ── 3차 회송 보정(Codex 재반려 3결함 회귀) ──────────────────────────────────────
def test_same_group_same_day_two_hospitals_no_substitution():
    """★결함 1: 같은 그룹·같은 날짜·다른 병원 2수술 — 2번째 이벤트의 코드·병명·
    입원/통원 맥락이 첫 이벤트 값으로 치환되지 않고 각자 보존되어야 한다."""
    records = [
        _basic("2024-05-05", "AX101", "(양방)가나질 환", cost="700,000", hosp="가나병 원"),
        _basic("2024-05-05", "AX102", "(양방)다라질 환", in_out="입원", days=3,
               cost="900,000", hosp="다라의 원"),
        _detail("2024-05-05", "절개술(제1범위,1cm미만)", hosp="가나병 원"),
        _detail("2024-05-05", "배농술(제2범위)", hosp="다라의 원"),
    ]
    stats, unassigned = _stats_full(records)
    x = next(s for s in stats.values() if s.get("diag_code") == "X10")
    recs = x.get("surgery_records") or []
    assert len(recs) == 2, f"건별 record 2건 기대, 실제 {len(recs)}"
    rec_a = next(r for r in recs if "절개술" in r["surgery_name"])
    rec_b = next(r for r in recs if "배농술" in r["surgery_name"])
    # 각 이벤트의 원문 코드·병명·맥락 — 첫 행 승자 치환 0.
    assert rec_a["code"] == "X101" and rec_a["name"] == "가나질환"
    assert rec_a["context"] == "통원1회" and rec_a["hospital"] == "가나병원"
    assert rec_b["code"] == "X102" and rec_b["name"] == "다라질환"
    assert rec_b["context"] == "입원3일" and rec_b["hospital"] == "다라의원"
    # co 병기도 자기 병원 이벤트로 한정(타 병원 진단 미병기).
    assert not any("X102" in co for co in rec_a["co_diagnoses"])
    assert not any("X101" in co for co in rec_b["co_diagnoses"])
    assert unassigned == []


def test_kakao_message_unassigned_only_still_outputs_block():
    """★결함 2: 일반 고지 0건 + 미특정 수술만 존재 — 조기 종료로 블록이 소실되지 않는다."""
    unassigned = [{"date": "2024-05-05", "surgery_name": "절제술(림프절)", "hospital": "무연고병원"}]
    msg = main._build_kakao_message("간편심사", TODAY, {}, unassigned)
    assert "고지 대상 없음" not in msg
    assert "[수술 내역(그룹 미특정)]" in msg
    assert "2024-05-05 / 절제술(림프절) / 무연고병원" in msg


def test_kakao_message_no_target_only_when_both_empty():
    msg = main._build_kakao_message("간편심사", TODAY, {}, [])
    assert "고지 대상 없음" in msg


def test_kakao_item_summary_line_drops_visit_aggregate_when_records():
    """★결함 3(서버): 건별 전개 그룹의 합산 줄에서 '통원N회' 수술 합산 제거 —
    진단 요약(기간/코드/병명)은 유지, 건별 record와 중복 0."""
    with open(_PARITY_FIXTURE, encoding="utf-8") as f:
        fx = json.load(f)
    out = main._kakao_item(fx["surgery_item"])
    assert "통원5회" not in out                       # 합산 중복 제거
    assert out.count("2023-02-05 / L0221") == 1       # 건별은 1회씩만
    assert out.splitlines()[0] == "2023-02-05 ~ 2023-03-10 / L0221·L0292 / (양방)합성질환"


def test_kakao_item_keeps_inpatient_period_lines_with_records():
    """입원 회차별 줄(periods)은 합산이 아니라 회차 근거 — records가 있어도 유지."""
    item = {
        "first_date": "2023-02-05", "latest_date": "2023-02-09",
        "display_code": "L050", "code": "L05", "name": "합성질환", "display_name": "합성질환",
        "visit": 0, "med_days": 0, "inpatient": 4, "inpatient_count": 1,
        "inpatient_periods": [{"start": "2023-02-05", "end": "2023-02-09", "days": 4, "hospital": "가나병원"}],
        "surgeries": ["절개술(제1범위)"], "surgery_count": 1, "surgery_dates": ["2023-02-05"],
        "surgery_suspected": [], "surgery_suspected_grade": "", "detail": "", "hospitals": ["가나병원"],
        "surgery_records": [{"date": "2023-02-05", "code": "L050", "context": "입원4일",
                             "name": "합성질환", "surgery_name": "절개술(제1범위)",
                             "hospital": "가나병원", "co_diagnoses": []}],
    }
    out = main._kakao_item(item)
    assert "2023-02-05 ~ 2023-02-09 / 입원4일 / L050 / (양방)합성질환" in out  # 회차 줄 유지
    assert "절개술(제1범위)" in out                                           # 건별 전개 유지


def test_kakao_item_parity_golden():
    """★4경로 정합: 서버 _kakao_item 출력 = 골든(프런트 memoItem도 동일 골든과 대조 —
    src/lib/disclosureMemo.test.ts). 형식 변경 시 골든·양쪽 테스트 동시 갱신."""
    with open(_PARITY_FIXTURE, encoding="utf-8") as f:
        fx = json.load(f)
    assert main._kakao_item(fx["surgery_item"]) == fx["surgery_item_expected"]
    msg = main._build_kakao_message("간편심사", TODAY, {}, fx["unassigned"])
    assert fx["unassigned_block_expected"] in msg
