# -*- coding: utf-8 -*-
"""BOHUMFIT-294 — 카카오 복사문 중복 문자열 생략 계약.

★고정하는 계약
  ① 직전 줄과 **글자 단위로 동일한** 코드·병명만 생략한다 — 값이 다르면 그대로 둔다(251 원문 충실화)
  ② 생략된 값은 **같은 블록 위쪽 줄에 반드시 존재**한다 → 정보 손실 0
  ③ 원문 값은 변형하지 않는다(절삭·정규화 0). 날짜·맥락·수술명·병원·동일일자 병기는 무변경
  ④ ★251 골든(record마다 코드·병명 상이)은 **압축 대상 0** — 기대 문자열이 그대로다(4경로 동등성 유지)
  ⑤ records 없는 구 데이터 폴백·입원 회차 근거·수술 0건 경로는 무변경

★PII: 전부 익명 합성 픽스처(실명·연락처·주민번호·주소 0건).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from main import _kakao_item

GOLDEN = json.loads(
    (Path(__file__).resolve().parent / "fixtures" / "disclosure_memo_parity_251.json").read_text(encoding="utf-8")
)


def _base(**over):
    item = {
        "first_date": "2023-02-05", "latest_date": "2024-01-07",
        "display_code": "L050", "code": "L05", "name": "합성질환A", "display_name": "합성질환A",
        "visit": 4, "med_days": 0, "inpatient": 0, "inpatient_count": 0, "inpatient_periods": [],
        "surgeries": [], "surgery_count": 0, "surgery_dates": [], "surgery_suspected": [],
        "surgery_suspected_grade": "", "detail": "5년 이내 통원", "hospitals": ["가나병원"],
        "surgery_records": [],
    }
    item.update(over)
    return item


def _rec(date, name_surgery, code="L050", name="합성질환A", context="통원1회", hospital="가나병원", co=None):
    return {"date": date, "code": code, "context": context, "name": name,
            "surgery_name": name_surgery, "hospital": hospital, "co_diagnoses": co or []}


def _lines(text):
    return [l for l in text.splitlines() if l.strip()]


# ── ④ ★4경로 골든 — 압축 대상 0이라 기대 문자열이 그대로여야 한다 ───────────────────
def test_golden_parity_unchanged_because_codes_differ_per_record():
    """251 골든은 record마다 코드·병명이 **다르다** — 294 규칙에서 생략되는 값이 하나도 없다."""
    assert _kakao_item(GOLDEN["surgery_item"]) == GOLDEN["surgery_item_expected"]
    records = GOLDEN["surgery_item"]["surgery_records"]
    assert len({r["code"] for r in records}) == len(records)     # 코드가 전부 다르다
    assert len({r["name"] for r in records}) == len(records)     # 병명도 전부 다르다


# ── ①② 헤더-상세 반복(A) — 생략하되 위쪽에 존재 ─────────────────────────────────
def test_repeated_code_and_name_are_omitted_but_present_in_the_header():
    item = _base(surgery_count=4, surgeries=["절개술", "배농술", "절제술", "봉합술"],
                 surgery_records=[_rec("2023-02-05", "절개술"), _rec("2023-07-21", "배농술"),
                                  _rec("2023-11-27", "절제술"), _rec("2024-01-07", "봉합술")])
    out = _kakao_item(item)
    lines = _lines(out)
    assert len(lines) == 5                                        # 헤더 1 + 건별 4 (줄 수는 그대로 — 삭제 아님)
    assert lines[0] == "2023-02-05 ~ 2024-01-07 / L050 / (양방)합성질환A"
    assert out.count("L050") == 1 and out.count("합성질환A") == 1   # ★같은 값이 5회 → 1회
    for line, surgery in zip(lines[1:], ("절개술", "배농술", "절제술", "봉합술")):
        assert "L050" not in line and "합성질환A" not in line
        assert "통원1회" in line and surgery in line and "가나병원" in line   # ③ 나머지 필드 무변경
    for date in ("2023-02-05", "2023-07-21", "2023-11-27", "2024-01-07"):
        assert date in out                                        # 날짜는 record마다 다르므로 전부 남는다


def test_omitted_values_always_appear_above_in_the_same_block():
    """② 정보 손실 0 — 어떤 줄에서 생략된 코드·병명도 블록 위쪽에서 이미 나왔다."""
    item = _base(surgery_count=3, surgeries=["절개술"],
                 surgery_records=[_rec("2023-02-05", "절개술"),
                                  _rec("2023-03-10", "배농술", code="L0292", name="합성질환B"),
                                  _rec("2023-04-01", "절제술", code="L0292", name="합성질환B")])
    out = _kakao_item(item)
    lines = _lines(out)
    # 2번째 record는 코드·병명이 바뀌었으므로 반드시 출력, 3번째는 같으므로 생략
    assert "L0292" in lines[2] and "합성질환B" in lines[2]
    assert "L0292" not in lines[3] and "합성질환B" not in lines[3]
    seen_codes, seen_names = set(), set()
    for line in lines:
        seen_codes |= set(re.findall(r"\b[A-Z]\d{2,5}\b", line))
        for candidate in ("합성질환A", "합성질환B"):
            if candidate in line:
                seen_names.add(candidate)
    assert {"L050", "L0292"} <= seen_codes and {"합성질환A", "합성질환B"} <= seen_names
    # 원문 집합 보존: 모든 record의 코드·병명이 문안 어딘가에 존재한다
    for r in item["surgery_records"]:
        assert r["code"] in out and r["name"] in out


# ── ① 251 의도분 보존 ────────────────────────────────────────────────────────
def test_same_day_multiple_codes_are_never_collapsed():
    """동일일자 복수코드(251 ③) — 코드·병명이 다르므로 생략 0."""
    item = _base(first_date="2023-02-05", latest_date="2023-02-05", surgery_count=2,
                 surgeries=["절개술", "배농술"], display_code="L0221·L0292",
                 surgery_records=[_rec("2023-02-05", "절개술", code="L0221", name="가나부위농양", hospital="가나병원"),
                                  _rec("2023-02-05", "배농술", code="L0292", name="다라부위농양",
                                       context="입원3일", hospital="다라의원", co=["K610 합성병기"])])
    out = _kakao_item(item)
    for token in ("L0221", "L0292", "가나부위농양", "다라부위농양", "동일일자 진단: K610 합성병기"):
        assert token in out
    assert len(_lines(out)) == 3


def test_inpatient_period_lines_are_never_compressed():
    """⑤ ★입원 회차줄은 **압축하지 않는다** — 205(회차 분리)·213(회차별 근거)는 회차마다 자기완결이어야
    한다는 별도 설계다. 뒤따르는 수술 record 줄만 중복을 생략한다."""
    item = _base(
        visit=0, inpatient=17, surgery_count=2, surgeries=["절개술", "배농술"],
        inpatient_periods=[
            {"start": "2023-02-05", "end": "2023-02-08", "days": 4, "hospital": "가나병원"},
            {"start": "2023-03-22", "end": "2023-03-27", "days": 6, "hospital": "가나병원"},
            {"start": "2024-01-07", "end": "2024-01-13", "days": 7, "hospital": "가나병원"},
        ],
        surgery_records=[_rec("2023-02-05", "절개술", context="입원4일"),
                         _rec("2023-03-22", "배농술", context="입원6일")],
    )
    out = _kakao_item(item)
    lines = _lines(out)
    assert len(lines) == 6                                  # 회차 3 + 합산 1 + 건별 2
    assert lines[0] == "2023-02-05 ~ 2023-02-08 / 입원4일 / L050 / (양방)합성질환A / 가나병원"
    assert lines[1] == "2023-03-22 ~ 2023-03-27 / 입원6일 / L050 / (양방)합성질환A / 가나병원"   # ★회차줄 무압축
    assert lines[2] == "2024-01-07 ~ 2024-01-13 / 입원7일 / L050 / (양방)합성질환A / 가나병원"
    assert lines[3] == "→ 입원 총 3회 · 합산 17일"                        # 회차 근거 무변경
    assert lines[4] == "2023-02-05 / 입원4일 / 절개술 / 가나병원"          # record 줄만 생략
    assert lines[5] == "2023-03-22 / 입원6일 / 배농술 / 가나병원"
    assert out.count("L050") == 3 and out.count("합성질환A") == 3          # 회차 3줄 유지
    for token in ("2024-01-07 ~ 2024-01-13", "입원7일", "입원4일", "입원6일"):
        assert token in out


# ── ⑤ 무변경 경로 ────────────────────────────────────────────────────────────
def test_legacy_payload_without_records_is_unchanged():
    """구 데이터 폴백(records 0) — 종전 한 줄 형식 그대로."""
    item = _base(surgery_count=2, surgeries=["절개술", "배농술"], surgery_records=[])
    out = _kakao_item(item)
    assert out == ("2023-02-05 ~ 2024-01-07 / 통원4회 / L050 / (양방)합성질환A / 가나병원\n"
                   "절개술, 배농술\n\n")


def test_no_surgery_item_is_unchanged():
    """수술 0건 — 판정 상세 줄 경로 무변경."""
    out = _kakao_item(_base())
    assert out.startswith("2023-02-05 ~ 2024-01-07 / 통원4회 / L050 / (양방)합성질환A / 가나병원\n")
    assert "L050" in out and "합성질환A" in out


def test_single_diagnosis_single_surgery_keeps_everything():
    """단일 진단 1시술 — 생략할 직전 값이 헤더뿐이라 record 줄은 날짜/맥락/수술명/병원만 남는다."""
    item = _base(surgery_count=1, surgeries=["절개술"], surgery_records=[_rec("2023-02-05", "절개술")])
    lines = _lines(_kakao_item(item))
    assert lines == ["2023-02-05 ~ 2024-01-07 / L050 / (양방)합성질환A",
                     "2023-02-05 / 통원1회 / 절개술 / 가나병원"]
