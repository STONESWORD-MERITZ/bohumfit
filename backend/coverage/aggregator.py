"""Aggregate KB coverage proposal rows into before/final report dictionaries."""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import date

from .constants import (
    AGG_SUM,
    DEATH_EXCLUSION_LABELS,
    EXTRA_LABEL_GROUP,
    GROUP13,
    GROUP_ETC,
    GROUP_EXCLUDED,
    KB_COVERAGES,
    NEW_ITEM_ORDER,
    STAGE_COMMON_ADD,
    STAGE_COMPONENTS,
    YN_ITEMS,
)
from .schema import before_coverage, final_coverage

# BOHUMFIT-246: 항목 표시 순서 인덱스(비분양식 시트2 순서) — 목록 밖 라벨은 그룹 내 뒤.
_ITEM_ORDER_IDX = {name: idx for idx, name in enumerate(NEW_ITEM_ORDER)}


def _apply_exclusions(matrix: dict, extras: dict) -> tuple[dict, dict, dict]:
    """BOHUMFIT-246 상호배타 — 상세 검출 담보가 매트릭스 표준 행에 이미 반영된 금액을 차감.

    ① 일반/재해사망: parser가 기록한 지급사유(class_amounts) 행 금액을 상해/질병사망
       매트릭스 셀에서 계약별로 차감하고, 차감 근거가 있는 계약만 사망 그룹으로 승격한다.
       근거 없는 계약(idx 미해석·지급사유 미기록)은 "(계약 미확인)" 라벨로 기타 보존 —
       이중 계상 0이 승격보다 우선(246 결정).
    ② 중입자방사선: parser가 기록한 target_included(고액항암치료비 지급사유 라인)를
       표적항암치료 매트릭스 셀에서 차감(D 실측 정합). 근거 없으면 무차감.
    차감 실적(dedup)은 총액 대사에 쓴다: 구총합 = 신총합 + subtracted_total.
    """
    matrix = {name: {**row, "by_company": dict(row.get("by_company", {}))} for name, row in matrix.items()}
    extras = {label: dict(entry) for label, entry in extras.items()}
    dedup = {"subtracted_total": 0, "details": []}

    def _subtract(row_name: str, key: str, amount: int) -> int:
        row = matrix.get(row_name)
        cell = (row or {}).get("by_company", {}).get(key)
        if not row or not cell:
            return 0
        sub = min(cell, amount)
        row["by_company"][key] = cell - sub
        dedup["subtracted_total"] += sub
        dedup["details"].append({"matrix_row": row_name, "contract": key, "amount": sub})
        return sub

    for label in DEATH_EXCLUSION_LABELS:
        entry = extras.get(label)
        if not entry:
            continue
        class_amounts = entry.get("class_amounts", {})
        promoted: dict = {}
        unresolved: dict = {}
        for key, amount in (entry.get("by_company") or {}).items():
            applied = 0
            for cls_name, cls_amount in (class_amounts.get(key) or {}).items():
                applied += _subtract(cls_name, key, cls_amount)
            if applied > 0:
                promoted[key] = amount
            else:
                unresolved[key] = amount
        if promoted:
            extras[label] = {**entry, "by_company": promoted}
        else:
            extras.pop(label, None)
        if unresolved:
            extras[f"{label}(계약 미확인)"] = {"agg": entry.get("agg", AGG_SUM), "by_company": unresolved}

    ion = extras.get("중입자방사선")
    if ion:
        for key, included in (ion.get("target_included") or {}).items():
            _subtract("표적항암치료", key, included)

    return matrix, extras, dedup


def carry_coverage_row(row: dict, kept_ids: set, known_ids: set, extra_values: dict | None = None) -> dict:
    """BOHUMFIT-249: [후] 이월 행 변환의 ★단일 소스(211 패리티 — 246 회송 보정 규칙 통일).

    - overview 행: **계약 귀속(by_company)이 있으면 일반 행과 동일 규칙**으로 이월한다
      (BOHUMFIT-259 — 256~258이 overview by_company를 채운 뒤부터 해지 반영이 가능해졌다.
      회사합=합계가 보장되므로 해지 0이면 재집계 결과가 [전]과 동일하다). 귀속이 없는
      overview 행(구 데이터·타 변형 문서)만 종전대로 합계 수준 이월 — 해지 반영 불가.
      신규 제안 값(extra_values)은 합계에 가산.
    - 일반 행: 계약 귀속 확인분은 keep/cancel(kept_ids) 필터, 계약 미상 키('?' 등 known_ids
      밖)는 해지 대상이 아니므로 그대로 이월. 신규 제안 값 병합 후 재집계.
    소비처: consulting.apply_consulting_plan · compare.build_after_analysis.
    클라이언트 미러: src/lib/coverageAfterDisplayCache.buildAfterResult — 규칙 변경 시 동기 수정.
    (249 배경: compare 경로만 이 규칙이 빠져 overview [후]가 0으로 소실 — 프로덕션 실물 결함.)
    """
    from copy import deepcopy

    extra_values = {key: value for key, value in (extra_values or {}).items() if value is not None}
    updated = deepcopy(row)
    # BOHUMFIT-259: 귀속된 overview 행은 아래 일반 경로(keep/cancel 필터 + 재집계)를 탄다.
    if row.get("overview") and not any(
        value is not None for value in (row.get("by_company") or {}).values()
    ):
        by_company = dict(extra_values)
        added = aggregate_coverage_values(by_company, row.get("agg")) if by_company else None
        summary = row.get("summary")
        if added is not None:
            summary = ((summary or 0) + added) if row.get("agg") == AGG_SUM else max(summary or 0, added)
        updated["by_company"] = by_company
        updated["summary"] = summary
        updated["enrolled"] = bool(row.get("enrolled")) or added is not None
        return updated
    # null 셀도 유지(클라이언트 캐시·종전 compare와 표기 동일 — 211 패리티는 셀 단위 비교).
    by_company = {
        str(key): value
        for key, value in (row.get("by_company") or {}).items()
        if str(key) in kept_ids or str(key) not in known_ids
    }
    by_company.update(extra_values)
    updated["by_company"] = by_company
    updated["summary"] = aggregate_coverage_values(by_company, row.get("agg"))
    updated["enrolled"] = any(value is not None for value in by_company.values())
    return updated


OVERVIEW_CANCEL_WARNING = (
    "전체 보장현황(합계형) 문서는 계약별 보장 귀속이 없어 해지를 보장 합계에 반영할 수 "
    "없습니다 — 해당 보장행은 [전] 합계 수준으로 유지됩니다."
)


def overview_rows_need_cancel_warning(coverages: list[dict]) -> bool:
    """BOHUMFIT-259: 해지 경고가 필요한지 — ★귀속되지 않은 overview 행이 있을 때만 True.

    256~258로 overview by_company가 채워지면 해지가 회사 열 단위로 정확히 반영되므로
    239/246의 "합계에 반영 불가" 경고는 사실과 달라진다(불필요한 경고 제거).
    """
    return any(
        row.get("overview")
        and not any(value is not None for value in (row.get("by_company") or {}).values())
        for row in coverages or []
    )


def compute_yn_flags(coverages: list[dict]) -> list[dict]:
    """BOHUMFIT-246: 양식 45~49행 Y/N 파생 — 원천 담보 1건 이상 enrolled면 Y.
    (원본 수식 `=IF(COUNTA(범위)=0,"N", IF(COUNTA(범위),"Y"))`의 의미 등가.)"""
    by_name = {row.get("kb_name"): row for row in coverages}
    flags = []
    for item, sources in YN_ITEMS:
        source_rows = [by_name.get(name) for name in sources]
        enrolled = any(row and row.get("enrolled") for row in source_rows)
        # BOHUMFIT-254 개정3: 계약(회사)별 Y 파생 — 해지 시 "어느 회사 담보가 빠지는지"
        #   식별용(누락 방지). ★금액은 건드리지 않는다: 원천 9행의 기존 by_company(253 귀속
        #   정합)에 값이 있는 계약 키만 "Y"로 표시한다(없으면 키 자체를 만들지 않음=공백).
        #   합계 Y/N 규칙(원천 1건 이상 enrolled)은 불변 — 5케이스 정합 상이 0 실측.
        per_company: dict[str, str] = {}
        for row in source_rows:
            for company_id, amount in ((row or {}).get("by_company") or {}).items():
                if amount is not None:
                    per_company[company_id] = "Y"
        flags.append({
            "item": item,
            "value": "Y" if enrolled else "N",
            "by_company": per_company,
            "sources": [
                {"kb_name": name, "summary": (by_name.get(name) or {}).get("summary")}
                for name in sources
            ],
        })
    return flags


def compute_stage_totals(coverages: list[dict]) -> dict:
    """BOHUMFIT-246: 종합비교 단계 파생(비분양식 시트3 수식 이식 — 원문은 constants 주석).
    빈 값은 0으로 합산(원본 SUM 동일). [후]도 같은 수식(I열 규칙 — K7 이중합산 미이식)."""
    by_name = {row.get("kb_name"): row for row in coverages}

    def _value(name: str) -> int:
        return (by_name.get(name) or {}).get("summary") or 0

    common = sum(_value(name) for name in STAGE_COMMON_ADD)
    return {stage: sum(_value(name) for name in names) + common for stage, names in STAGE_COMPONENTS}


def _coverage_sort_key(index_and_row: tuple[int, dict]) -> tuple[int, int, int]:
    insertion, row = index_and_row
    group = row.get("group12")
    group_idx = GROUP13.index(group) if group in GROUP13 else len(GROUP13)
    item_idx = _ITEM_ORDER_IDX.get(row.get("kb_name"), len(NEW_ITEM_ORDER))
    return (group_idx, item_idx, insertion)


def aggregate_coverage_values(by_company: dict, agg: str):
    vals = [v for v in by_company.values() if v is not None]
    if not vals:
        return None
    return sum(vals) if agg == AGG_SUM else max(vals)


def _aggregate(by_company: dict, agg: str):
    return aggregate_coverage_values(by_company, agg)


def _paid(contract: dict):
    premium = contract.get("monthly_premium")
    months = contract.get("pay_months")
    # BOHUMFIT-234: 일시납은 표기 금액이 1회 납입 총액 — 개월 수를 곱하지 않는다.
    if contract.get("pay_cycle") == "일시납":
        return premium
    return premium * months if premium is not None and months is not None else None


def _remark(note: dict | None):
    if not note:
        return None
    if note.get("kp_differs"):
        return f"계피상이(계약자 {note.get('contractor')}·피보험자 {note.get('insured')})"
    return "계피동일"


def _company_sort_key(contract: dict):
    # BOHUMFIT-236 B: 계약 번호 숫자 오름차순으로 통일 — KB 원본 번호 순서를 보존해
    # 산출물 대조를 쉽게 하고, 과거 보험사 가나다 + str(idx) 사전식("1,10,11,…,2") 정렬을 대체.
    idx = contract.get("idx")
    try:
        return (0, int(idx))
    except (TypeError, ValueError):
        return (1, 0)


_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def _pay_end_date(contract: dict) -> str | None:
    """납입 종료(예정)일 ISO 문자열 — contract_date + pay_months. 판별 불가 시 None."""
    match = _DATE_RE.match(str(contract.get("contract_date") or ""))
    months = contract.get("pay_months")
    if not match or not months:
        return None
    year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
    total = (month - 1) + int(months)
    return f"{year + total // 12:04d}-{total % 12 + 1:02d}-{day:02d}"


def _is_paid_up(contract: dict, today_iso: str) -> bool:
    """BOHUMFIT-236 A: 납입완료 판별 — 일시납은 즉시 완료, 월납·연납은 납입기간 경과 시 완료.
    (234 실측: KB 원본 헤더의 월납 합계 = 납입 중 계약만 합산 — 부값 산식의 근거)"""
    if contract.get("pay_cycle") == "일시납":
        return True
    end = _pay_end_date(contract)
    return end is not None and end <= today_iso


def build_before(raw: dict, today: str | None = None) -> dict:
    contracts = raw.get("contracts", [])
    today_iso = today or date.today().isoformat()
    # BOHUMFIT-234 ⑥: 일시납 계약의 표기 금액은 월 보험료가 아니다 — 월납 합산에서 제외
    # (KB 원본 헤더 월납 합계와 정합 — 234 실사용 케이스 실측: 일시납 혼입 시 합계 왜곡).
    monthly_total = sum(
        c["monthly_premium"]
        for c in contracts
        if c.get("monthly_premium") and c.get("pay_cycle") != "일시납"
    )
    # BOHUMFIT-236 A: 병기 부값 — 납입완료 계약까지 제외한 합(KB 원본 헤더 산식과 일치).
    monthly_total_active = sum(
        c["monthly_premium"]
        for c in contracts
        if c.get("monthly_premium")
        and c.get("pay_cycle") != "일시납"
        and not _is_paid_up(c, today_iso)
    )
    paid_total = sum((_paid(c) or 0) for c in contracts)
    notes = raw.get("notes", {})
    companies = sorted(contracts, key=_company_sort_key)
    companies = [
        {
            **c,
            "paid_total": _paid(c),
            "paid_up": _is_paid_up(c, today_iso),
            "remark": _remark(notes.get(c.get("idx"))) or c.get("remark"),
        }
        for c in companies
    ]

    # BOHUMFIT-246: 상호배타 차감(사망·중입자)을 집계 전에 적용 — 차감 실적은 총액 대사용.
    matrix, extras, dedup = _apply_exclusions(raw.get("matrix", {}), raw.get("extra", {}))
    coverages = []
    for kb_name, kb_group, group12, agg in KB_COVERAGES:
        if group12 == GROUP_EXCLUDED:
            continue
        row = matrix.get(kb_name)
        by_company = row["by_company"] if row else {}
        overview_row = bool(row and row.get("overview"))
        if overview_row:
            # BOHUMFIT-239: 전체 보장현황 fallback — 담보별 합계만 제공(계약별 열 없음).
            # 표준 문서(상품별 가입현황 매트릭스)는 이 플래그가 없어 else 경로로 무변경.
            summary = row.get("summary")
            enrolled = summary is not None
        else:
            summary = _aggregate(by_company, agg)
            enrolled = any(v is not None for v in by_company.values())
        built = before_coverage(kb_name, kb_group, group12, agg, summary, by_company, enrolled)
        if overview_row:
            # BOHUMFIT-246 회송 보정: 합계-only 출처 표식 — [후] 이월(consulting)이 빈 계약
            # 셀로 재집계해 값을 소실하지 않도록 행 단위로 전달한다(239 가드와 동일 원칙).
            built["overview"] = True
        coverages.append(built)

    for label, extra in extras.items():
        by_company = extra.get("by_company", {})
        agg = extra.get("agg", AGG_SUM)
        group12 = EXTRA_LABEL_GROUP.get(label, GROUP_ETC)
        summary = _aggregate(by_company, agg)
        display_label = label
        # BOHUMFIT-237 C: N대수술비는 원문의 N을 병기 — 복수면 나열(정보 무손실 표기.
        # 최대값 단일 표기는 계약별 상이 정보를 잃어 나열을 대표 규칙으로 채택).
        n_values = extra.get("n_values") or []
        if label == "N대수술비" and n_values:
            display_label = f"N대수술비({'·'.join(str(n) for n in sorted(set(n_values)))}대)"
        row = before_coverage(
            display_label,
            group12,
            group12,
            agg,
            summary,
            by_company,
            any(value is not None for value in by_company.values()),
        )
        # BOHUMFIT-238: 표준 환산 산출 행 구분 필드(표시명 외 데이터 소비자용) — 246 유실 금지.
        if extra.get("estimated"):
            row["estimated"] = True
        coverages.append(row)

    # BOHUMFIT-246: 표시 순서 = (비분양식 그룹 순서, 시트2 항목 순서, 유입 순서).
    coverages = [row for _idx, row in sorted(enumerate(coverages), key=_coverage_sort_key)]

    return {
        "customer": raw.get("customer"),
        "premium": {
            "monthly_total": monthly_total,
            "monthly_total_active": monthly_total_active,
            "paid_total": paid_total,
            "currency": "KRW",
        },
        "companies": companies,
        "contract_list": companies,
        "coverages": coverages,
        # BOHUMFIT-246: 파생치 — Y/N(양식 45~49행)·종합비교 단계(시트3 수식)·배타 차감 실적.
        "yn_flags": compute_yn_flags(coverages),
        "stage_totals": compute_stage_totals(coverages),
        "death_dedup": dedup,
    }


def build_final(before: dict, diagnosis: dict) -> dict:
    coverages = []
    rollup_counts = defaultdict(lambda: {"충분": 0, "부족": 0, "미가입": 0})
    for coverage in before["coverages"]:
        if coverage.get("group12") == GROUP_EXCLUDED:
            continue
        diagnosis_row = diagnosis.get(coverage["kb_name"], {})
        status = diagnosis_row.get("status")
        coverages.append(
            final_coverage(
                coverage["group12"],
                coverage["kb_name"],
                coverage["agg"],
                coverage["summary"],
                diagnosis_row.get("recommended"),
                diagnosis_row.get("gap"),
                status,
            )
        )
        if status in rollup_counts[coverage["group12"]]:
            rollup_counts[coverage["group12"]][status] += 1
    rollup = [{"group12": group, "status_counts": dict(rollup_counts[group])} for group in GROUP13]
    return {"premium": before["premium"], "coverages": coverages, "rollup_by_group12": rollup}
