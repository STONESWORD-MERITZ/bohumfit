"""Aggregate KB coverage proposal rows into before/final report dictionaries."""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import date

from .constants import (
    AGG_SUM,
    CASCADE_CASE_LABEL_V2,
    DEATH_EXCLUSION_LABELS,
    KB_COVERAGES_V2,
    LEGACY_TO_V2,
    PAYOUT_CASCADE_V2,
    YN_ITEMS_V2,
)
from .schema import before_coverage, final_coverage
from .v2_mapping import (
    DUAL_COLUMNS,
    GROUP13_V2,
    GROUP_APPENDIX_V2,
    KIND_ROW,
    ROW_AGG,
    ROW_INDEX,
    ROWS_BY_ID,
    combine,
    resolve,
)

# BOHUMFIT-290(S2): ★V2 49행이 처음으로 실계산에 물린다. 구 40행 스키마 상수(행 목록·그룹 순서·
#   항목 순서·246 단계 수식·Y/N 항목표)는 이 모듈에서 더 이상 참조하지 않는다(배선 증명 테스트가
#   고정). 구 상수 자체는 S3 완료 시점까지 삭제하지 않는다(export 최소 어댑터가 쓴다).


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


def carry_coverage_row(
    row: dict, kept_ids: set, known_ids: set, extra_values: dict | None = None,
    extra_columns: dict | None = None,
) -> dict:
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
    # BOHUMFIT-290: 2열 병기(`columns`)·원천 상세(`sources`)도 같은 keep/cancel 필터를 탄다.
    #   신규 제안값은 `extra_columns`(열별)로 받는다 — 열을 모르면 unspecified.
    if row.get("columns"):
        columns = {}
        for column, cell in row["columns"].items():
            cells = {
                str(key): value
                for key, value in (cell.get("by_company") or {}).items()
                if str(key) in kept_ids or str(key) not in known_ids
            }
            cells.update({k: v for k, v in ((extra_columns or {}).get(column) or {}).items() if v is not None})
            columns[column] = {"by_company": cells, "summary": aggregate_coverage_values(cells, row.get("agg"))}
        updated["columns"] = columns
    if row.get("sources"):
        updated["sources"] = {
            name: {str(k): v for k, v in cells.items() if str(k) in kept_ids or str(k) not in known_ids}
            for name, cells in row["sources"].items()
        }
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
    """BOHUMFIT-246 → 290(Q5): Y/N 파생 — 원천 담보 1건 이상 enrolled면 Y.

    ★내부 플래그(item 5종·값·계약별 Y)는 **그대로 유지**하고, 원천만 V2 행으로 재배선했다.
      원천 담보(구 이름)는 V2 행의 `sources`에 남아 있어 상해실손/질병실손처럼 **같은 행에
      합쳐진 원천도 구분**할 수 있다. 해지(carry)로 계약이 빠지면 행 by_company에서도 빠지므로
      `sources` 값 ∩ 행 by_company 생존 키로 판정한다.
    """
    by_id = {row.get("row_id"): row for row in coverages if row.get("row_id")}
    by_name = {row.get("kb_name"): row for row in coverages}
    flags = []
    for item, sources in YN_ITEMS_V2:
        per_company: dict[str, str] = {}
        source_summaries = []
        enrolled = False
        for source_name in sources:
            row_id = LEGACY_TO_V2.get(source_name)
            row = by_id.get(row_id) or by_name.get(source_name)
            if not row:
                source_summaries.append({"kb_name": source_name, "summary": None})
                continue
            row_cells = {k: v for k, v in (row.get("by_company") or {}).items() if v is not None}
            sources_map = row.get("sources")
            if sources_map is None:
                # 원천 상세가 없는 행(구 payload·제안서 전용 행)은 행 값으로 판정한다.
                src_cells = row_cells
                sources_map = {}
            else:
                # V2 행: 이 원천이 없으면 빈 것 — 같은 행의 **다른** 원천(예: 상해실손) 값을 빌리지 않는다.
                src_cells = sources_map.get(source_name) or {}
            live = {k: v for k, v in src_cells.items() if v is not None and k in row_cells}
            # 신규 제안(carry로 병합된 P키 등) — 어느 원천에도 없는 계약 키는 이 행의 값이므로 포함한다.
            sourced_keys = {k for cells in sources_map.values() for k, v in cells.items() if v is not None}
            live.update({k: v for k, v in row_cells.items() if k not in sourced_keys})
            if live:
                enrolled = True
                for company_id in live:
                    per_company[company_id] = "Y"
                source_summary = aggregate_coverage_values(live, row.get("agg"))
            elif row.get("enrolled") and not row_cells:
                # 239 합계-only(overview·귀속 없음) 행: 계약 열은 없지만 가입은 맞다 — 246 규칙 유지.
                enrolled = True
                source_summary = row.get("summary")
            else:
                source_summary = None
            source_summaries.append({"kb_name": source_name, "summary": source_summary})
        flags.append({
            "item": item,
            "value": "Y" if enrolled else "N",
            "by_company": per_company,
            "sources": source_summaries,
        })
    return flags


# BOHUMFIT-290: 종합 판정 블록 라벨 — 뇌·심장은 패킷 정의 그대로 구 라벨을 재사용한다
#   (뇌초기=뇌혈관 / 뇌중기=뇌혈관+뇌졸중 / 뇌말기=+뇌출혈 · 심장초기=허혈성 / 심장중기=허혈성+급성).
#   ★구 `심장말기`·`암`은 케스케이드에 대응 체인이 없어 **사라진다**(S3 블록 재설계 항목).
STAGE_LABEL_V2: dict[str, str] = {
    "cerebral_disease": "뇌초기",
    "stroke": "뇌중기",
    "cerebral_hemorrhage": "뇌말기",
    "ischemic_heart": "심장초기",
    "acute_mi": "심장중기",
}


def stage_label(key: str) -> str:
    if key in STAGE_LABEL_V2:
        return STAGE_LABEL_V2[key]
    if key in CASCADE_CASE_LABEL_V2:
        return CASCADE_CASE_LABEL_V2[key]
    return ROWS_BY_ID[key].display if key in ROWS_BY_ID else key


def compute_stage_totals(coverages: list[dict]) -> dict:
    """BOHUMFIT-290(S2): 종합 판정 = **케스케이드 체인별 지급 합계**(Human 확정 · 289 정의).

    ★행 정의가 `PAYOUT_CASCADE_V2`와 1:1이다 — 체인 하나가 블록 한 행. 진단이 나면 체인의
      행이 **함께 지급**되므로 값은 체인 행 summary의 합이다(빈 값 0).
    ★246 공통 가산(일반종수술5종+질병수술)은 케스케이드 정의에 없어 **폐기**됐다.
    """
    by_id = {row.get("row_id"): row for row in coverages if row.get("row_id")}

    def _value(row_id: str) -> int:
        return (by_id.get(row_id) or {}).get("summary") or 0

    return {
        stage_label(key): sum(_value(row_id) for row_id in chain)
        for key, chain in PAYOUT_CASCADE_V2.items()
    }


def _coverage_sort_key(index_and_row: tuple[int, dict]) -> tuple[int, int, int]:
    """BOHUMFIT-290: 표시 순서 = (V2 스키마 순서, 비고는 유입 순서)."""
    insertion, row = index_and_row
    row_id = row.get("row_id")
    if row_id in ROW_INDEX:
        return (0, ROW_INDEX[row_id], insertion)
    return (1, 0, insertion)


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


def _empty_bucket() -> dict:
    return {
        "by_company": {},
        "columns": {column: {} for column in DUAL_COLUMNS},
        "sources": {},
        "overview": False,
        "estimated": False,
    }


def _feed(bucket: dict, name: str, by_company: dict, agg: str, column: str | None) -> None:
    for key, value in (by_company or {}).items():
        key = str(key)
        bucket["by_company"][key] = combine(bucket["by_company"].get(key), value, agg)
        if column:
            cells = bucket["columns"][column]
            cells[key] = combine(cells.get(key), value, agg)
    bucket["sources"][name] = {str(k): v for k, v in (by_company or {}).items()}


def _appendix_row(name: str, by_company: dict, agg: str, **flags) -> dict:
    row = before_coverage(
        name, GROUP_APPENDIX_V2, GROUP_APPENDIX_V2, agg,
        _aggregate(by_company, agg), dict(by_company),
        any(value is not None for value in by_company.values()),
    )
    row.update({k: v for k, v in flags.items() if v})
    return row


def build_v2_rows(matrix: dict, extras: dict) -> list[dict]:
    """BOHUMFIT-290(S2): 파서 결과(구 이름 매트릭스 + extras) → **V2 49행 + 비고행**.

    ★규칙
      · 이름 → 목적지는 `v2_mapping.resolve()` 한 곳에서 정한다(표시명 → 별칭 → 처분).
      · 같은 계약 키에 원천이 겹치면 행 agg로 합친다(sum=더함 · rep=큰 값). 실손 입원 2행이
        한 행으로 합쳐질 때 같은 계약의 5,030만이 두 번 더해지지 않는 이유다(rep).
      · 2열 병기 행은 `columns`(disease/injury/unspecified)를 따로 갖고, 행 by_company·summary는
        전 열 합산이다(S3가 열을 표시한다).
      · ★자리가 없는 이름은 **비고행**으로 남긴다 — 버리지 않는다(276a·패킷 원칙).
      · 80% 행(`sum_excluded`)은 값을 보존하고 플래그만 단다 — 합계 제외는 소비처(S3)와
        `group_rollup_v2`가 지킨다.
    """
    buckets: dict[str, dict] = {}
    appendix: list[dict] = []

    def _route(name: str, by_company: dict, agg: str, overview_summary=None, **flags):
        target = resolve(name)
        if target.kind == KIND_ROW:
            bucket = buckets.setdefault(target.row_id, _empty_bucket())
            _feed(bucket, name, by_company, ROW_AGG[target.row_id], target.column)
            for flag in ("overview", "estimated"):
                if flags.get(flag):
                    bucket[flag] = True
            if overview_summary is not None:
                bucket["overview_summary"] = combine(bucket.get("overview_summary"), overview_summary, ROW_AGG[target.row_id])
            return
        # 분배 대상(암 주요치료비)은 S4 배선 전까지, 그 밖의 미매칭은 영구적으로 비고행.
        if any(value is not None for value in (by_company or {}).values()) or overview_summary is not None:
            row = _appendix_row(name, by_company, agg, **flags)
            if overview_summary is not None and row.get("summary") is None:
                row["summary"] = overview_summary
                row["enrolled"] = True
            appendix.append(row)

    for name, row in (matrix or {}).items():
        by_company = row.get("by_company") or {}
        overview = bool(row.get("overview"))
        overview_summary = None
        if overview and not any(v is not None for v in by_company.values()):
            # 239 합계-only 문서(계약 귀속 없음): 합계만 행 수준으로 싣는다 — 259 이월 규칙
            #   (귀속 없는 overview 행은 합계 수준 이월)이 그대로 성립하도록 by_company는 비워 둔다.
            overview_summary = row.get("summary")
        _route(name, by_company, row.get("agg") or AGG_SUM, overview=overview, overview_summary=overview_summary)

    for label, extra in (extras or {}).items():
        by_company = extra.get("by_company") or {}
        display_label = label
        n_values = extra.get("n_values") or []
        if label == "N대수술비" and n_values:
            display_label = f"N대수술비({'·'.join(str(n) for n in sorted(set(n_values)))}대)"
        _route(display_label, by_company, extra.get("agg", AGG_SUM), estimated=bool(extra.get("estimated")))

    rows: list[dict] = []
    for spec in KB_COVERAGES_V2:
        bucket = buckets.get(spec.row_id) or _empty_bucket()
        agg = ROW_AGG[spec.row_id]
        by_company = bucket["by_company"]
        summary = _aggregate(by_company, agg)
        enrolled = any(value is not None for value in by_company.values())
        if bucket.get("overview_summary") is not None and summary is None:
            # 239: 귀속 없는 합계-only 값 — 행 수준 summary로만 싣는다(by_company는 비어 있음).
            summary, enrolled = bucket["overview_summary"], True
        row = before_coverage(spec.display, spec.group, spec.group, agg, summary, by_company, enrolled)
        row["row_id"] = spec.row_id
        row["sources"] = bucket["sources"]
        if spec.dual_column:
            row["columns"] = {
                column: {"by_company": cells, "summary": _aggregate(cells, agg)}
                for column, cells in bucket["columns"].items()
            }
        if spec.sum_excluded:
            row["sum_excluded"] = True
        if bucket["overview"]:
            row["overview"] = True
        if bucket["estimated"]:
            row["estimated"] = True
        rows.append(row)

    rows.extend(appendix)
    return [row for _idx, row in sorted(enumerate(rows), key=_coverage_sort_key)]


def group_rollup_v2(coverages: list[dict]) -> dict[str, int]:
    """BOHUMFIT-290: 대분류 합계 = 소속 행 summary 합 — ★`sum_excluded`(80%) 행은 뺀다(Q2·243)."""
    totals: dict[str, int] = {group: 0 for group in GROUP13_V2}
    for row in coverages:
        if row.get("sum_excluded"):
            continue
        group = row.get("group12")
        if group in totals:
            totals[group] += row.get("summary") or 0
    return totals


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
    coverages = build_v2_rows(matrix, extras)

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


def _diagnosis_for(diagnosis: dict, coverage: dict) -> dict:
    """BOHUMFIT-290: KB 진단은 구 담보명으로 온다 — V2 행은 표시명·별칭·원천명 순으로 찾는다."""
    if not diagnosis:
        return {}
    candidates = [coverage.get("kb_name")]
    spec = ROWS_BY_ID.get(coverage.get("row_id") or "")
    if spec:
        candidates.extend(spec.aliases)
    candidates.extend((coverage.get("sources") or {}).keys())
    for name in candidates:
        if name in diagnosis:
            return diagnosis[name]
    return {}


def build_final(before: dict, diagnosis: dict) -> dict:
    coverages = []
    rollup_counts = defaultdict(lambda: {"충분": 0, "부족": 0, "미가입": 0})
    for coverage in before["coverages"]:
        diagnosis_row = _diagnosis_for(diagnosis, coverage)
        status = diagnosis_row.get("status")
        final_row = final_coverage(
            coverage["group12"],
            coverage["kb_name"],
            coverage["agg"],
            coverage["summary"],
            diagnosis_row.get("recommended"),
            diagnosis_row.get("gap"),
            status,
        )
        # BOHUMFIT-290: 최종 행도 row_id·플래그를 유지한다(표시·투영·S3가 쓴다).
        for key in ("row_id", "sum_excluded", "columns"):
            if coverage.get(key):
                final_row[key] = coverage[key]
        coverages.append(final_row)
        if status in rollup_counts[coverage["group12"]]:
            rollup_counts[coverage["group12"]][status] += 1
    rollup = [{"group12": group, "status_counts": dict(rollup_counts[group])} for group in GROUP13_V2]
    return {
        "premium": before["premium"],
        "coverages": coverages,
        "rollup_by_group12": rollup,
        # BOHUMFIT-290: 대분류 금액 합계(80% 제외) — S3 표시·Q6 대조표용.
        "group_totals": group_rollup_v2(before["coverages"]),
    }
