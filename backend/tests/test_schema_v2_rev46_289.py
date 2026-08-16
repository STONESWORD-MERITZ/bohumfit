# -*- coding: utf-8 -*-
"""BOHUMFIT-289(S1b) → BOHUMFIT-290(S2 Step 0) — V2 스키마 46 → **49행** + 지급 케스케이드·분배 상수.

★287과 같은 원칙이다: **정의만 하고 어디에도 배선하지 않는다.**
  케스케이드·분배는 "지급이 이렇게 번진다"는 **데이터**일 뿐, 이 태스크에서 계산에 쓰이지 않는다.

★고정하는 계약
  ①46행 전문이 신판 수기표(`컨설팅 전`/`컨설팅 후`)와 문자열 단위로 같다
  ②암 대분류가 11행이고 Q3 폐기(세기조절·양성자·중입자 3행 분리)가 반영돼 있다
  ③케스케이드는 무순환·자기 포함·접두 폐쇄이고, 참조 row_id가 전부 실재한다
  ④★`심 장 질 환`·일반암·유사암은 케스케이드에 **없다**(Human 확정 — 독립 행)
  ⑤분배 규칙 2종의 대상 행이 실재하고, 확인 안 된 부분은 규칙이 아니라 **미해결 목록**에 있다
  ⑥`L ` 접두는 케스케이드 **하위 행**에만 붙는다(신판 `최종` 시트 실측과 일치)
"""
from __future__ import annotations

from pathlib import Path

import pytest

from coverage.constants import (
    CASCADE_CASE_LABEL_V2,
    CASCADE_CASE_ROW_V2,
    CASCADE_CHILD_PREFIX_V2,
    CASCADE_INDEPENDENT_V2,
    DISTRIBUTION_EQUAL_V2,
    DISTRIBUTION_RULES_V2,
    DISTRIBUTION_UNRESOLVED_V2,
    GROUP12_V2,
    KB_COVERAGES_V2,
    PAYOUT_CASCADE_V2,
    SHEET_NAME_AFTER_V2,
    SHEET_NAME_BEFORE_V2,
    STANDARD_COUNT_V2,
)

# ── 신판 46행 실측(`컨설팅 전`·`컨설팅 후` 두 시트 r7~r52 · 완전 일치) ────────
EXPECTED_DISPLAY_46: tuple[str, ...] = (
    "상 해/질 병 입 원", "상 해/질 병 통 원 약 제",
    "상 해 수 술 비", "질 병 수 술 비",
    "1종 수술비 (질병 I 상해)", "2종 수술비 (질병 I 상해)", "3종 수술비 (질병 I 상해)",
    "4종 수술비 (질병 I 상해)", "5종 수술비 (질병 I 상해)",
    "뇌혈관 수술비", "심장질환 수술비",
    # ★암 11행 — 289 재설계의 핵심
    "암 진 단 비(일반암)", "유 사 암 진 단 비",
    "암 수 술 (레보아이 포함)", "유사암 수술", "다빈치 로봇 수술", "다빈치 특정암",
    "항암 약물 치료", "표적 약물 치료", "면역 약물 치료",
    "방사선 치료", "세기조절 방사선 치료", "양성자 방사선 치료", "중 입 자 치료",
    "뇌 혈 관 질 환", "뇌 졸 중", "뇌 출 혈",
    "심 장 질 환", "허혈성 심장질환", "급성심근경색", "순환계 치료비",
    "상 해 입 원", "질 병 입 원", "1 인 실 입 원", "간 병 인",
    "일 반 사 망", "상 해 사 망", "질 병 사 망",
    "상해 질병 후 유 장 해 80%", "상 해 후 유 장 해 3%", "질 병 후 유 장 해 3%",
    "골 절 진 단 비", "골 절 수 술 비", "깁스치료비",
    "일 상 생 활 배 상 책 임",
    "형 사 합 의 금", "변 호 사 선 임", "벌 금", "자 부 상",
)


# ── ① 46행 골격 ──────────────────────────────────────────────────────────
# ★BOHUMFIT-290(Step 0): 신판 46행 + 3행(유사암 수술·다빈치 특정암·순환계 치료비) = **49행**.
#   신판 파일에는 이 3행이 없으므로 원본 대조 테스트는 그 3행을 **빼고** 비교한다.
ROWS_ADDED_IN_290 = ("유사암 수술", "다빈치 특정암", "순환계 치료비")


def test_forty_nine_rows_in_sheet_order():
    assert STANDARD_COUNT_V2 == 49
    assert len(EXPECTED_DISPLAY_46) == 49
    assert tuple(row.display for row in KB_COVERAGES_V2) == EXPECTED_DISPLAY_46


def test_cancer_group_has_eleven_rows():
    """★암 7행 → 11행. 묶여 있던 수술·약물·방사선이 전부 풀렸다."""
    cancer = [row.display for row in KB_COVERAGES_V2 if row.group == "암"]
    assert len(cancer) == 13  # ★290: 11 + 유사암 수술 + 다빈치 특정암
    assert cancer[2:6] == ["암 수 술 (레보아이 포함)", "유사암 수술", "다빈치 로봇 수술", "다빈치 특정암"]
    assert cancer[6:9] == ["항암 약물 치료", "표적 약물 치료", "면역 약물 치료"]
    assert cancer[9:] == ["방사선 치료", "세기조절 방사선 치료", "양성자 방사선 치료", "중 입 자 치료"]


def test_q3_is_retired_three_radiation_rows_are_separate():
    """★Q3 폐기: `세기조절 / 양성자`·`중입자 / 정위` 묶음 표기가 사라졌다."""
    displays = {row.display for row in KB_COVERAGES_V2}
    assert "세기조절 / 양성자 방사선" not in displays
    assert "중입자 / 정위 방사선" not in displays
    assert {"세기조절 방사선 치료", "양성자 방사선 치료", "중 입 자 치료"} <= displays


def test_group_count_unchanged_at_eleven():
    """행이 늘어도 **대분류는 11개 그대로**다(암 안에서만 늘었다)."""
    assert len(GROUP12_V2) == 11
    assert set(row.group for row in KB_COVERAGES_V2) == set(GROUP12_V2)


def test_row_flags_survive_the_revision():
    """★개정이 기존 행 성격을 흔들지 않았는지 — 2열 5행·합계제외 1행·Y/N 7행."""
    assert [r.row_id for r in KB_COVERAGES_V2 if r.dual_column] == [
        f"tier_surgery_{tier}" for tier in range(1, 6)
    ] + ["caregiver"]  # ★290: 간병인 상해|질병 2열(Human)
    assert [r.row_id for r in KB_COVERAGES_V2 if r.sum_excluded] == ["disability_80"]
    assert len([r for r in KB_COVERAGES_V2 if r.yn_source]) == 7


def test_sheet_names_follow_the_new_workbook():
    assert (SHEET_NAME_BEFORE_V2, SHEET_NAME_AFTER_V2) == ("컨설팅 전", "컨설팅 후")


# ── ② 케스케이드 ─────────────────────────────────────────────────────────
def test_cascade_targets_all_exist():
    ids = {row.row_id for row in KB_COVERAGES_V2}
    for key, chain in PAYOUT_CASCADE_V2.items():
        # ★290: 키는 row_id이거나 **케이스 id**(다빈치 3분류)다.
        assert key in ids or key in CASCADE_CASE_ROW_V2, key
        for target in chain:
            assert target in ids, (key, target)


def test_case_keys_end_at_their_landing_row():
    """★다빈치 3분류 — 케이스 체인의 마지막 행 = 착지 행."""
    for case, landing in CASCADE_CASE_ROW_V2.items():
        assert PAYOUT_CASCADE_V2[case][-1] == landing
        assert case in CASCADE_CASE_LABEL_V2


def test_every_chain_ends_with_itself():
    """★자기 포함 — 진단이 나면 그 담보 자신이 먼저 지급된다(케이스 키는 착지 행으로)."""
    for key, chain in PAYOUT_CASCADE_V2.items():
        assert chain[-1] == CASCADE_CASE_ROW_V2.get(key, key), key
        assert len(set(chain)) == len(chain), f"{key} 체인에 중복이 있다"


def test_chains_are_prefix_closed_which_proves_acyclicity():
    """★무순환 증명 — 체인에 들어간 상위 행의 체인이 **자기 체인의 부분집합**이어야 한다.

    이게 성립하면 상위→하위 방향이 일관되어 순환이 생길 수 없다.
    """
    for key, chain in PAYOUT_CASCADE_V2.items():
        for parent in chain[:-1]:
            parent_chain = PAYOUT_CASCADE_V2.get(parent, (parent,))
            assert set(parent_chain) <= set(chain), f"{key} ⊅ {parent} 체인"
            assert key not in parent_chain, f"{key}와 {parent}가 서로를 물고 있다(순환)"


def test_brain_and_heart_chains_match_the_confirmed_table():
    assert PAYOUT_CASCADE_V2["cerebral_hemorrhage"] == (
        "cerebral_disease", "stroke", "cerebral_hemorrhage",
    )
    assert PAYOUT_CASCADE_V2["stroke"] == ("cerebral_disease", "stroke")
    assert PAYOUT_CASCADE_V2["cerebral_disease"] == ("cerebral_disease",)
    assert PAYOUT_CASCADE_V2["acute_mi"] == ("ischemic_heart", "acute_mi")
    assert PAYOUT_CASCADE_V2["ischemic_heart"] == ("ischemic_heart",)


def test_davinci_three_way_cascade():
    """★290 Human 확정: 다빈치 종별 3분류. 289 단일 체인은 일반암 케이스로 흡수."""
    assert PAYOUT_CASCADE_V2["davinci_general"] == ("cancer_surgery", "cancer_surgery_davinci")
    assert PAYOUT_CASCADE_V2["davinci_prostate"] == ("cancer_surgery", "cancer_surgery_davinci_specific")
    assert PAYOUT_CASCADE_V2["davinci_thyroid"] == ("cancer_minor_surgery", "cancer_surgery_davinci_specific")
    assert "cancer_surgery_davinci" not in PAYOUT_CASCADE_V2, "행 키 단일 체인은 폐기됐다"


def test_cancer_chains_match_the_confirmed_table():
    assert PAYOUT_CASCADE_V2["cancer_drug_immune"] == (
        "cancer_drug", "cancer_drug_targeted", "cancer_drug_immune",
    )
    assert PAYOUT_CASCADE_V2["cancer_drug_targeted"] == ("cancer_drug", "cancer_drug_targeted")


def test_radiation_siblings_do_not_accumulate():
    """★형제 비누적 — 세기조절·양성자·중입자는 서로를 포함하지 않는다."""
    siblings = ("radio_imrt", "radio_proton", "radio_carbon")
    for row_id in siblings:
        chain = PAYOUT_CASCADE_V2[row_id]
        assert chain == ("cancer_radiation", row_id)
        for other in siblings:
            if other != row_id:
                assert other not in chain, f"{row_id} 체인이 형제 {other}를 물고 있다"


def test_independent_rows_have_no_chain():
    """★★Human 확정 — `심 장 질 환`은 케스케이드 **밖**이다. 일반암·유사암도 독립이다.

    여기에 체인이 생기면 심장질환 담보가 허혈성·급성과 함께 지급되는 것으로 잘못 계산된다.
    """
    assert CASCADE_INDEPENDENT_V2 == (
        "cardiac_disease", "cancer_general", "cancer_minor", "circulatory_treatment",
    )
    for row_id in CASCADE_INDEPENDENT_V2:
        assert row_id not in PAYOUT_CASCADE_V2, f"{row_id}에 체인이 생겼다"
        for chain in PAYOUT_CASCADE_V2.values():
            assert row_id not in chain, f"{row_id}가 다른 체인에 끌려 들어갔다"


def test_cascade_child_prefix_matches_the_final_sheet():
    """★신판 `최종` 시트 실측: `L 뇌 졸 중`·`L 뇌 출 혈`·`L 급 성 심 근 경 색`.

    루트(뇌혈관질환·허혈성)와 독립 행(심장질환)에는 접두가 없었다 — 체인 정의와 정확히 맞물린다.
    """
    assert CASCADE_CHILD_PREFIX_V2 == "L "
    children = {k for k, chain in PAYOUT_CASCADE_V2.items() if len(chain) > 1}
    roots = {k for k, chain in PAYOUT_CASCADE_V2.items() if len(chain) == 1}
    assert {"stroke", "cerebral_hemorrhage", "acute_mi"} <= children
    assert {"cerebral_disease", "ischemic_heart"} <= roots
    assert "cardiac_disease" not in children | roots


# ── ③ 분배 규칙 ──────────────────────────────────────────────────────────
def test_distribution_targets_exist_and_are_equal_mode():
    ids = {row.row_id for row in KB_COVERAGES_V2}
    assert len(DISTRIBUTION_RULES_V2) == 3  # ★290: 본체 규칙 추가
    for rule in DISTRIBUTION_RULES_V2:
        assert rule.mode == DISTRIBUTION_EQUAL_V2
        assert rule.targets, rule.rule_id
        for target in rule.targets:
            assert target in ids, (rule.rule_id, target)


def test_major_treatment_rule_fills_three_rows():
    """★`암 주요치료비` 한 담보가 암수술·항암약물·방사선 3행을 동액으로 채운다(Human 확정)."""
    rule = next(r for r in DISTRIBUTION_RULES_V2 if r.rule_id == "major_treatment")
    assert rule.source == "암 주요치료비"
    assert rule.targets == ("cancer_surgery", "cancer_drug", "cancer_radiation")


def test_q8_rule_covers_only_the_verified_surgery_part():
    """★Q8형은 **확인된 부분만** 규칙으로 만들었다 — 약관 내역의 '수술' 항목 → r16·r17."""
    rule = next(r for r in DISTRIBUTION_RULES_V2 if r.rule_id == "integrated_treatment_surgery")
    assert rule.targets == ("surgery_cerebral", "surgery_cardiac")


def test_unresolved_is_now_empty_and_body_lands_on_circulatory_row():
    """★290: 289가 주차한 미해결분이 해소됐다 — 본체 착지 = `circulatory_treatment`(Human 확정)."""
    from coverage.constants import DISTRIBUTION_PATTERN_RULE_V2

    assert DISTRIBUTION_UNRESOLVED_V2 == ()
    body = next(r for r in DISTRIBUTION_RULES_V2 if r.rule_id == "integrated_treatment_body")
    assert body.targets == ("circulatory_treatment",)
    assert "Q8형" in DISTRIBUTION_PATTERN_RULE_V2 and "주요치료비형" in DISTRIBUTION_PATTERN_RULE_V2


# ── ④ ★무배선 유지 (케스케이드·분배 포함) ────────────────────────────────
def test_distribution_rules_are_still_not_wired_but_cascade_is():
    """★BOHUMFIT-290(S2): 케스케이드는 배선됐고(aggregator.compute_stage_totals), **분배 규칙은 아직 아니다**(S4).
    파서(`proposal_parser.py`)는 어느 V2 상수도 참조하지 않는다(파싱 로직 무접촉)."""
    root = Path(__file__).resolve().parents[1] / "coverage"
    aggregator = (root / "aggregator.py").read_text(encoding="utf-8")
    assert "PAYOUT_CASCADE_V2" in aggregator
    for name in ("aggregator.py", "export_excel.py", "export_pdf.py", "proposal_parser.py", "compare.py"):
        text = (root / name).read_text(encoding="utf-8")
        assert "DISTRIBUTION_RULES_V2" not in text, f"{name}이 분배 규칙을 참조한다 — S4 범위다"
    parser = (root / "proposal_parser.py").read_text(encoding="utf-8")
    assert "_V2" not in parser


# ── ⑤ 신판 수기표 원본 대조(파일이 있을 때만) ────────────────────────────
MANUAL_DIR = Path(__file__).resolve().parents[2] / "보장분석" / "비교분석표"


def _new_manual() -> Path:
    matches = sorted(MANUAL_DIR.glob("* - 민규.xlsx"))
    return matches[0] if matches else MANUAL_DIR / "manual-rev46-missing.xlsx"


@pytest.mark.parametrize("sheet", (SHEET_NAME_BEFORE_V2, SHEET_NAME_AFTER_V2))
def test_display_names_match_the_new_workbook(sheet: str):
    """★상수만 보고 자기 자신을 검증하지 않기 위해 원본과 직접 대조한다."""
    path = _new_manual()
    if not path.exists():
        pytest.skip(f"수기 엑셀 없음(gitignore 폴더): {path.name}")
    openpyxl = pytest.importorskip("openpyxl")
    worksheet = openpyxl.load_workbook(path, data_only=True)[sheet]
    actual = tuple(str(worksheet.cell(row, 3).value).strip() for row in range(7, 53))
    expected = tuple(d for d in EXPECTED_DISPLAY_46 if d not in ROWS_ADDED_IN_290)
    assert actual == expected
