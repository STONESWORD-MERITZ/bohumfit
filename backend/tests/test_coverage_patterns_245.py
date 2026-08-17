# -*- coding: utf-8 -*-
"""BOHUMFIT-245 회귀 — 신 체계 1단계 신규 담보 패턴(익명 합성 픽스처, 홍길동).

244 S2 채집 표기 기반: 일반/재해사망(배타 가드), 중입자>항암약물 선순위, 표적 배제,
순환계·응급실·깁스, 표적항암 통합(표준행 개명·별칭 매칭).
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from coverage.aggregator import build_before  # noqa: E402
from coverage.constants import (  # noqa: E402
    EXTRA_LABEL_GROUP,
    GROUP_ETC,
    KB_NAME_ALIASES,
    classify_extra,
    match_coverage,
)
from coverage.parser import parse_detail_pages  # noqa: E402

MAN = 10_000


# ── 패턴 단위: 244 S2 원문 표기 기반(케이스 A~E 실측 형태의 익명 재현) ──────────
# BOHUMFIT-290(S2): 집계 행이 V2 49행으로 바뀌었다 — 구 이름 조회는 투영 헬퍼로(값·셀 불변).
from tests.v2names import find_row as _find_v2  # noqa: E402
from coverage.v2_mapping import GROUP_APPENDIX_V2 as _APPENDIX  # noqa: E402


def test_new_pattern_labels():
    cases = {
        # ① 일반사망(A형) — 독립 담보로 명시된 경우만
        "3 정액 일반사망 질병사망 6,000만": "일반사망",
        # ② 재해사망(D형)
        "5 정액 재해사망특약 상해사망 10,000만": "재해사망",
        # ③ 항암약물방사선(A·B·D·E형) — ★BOHUMFIT-292(S4·Phase E): 결합 담보만 합성 라벨, 약물만인 담보는
        #   `항암약물치료비`(V2 항암 약물 치료 행)로 분리된다(Human 확정 · 검출 자체는 그대로 1회 계상).
        "7 정액 항암방사선약물치료비 항암방사선약물치료비 500만": "항암약물방사선",
        "2 정액 항암약물치료특약(간편고지형(4), 갱신형) 최초계약 항암방사선약물치료비 1,000만": "항암약물치료비",
        # ⑤ 중입자방사선(D·E형) — ③보다 선순위(포괄 패턴 선점 방지)
        "4 정액 항암 중입자방사선치료특약(갱신형) 최초계약 고액항암치료비 5,000만": "중입자방사선",
        "6 정액 갱신형 항암중입자방사선치료비(통합간편가입) 기타 인보험(정액)담보 5,000만": "중입자방사선",
        # ⑥ 순환계 치료비(A·E형)
        "8 정액 갱신형 특정순환계질환 통합치료비(통합간편가입) 기타 인보험(정액)담보 5,000만": "순환계 치료비",
        # ⑦ 응급실(B·E형)
        "9 정액 갱신형 응급실내원비(비응급) 응급치료 2만": "응급실",
        "1 정액 응급실내원치료비(응급)(간편,갱신형) 응급치료 5만": "응급실",
        # ⑧ 깁스치료비(B·C·D·E형)
        "2 정액 [갱신형]깁스치료비(부목치료 제외) 깁스치료 50만": "깁스치료비",
        "3 정액 깁스치료특약(간편고지형(4), 갱신형) 최초계약 깁스치료 50만": "깁스치료비",
    }
    for line, want in cases.items():
        got = classify_extra(line)
        assert got is not None and got[0] == want, f"{line!r} -> {got}"


def test_new_pattern_exclusions():
    # ④ 표적항암약물 라인은 미캡처 — KB가 매트릭스 표적항암치료 행에 이미 합산(이중 계상 0).
    assert classify_extra("4 정액 표적항암약물치료비 고액항암치료비 7,000만") is None
    assert classify_extra("5 정액 표적항암약물허가치료특약(갱신형) 최초계약 고액항암치료비 6,000만") is None
    # ⑧ 복합특약의 분류 전용 행(C 실측 형태) 미계상 — 234 ⑨ 원칙.
    assert classify_extra("6 정액 상해 통합치료비 (실속형) 깁스치료 10만") is None
    # ① 일반사망은 접두 한정 — 파생 명칭 오포섭 방지.
    assert classify_extra("7 정액 특정일반사망담보 질병사망 1,000만") is None


def test_group_assignment():
    # BOHUMFIT-246: 신규 7종을 비분양식 그룹으로 승격(245 당시 기타 잠정 귀속을 대체).
    expected = {
        "일반사망": "사망", "재해사망": "사망",
        "항암약물방사선": "암", "중입자방사선": "암",
        "순환계 치료비": "심장", "응급실": "의료이용", "깁스치료비": "골절",
    }
    for label, group in expected.items():
        assert EXTRA_LABEL_GROUP[label] == group, label


# ── 사망 배타 가드: KB의 지급사유 중복 행 1회 계상 + 사망 그룹 총합 보존 ─────────
def _detail_page(lines):
    return ["상품별 가입담보상세", "홍길동", *lines]


def test_death_dedup_and_group_total_preserved():
    detail = _detail_page([
        "1 정액 일반사망 질병사망 6,000만",
        "2 정액 일반사망 상해사망 6,000만",  # 동일 담보의 지급사유 중복 행(A 실측 형태)
    ])
    _notes, extra = parse_detail_pages([detail], contracts=[], jong_table=None)
    row = extra["일반사망"]
    assert sum(row["by_company"].values()) == 6000 * MAN  # 1.2억이 아닌 6,000만(1회 계상)

    raw = {
        "customer": {"name": "홍길동", "age": 50, "sex": "남자"},
        "contracts": [{
            "idx": 1, "insurer": "가나손보", "product": "합성", "contract_date": "2024-01-01",
            "pay_cycle": "월납", "pay_years": 20, "pay_months": 240, "maturity": "100세",
            "monthly_premium": 50_000,
        }],
        "matrix": {
            "상해사망": {"by_company": {"1": 6000 * MAN}},
            "질병사망": {"by_company": {"1": 6000 * MAN}},
        },
        "diagnosis": {}, "notes": {},
        # BOHUMFIT-246: 차감 근거(class_amounts) 없는 검출분은 승격하지 않고
        #   "(계약 미확인)" 라벨로 기타 보존 — 이중 계상 0이 승격보다 우선.
        "extra": {"일반사망": {"agg": "sum", "by_company": {"1": 6000 * MAN}}},
        "warnings": [],
    }
    before = build_before(raw, today="2026-07-25")
    death = [c for c in before["coverages"] if c["group12"] == "사 망" and c["enrolled"]]  # 290: V2 표기
    etc = [c for c in before["coverages"] if c["group12"] == _APPENDIX and c["enrolled"]]  # 290: 기타→비고
    # 근거 없음 → 매트릭스 무차감(사망 그룹 보존) + 일반사망은 기타(계약 미확인)로 표시.
    assert sum(c["summary"] for c in death) == 12000 * MAN
    assert [(c["kb_name"], c["summary"]) for c in etc] == [("일반사망(계약 미확인)", 6000 * MAN)]
    assert before["death_dedup"]["subtracted_total"] == 0
    # 차감 근거가 있으면 승격 + 매트릭스 차감(상호배타) — 246 본검증은 test_taxonomy_246.
    raw2 = {**raw, "extra": {"일반사망": {
        "agg": "sum", "by_company": {"1": 6000 * MAN},
        "class_amounts": {"1": {"상해사망": 6000 * MAN, "질병사망": 6000 * MAN}},
    }}}
    before2 = build_before(raw2, today="2026-07-25")
    death2 = [c for c in before2["coverages"] if c["group12"] == "사 망" and c["enrolled"]]
    assert sum(c["summary"] for c in death2) == 6000 * MAN  # 일반사망 6,000만 단일 계상
    assert before2["death_dedup"]["subtracted_total"] == 12000 * MAN


def test_death_distinct_riders_not_deduped():
    """금액·담보명이 다른 실제 별개 담보는 정상 합산된다(가드 과잉 방지)."""
    detail = _detail_page([
        "1 정액 재해사망특약 상해사망 10,000만",
        "2 정액 재해사망보장특약 상해사망 5,000만",
    ])
    _notes, extra = parse_detail_pages([detail], contracts=[], jong_table=None)
    assert sum(extra["재해사망"]["by_company"].values()) == 15000 * MAN


# ── ⑦ 표적항암 통합: 별칭 매칭 + 표준행 개명 ────────────────────────────────────
def test_target_cancer_alias_and_rename():
    assert KB_NAME_ALIASES["고액(표적)항암치료비"] == "표적항암치료"
    meta = match_coverage("고액(표적)항암치료비 8,000만 - 8,000만")
    assert meta is not None and meta[0] == "표적항암치료" and meta[2] == "암"

    raw = {
        "customer": {"name": "홍길동", "age": 50, "sex": "남자"},
        "contracts": [{
            "idx": 1, "insurer": "가나손보", "product": "합성", "contract_date": "2024-01-01",
            "pay_cycle": "월납", "pay_years": 20, "pay_months": 240, "maturity": "100세",
            "monthly_premium": 50_000,
        }],
        # 파서가 별칭 행을 만나면 정식명 키로 적재된다 — 집계 입력도 정식명 기준.
        "matrix": {"표적항암치료": {"by_company": {"1": 7000 * MAN}}},
        "diagnosis": {}, "notes": {}, "extra": {}, "warnings": [],
    }
    before = build_before(raw, today="2026-07-25")
    target = _find_v2(before["coverages"], "표적항암치료")  # 290: V2 `표적 약물 치료`
    assert target["summary"] == 7000 * MAN and target["group12"] == "암"
    # 구명칭 행은 더 이상 존재하지 않는다(단일 라벨 — 값 이관).
    assert not any(c["kb_name"] == "고액(표적)항암치료비" for c in before["coverages"])
