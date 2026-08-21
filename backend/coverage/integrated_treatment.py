# -*- coding: utf-8 -*-
"""BOHUMFIT-292(S4·Phase D) — 통합치료비류 담보의 **자동 판정·분배 배선**.

★Human 확정(292 패킷 · 재검토 금지)
  · 자동 판정: 약관 내역에 치료별 금액이 **상이** → Q8형(내역 분해) / **동액 또는 미기재** → 주요치료비형(3행 동액)
  · Q8형(순환계): 본체 → `순환계 치료비` 행 + 내역 "수술 1회당" → 뇌혈관 수술비·심장질환 수술비
  · 주요치료비형: 가입금액 동액을 [암수술, 항암약물, 방사선]에
  · ★한도 문구(`위 1)~3) 합산하여 연간 총 지급액 X 한도` · `연간 총 지급액 한도`)는 지급 항목이 아니다
  · 분배분 + 개별 특약 공존 → sum(별개 보장) / 같은 담보의 리스트·상세 중복은 rep — 출처 식별자 `origin`으로 구분

★원문 근거(오현지 알파Plus 가입제안서 실측)
  · #169 특정순환계질환 통합치료비 5,000만: 담보사항면에 내역 `- 항목 : 금액` 목록(검사 3·주요치료 8·재활 2) +
    한도 문구 `※ 위1)~3)까지 합산하여 연간 총 지급액은 5,000만원 한도` → 금액 상이 → **Q8형**
  · #117 암 통합치료비(실속형) 3,000만 · #119 암 통합치료비Ⅱ 1억: 담보사항면에는 "약관에서 정한 금액"뿐이지만
    ★**`… 특약 안내사항` 표**(제안서 후반)에 통합치료항목별 지급금액이 있다(암수술 500/1,000 · 유사암수술 100/200 ·
    항암방사선 500/1,000 · 다빈치 500/1,000 · 표적/면역/양성자 500/3,000 …) → 금액 상이 → **Q8형**.
    (288 §3-4가 "본문에 없음"으로 판정 불가로 남긴 것은 담보사항면만 본 결과 — 안내사항 표로 해소)
  · Ⅱ형 표는 `1년 경과 전 / 이후` 2열 — **이후(정상) 금액**을 쓴다(감액은 지급 조건이지 가입금액이 아니다).

★추측 금지
  · Human ⑥ 확정: 유사암 계열 항암방사선/약물 내역은 `유사암 수술` 행에 함께 표시한다. 검사·재활 등은 `unrouted`로 기록만 한다.
  · 암 통합치료비 **본체**는 한도라 지급 항목이 아니고 49행에 자리도 없다 → **비고행**(정보 보존)으로만 싣는다.
  · 내역 파싱 실패(Q8형인데 수술 항목 없음 등)면 본체만 싣고 나머지는 빈칸 + `needs_review`(폴백 금지).
"""
from __future__ import annotations

import re
from typing import Any, Sequence

from .constants import AGG_SUM

MODE_Q8 = "Q8"
MODE_MAJOR = "MAJOR"
ORIGIN_DISTRIBUTED = "distributed"

#: 주요치료비형(3행 동액) 착지 — Human 확정 [암수술, 항암약물, 방사선]
MAJOR_TARGETS: tuple[str, ...] = ("암수술", "항암약물치료비", "항암방사선치료비")

#: 리스트/상세면의 담보 헤더: `169 갱신형 특정순환계질환 통합치료비 [5천만원 12,084]`
_RIDER_HEAD_RE = re.compile(r"^(?P<no>\d{1,3})\s+(?P<name>(?:갱신형\s+)?[^\d].*?통합치료비.*?)(?:\s+(?P<amt>\d[\d,]*\s*(?:천만|백만|십만|억|만)?원)\s+[\d,]+)?\s*$")
_ANY_RIDER_HEAD_RE = re.compile(r"^\d{1,3}\s+(?:갱신형\s+)?\S")
_AMOUNT_LINE_RE = re.compile(r"(?P<amt>\d[\d,]*\s*(?:천만|백만|십만|억|만)?원)\s+[\d,]+\s*$")
#: 순환계형 내역: `- 혈전용해치료 : 1,000만원 (연간 1회한)` · `- 수술 : 수술 1회당 1,000만원`
_ITEM_DASH_RE = re.compile(r"^-\s*(?P<name>[^:]+?)\s*:\s*(?:수술\s*1회당\s*)?(?P<amt>\d[\d,]*\s*(?:천만|백만|억|만)원)")
#: 안내사항 표 행: `▶비급여(전액본인부담 포함) 암(유사암제외) 수술 암(유사암제외) 수술 1회당 500만원 1,000만원`
_ITEM_TABLE_RE = re.compile(r"^(?P<name>.+?)\s+(?:수술\s*1회당|연간\s*1회한)\s+(?P<amts>(?:\d[\d,]*\s*(?:천만|백만|억|만)원\s*)+)$")
_MAN_RE = re.compile(r"(\d[\d,]*)\s*(천만|백만|억|만)원")
_LIMIT_MARKERS = ("합산하여", "총 지급액", "총지급액", "한도")
_TABLE_HEAD_RE = re.compile(r"^(?P<name>.+?)\s*특약\s*안내사항\s*$")
_TABLE_PREFIXES = ("▶", "주요치료", "특정치료", "주요", "치료", "비급여(전액본인부담 포함)", "비급여")


def _man_to_krw(text: str) -> int | None:
    m = _MAN_RE.search(text or "")
    if not m:
        return None
    n = int(m.group(1).replace(",", ""))
    unit = m.group(2)
    return n * {"만": 10_000, "백만": 1_000_000, "천만": 10_000_000, "억": 100_000_000}[unit]


def _amount_from(text: str) -> int | None:
    """`3천만원`·`1억원`·`5천만원`·`1,000만원` → 원."""
    m = re.search(r"(\d[\d,]*)\s*(천만|백만|십만|억|만)?원", text or "")
    if not m:
        return None
    n = int(m.group(1).replace(",", ""))
    unit = m.group(2) or ""
    return n * {"": 1, "만": 10_000, "십만": 100_000, "백만": 1_000_000, "천만": 10_000_000, "억": 100_000_000}[unit]


def _compact(text: str) -> str:
    return "".join((text or "").split())


def _clean_item_name(name: str) -> str:
    text = name.strip()
    changed = True
    while changed:
        changed = False
        for prefix in _TABLE_PREFIXES:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
                changed = True
    # 대상질병 열 반복 제거: `암(유사암제외) 수술 암(유사암제외)` → `암(유사암제외) 수술`
    parts = text.split()
    # 대상질병 열이 여러 단어로 반복되는 경우(`기타피부암 및 갑상선암 항암방사선치료 기타피부암 및 갑상선암`)까지 제거.
    for width in range(len(parts) // 2, 0, -1):
        if parts[:width] == parts[-width:] and len(parts) > width:
            parts = parts[:-width]
            break
    text = " ".join(parts)
    text = re.sub(r"\s*비급여\(전액본인부담 포함\)\s*", " ", text).strip()
    return text


def route_item(item_name: str) -> str | None:
    """내역 항목명 → 착지 kb_name(V2 별칭/구명) — 자리 없으면 None(unrouted · 추측 금지)."""
    c = _compact(item_name)
    if "다빈치" in c:
        if "특정암제외" in c or "일반암" in c:
            return "다빈치(일반암)"
        if "특정암" in c:
            return "다빈치(특정암)"
        return "다빈치(종별 미상)"
    if "유사암" in c and "수술" in c and "유사암제외" not in c:
        return "유사암수술"
    if "수술" in c and ("암(유사암제외)" in c or c.startswith("암수술") or c == "수술"):
        # `수술`(순환계 Q8 — 수술 1회당)은 호출부가 뇌·심장 두 행으로 나눈다.
        return "암수술" if "암" in c else "수술"
    if "표적항암" in c:
        return "표적항암치료"
    if "면역항암" in c:
        return "면역항암치료"
    if "중입자" in c:
        return "중입자방사선"
    if "세기조절" in c:
        return "세기조절방사선"
    if "양성자" in c:
        return "양성자방사선"
    similar = "기타피부암" in c or "갑상선암" in c or ("유사암" in c and "유사암제외" not in c)
    if "항암방사선치료" in c:
        return "유사암수술" if similar else "항암방사선치료비"
    if "항암약물치료" in c:
        return "유사암수술" if similar else "항암약물치료비"
    return None


def _decide_mode(items: list[dict[str, Any]]) -> tuple[str, str]:
    amounts = {item["amount"] for item in items if item.get("amount")}
    if not amounts:
        return MODE_MAJOR, "내역 미기재 → 주요치료비형(3행 동액)"
    if len(amounts) == 1:
        return MODE_MAJOR, f"내역 치료별 금액 동액({next(iter(amounts)) // 10_000:,}만) → 주요치료비형(3행 동액)"
    return MODE_Q8, f"내역 치료별 금액 상이({len(amounts)}종) → Q8형(내역 분해)"


def extract_integrated_treatments(lines: Sequence[str]) -> list[dict[str, Any]]:
    """제안서 전 라인에서 통합치료비류 담보를 찾아 본체·내역·자동 판정을 돌려준다(값 계산 없음)."""
    riders: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    n = len(lines)

    # 1) 담보 헤더 + 본체 금액 + 대시형 내역(같은 블록 안)
    for i, raw in enumerate(lines):
        line = raw.strip()
        head = _RIDER_HEAD_RE.match(line)
        if not head:
            continue
        name = re.sub(r"\s+", " ", head.group("name")).strip()
        # 상세면 헤더는 괄호가 닫히기 전에 줄이 바뀔 수 있다(`… 암중점치료기` / `관(상급종합병원 포함))`) — 균형이 맞을 때까지
        # 다음 줄(최대 2줄)의 앞부분을 붙인다(리스트면처럼 금액이 이미 있으면 붙이지 않는다).
        if not head.group("amt"):
            k = i + 1
            while name.count("(") > name.count(")") and k < n and k <= i + 2:
                frag = lines[k].strip()
                cut = frag.find("))")
                frag = frag[: cut + 2] if cut >= 0 else frag.split(" ")[0]
                name = (name + frag).strip()
                k += 1
        name = re.sub(r"^갱신형\s+", "", name)
        # 리스트면 이름이 다음 줄로 이어질 수 있다(`… 암중점치료기` / `관(상급종합병원 포함))`) — 이름 뒤 조각은 붙이지 않고
        # 상세면 헤더(같은 번호)에서 정규화된 이름을 우선한다.
        no = head.group("no")
        rider = riders.get(no)
        if rider is None:
            rider = {"no": no, "name": name, "body_amount": None, "items": [], "unrouted": [], "limit_lines": []}
            riders[no] = rider
            order.append(no)
        elif len(name) > len(rider["name"]):
            rider["name"] = name
        if head.group("amt"):
            rider["body_amount"] = rider["body_amount"] or _amount_from(head.group("amt"))
        # 블록 스캔: 다음 담보 헤더 전까지
        j = i + 1
        while j < n and j < i + 40:
            cur = lines[j].strip()
            if _ANY_RIDER_HEAD_RE.match(cur) and not cur.startswith("-"):
                # 안내사항 표 행(`119 …`)이 아니라 담보 헤더면 종료
                if _RIDER_HEAD_RE.match(cur) or re.match(r"^\d{1,3}\s+갱신형\s+", cur):
                    break
            if rider["body_amount"] is None:
                am = _AMOUNT_LINE_RE.search(cur)
                if am and not cur.startswith("-"):
                    rider["body_amount"] = _amount_from(am.group("amt"))
            if any(marker in cur for marker in _LIMIT_MARKERS) and re.search(r"한도", cur):
                rider["limit_lines"].append(cur)
            else:
                dash = _ITEM_DASH_RE.match(cur)
                if dash:
                    amt = _man_to_krw(dash.group("amt"))
                    if amt:
                        rider["items"].append({"name": dash.group("name").strip(), "amount": amt, "src": "dash"})
            j += 1

    # 2) `… 특약 안내사항` 표(암 통합치료비류) — 이름으로 담보에 귀속
    for i, raw in enumerate(lines):
        th = _TABLE_HEAD_RE.match(raw.strip())
        if not th:
            continue
        table_name = _compact(th.group("name"))
        target = None
        for no in order:
            rn = _compact(riders[no]["name"]).replace("갱신형", "")
            key = rn.split("(")[0]
            if key and key in table_name and (
                ("Ⅱ" in rn) == ("Ⅱ" in table_name)
            ):
                target = riders[no]
                break
        if target is None:
            continue
        j = i + 1
        while j < n and j < i + 40:
            cur = lines[j].strip()
            if any(marker in cur for marker in ("연간 총 지급액 한도", "총 지급액 한도")):
                target["limit_lines"].append(cur)
                break
            m = _ITEM_TABLE_RE.match(cur)
            if m:
                amts = [_man_to_krw(a + "원") for a in re.findall(r"\d[\d,]*\s*(?:천만|백만|억|만)", m.group("amts"))]
                amts = [a for a in amts if a]
                if amts:
                    target["items"].append({"name": _clean_item_name(m.group("name")), "amount": amts[-1], "src": "table",
                                            "amounts": amts})
            j += 1

    results: list[dict[str, Any]] = []
    for no in order:
        rider = riders[no]
        mode, basis = _decide_mode(rider["items"])
        rider["mode"], rider["basis"] = mode, basis
        results.append(rider)
    return results


def _is_circulatory(name: str) -> bool:
    return "순환계" in _compact(name)


def _is_thrombolysis(name: str) -> bool:
    """BOHUMFIT-302b: 순환계 내역의 혈전용해 항목(`혈전용해치료` 등)."""
    return "혈전용해" in _compact(name)


def distribution_entries(treatments: list[dict[str, Any]], make_entry) -> list[dict[str, Any]]:
    """판정 결과 → 분배 entry 목록. `make_entry(kb_name, amount, group12, agg, source, raw)`는 proposal_parser._entry."""
    entries: list[dict[str, Any]] = []
    for rider in treatments:
        tag = f"분배:{rider['mode']}(#{rider['no']} {rider['name']})"
        body = rider.get("body_amount")
        if rider["mode"] == MODE_MAJOR:
            if not body:
                rider["needs_review"] = "본체 금액 미확인 — 분배 불가"
                continue
            for target in MAJOR_TARGETS:
                entries.append(_mark(make_entry(target, body, "암", AGG_SUM, tag, rider["name"]), rider["no"]))
            continue
        # Q8형
        if _is_circulatory(rider["name"]):
            if body:
                # BOHUMFIT-302b: 본체(연간 총 지급 한도)는 뇌 대분류 최상단 회색 헤더 행에 싣는다(`sum_excluded`).
                entries.append(_mark(make_entry("순환계 치료비", body, "뇌", AGG_SUM, tag + ":본체", rider["name"]), rider["no"]))
            surgery = [it for it in rider["items"] if _compact(it["name"]) == "수술"]
            if surgery:
                amt = surgery[0]["amount"]
                for target in ("뇌혈관수술", "심혈관수술"):
                    entries.append(_mark(make_entry(target, amt, "수술", AGG_SUM, tag + ":수술", surgery[0]["name"]), rider["no"]))
            else:
                rider["needs_review"] = "내역에 수술 항목 없음 — 뇌·심장 수술비 빈칸(폴백 금지)"
            # BOHUMFIT-302b(Human 확정): 혈전용해치료 → 신규 2행(뇌·심장)에 **각각 같은 금액**으로 싣는다.
            #   ★`route_item` 표기 매칭은 무변경 — 순환계 분배 분기에서만 처리한다(302 판정 준수).
            thrombo = [it for it in rider["items"] if _is_thrombolysis(it["name"])]
            if thrombo:
                amt = thrombo[0]["amount"]
                for target in ("뇌혈전용해", "심장혈전용해"):
                    entries.append(_mark(make_entry(target, amt, "수술", AGG_SUM, tag + ":혈전용해", thrombo[0]["name"]),
                                         rider["no"]))
            for it in rider["items"]:
                # 수술·혈전용해는 위에서 착지했다. 나머지(CRRT·인공호흡기·저체온·부분체외순환·중환자실·
                # 검사 MRI/PET/CT·재활)는 **제외**(Human 확정) — 표·비고 어디에도 넣지 않고 기록만 한다.
                if _compact(it["name"]) != "수술" and not _is_thrombolysis(it["name"]):
                    rider["unrouted"].append(it)
            continue
        # 암 통합치료비류 Q8형: 내역 항목 → 각자 행.
        # BOHUMFIT-302b(Human 확정): 본체(연간 총 지급 한도)는 **비고 → 암 대분류 최상단 회색 헤더 행**으로
        #   이관한다(`sum_excluded`이라 합계에는 안 더해진다). 담보가 여러 건이면 한 행에 합산되고
        #   출처는 `source`(담보 번호·이름)로 분리 보존된다.
        if body:
            entries.append(_mark(make_entry("암 통합치료비 한도", body, "암", AGG_SUM, tag + ":본체(한도)", rider["name"]),
                                 rider["no"]))
        routed_any = False
        for it in rider["items"]:
            target = route_item(it["name"])
            if target in (None, "수술"):
                rider["unrouted"].append(it)
                continue
            routed_any = True
            entries.append(_mark(make_entry(target, it["amount"], "암", AGG_SUM, tag + f":{it['name']}", it["name"]), rider["no"]))
        if not routed_any:
            rider["needs_review"] = "내역 항목을 행에 연결하지 못함 — 본체(비고)만"
    return entries


def _mark(entry: dict[str, Any], rider_no: str) -> dict[str, Any]:
    entry["merge_rule"] = AGG_SUM
    entry["origin"] = ORIGIN_DISTRIBUTED
    entry["origin_rider"] = rider_no
    return entry


def summarize(treatments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """metadata용 요약(원문 근거 보존)."""
    out = []
    for r in treatments:
        out.append({
            "no": r["no"], "name": r["name"], "mode": r["mode"], "basis": r["basis"],
            "body_amount": r.get("body_amount"),
            # BOHUMFIT-302b: 순환계는 `route_item`이 아니라 분배 분기가 착지를 정한다 —
            #   수술 → 뇌·심장 수술비, 혈전용해 → 뇌·심장 혈전용해(신규 2행). 그 외는 제외(None).
            "items": [{"name": it["name"], "amount": it["amount"],
                       "route": route_item(it["name"]) if not _is_circulatory(r["name"]) else (
                           "뇌혈관수술·심혈관수술" if _compact(it["name"]) == "수술"
                           else ("뇌혈전용해·심장혈전용해" if _is_thrombolysis(it["name"]) else None))}
                      for it in r["items"]],
            "limit_lines": r.get("limit_lines", []),
            "needs_review": r.get("needs_review"),
        })
    return out
