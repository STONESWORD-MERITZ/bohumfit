"""BOHUMFIT-114: 보장 비교분석 PDF 파서.

- 보장분석서(current): 한화손보·KB손보 형식 지정 + 공통 보장분석 레이아웃 범용 처리.
- 가입제안서(proposal): 모든 손보/생보 범용 텍스트 파싱.
- ★ 실패 시 예외를 던지지 않는다(parse_warnings 누적). 실 PDF·PII는 저장/커밋하지 않는다.
- pdfplumber 텍스트 기반. 회사별 정밀 보정은 추후 레이어로 확장.
"""
from __future__ import annotations

import io
import re

import pdfplumber

# 알려진 보험사명(텍스트 감지용). 약식 표기는 _detect_insurer에서 보정.
_KNOWN_INSURERS = (
    "메리츠화재", "삼성화재", "DB손해보험", "KB손해보험", "현대해상", "한화손해보험",
    "롯데손해보험", "흥국화재", "NH농협손해보험", "하나손해보험", "AXA손해보험",
    "MG손해보험", "캐롯손해보험", "신한EZ손해보험", "삼성생명", "한화생명", "교보생명",
    "신한라이프", "NH농협생명", "동양생명", "미래에셋생명", "라이나생명", "흥국생명",
    "KB라이프", "메트라이프생명", "AIA생명", "DB생명", "처브라이프생명", "푸본현대생명",
    "ABL생명", "iM라이프", "하나생명", "IBK연금보험",
)

_DATE_YM = re.compile(r"(20\d{2})[./\-](\d{1,2})")
_TERM = re.compile(r"(\d{1,3}\s*세\s*만기|\d{1,3}\s*년\s*만기|종신)")
_PAYTERM = re.compile(r"(\d{1,3}\s*년\s*납|일시납|전기납|종신납)")
_PAYMETHOD = re.compile(r"(월납|연납|일시납|3개월납|6개월납)")


def _digits(s: str | None) -> int:
    """숫자만 추출해 int. 없으면 0."""
    if not s:
        return 0
    d = re.sub(r"[^\d]", "", s)
    return int(d) if d else 0


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def _pages_text(pdf_bytes: bytes) -> list[str]:
    """pdfplumber로 페이지별 텍스트. 페이지 캐시는 즉시 해제(메모리 안전)."""
    out: list[str] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            out.append(page.extract_text() or "")
            try:
                page.flush_cache()
            except Exception:
                pass
    return out


def _detect_insurer(text: str) -> str:
    """텍스트에서 보험사명 추출(감지 실패 시 '알 수 없음')."""
    norm = _norm(text)
    for k in _KNOWN_INSURERS:
        if _norm(k) in norm:
            return k
    if "KB손보" in norm or "KB손해" in norm:
        return "KB손해보험"
    if "한화손보" in norm or "한화손해" in norm:
        return "한화손해보험"
    return "알 수 없음"


def _extract_premium(text: str) -> int:
    """월납보험료(원)를 추출. '월납보험료 합계/월 보험료/보험료 합계' 인근 숫자."""
    for pat in (
        r"월납보험료\s*합계\D{0,8}([\d,]{3,})",
        r"(?:월납보험료|월\s*보험료|월\s*납입보험료)\D{0,8}([\d,]{3,})",
        r"보험료\s*합계\D{0,8}([\d,]{3,})",
    ):
        m = re.search(pat, text)
        if m:
            return _digits(m.group(1))
    return 0


# 담보 줄 패턴: ① 보장유형(정액|실손) 담보명 금액  ② 담보명 금액'만원'.
_COV_TYPED = re.compile(r"(정액|실손)\s+([가-힣A-Za-z()\[\]·/\d\s]{2,40}?)\s+([\d,]{2,7})\b")
_COV_MANWON = re.compile(r"([가-힣A-Za-z()\[\]·/]{2,40}?)\s+([\d,]{2,7})\s*만원")
# 노이즈 라인(계약현황·헤더·면책 등) — 담보 추출에서 제외.
_COV_SKIP = (
    "합계", "월납보험료", "기납입", "잔여", "페이지", "약관", "분석자료", "단위",
    "납입방법", "보장기간", "계약자", "가입년월", "보험계약정보", "회사명", "상품명",
)


def _extract_coverages(text: str) -> list[dict]:
    """담보명+보장금액(만원) 목록 추출(범용). '보장명' 세부는 금액 뒤 한글 토큰.

    ★ PII 회피·노이즈 제거: 보험사명·날짜(YYYY/MM)·연도형 금액·계약현황 헤더 라인은 제외하고,
      보장유형(정액/실손) 또는 명시적 '만원'이 있는 줄만 담보로 인정한다.
    """
    covs: list[dict] = []
    for raw in text.split("\n"):
        line = raw.strip()
        if not line or any(s in line for s in _COV_SKIP):
            continue
        if _DATE_YM.search(line):                 # YYYY/MM 포함(계약현황 행) 제외
            continue
        nline = _norm(line)
        if any(_norm(k) in nline for k in _KNOWN_INSURERS):  # 회사명 포함 행 제외(이름 동반 가능)
            continue
        m = _COV_TYPED.search(line)
        if m:
            cov_type, name, amt_s, end = m.group(1), m.group(2), m.group(3), m.end()
        else:
            m2 = _COV_MANWON.search(line)
            if not m2:
                continue
            cov_type, name, amt_s, end = "", m2.group(1), m2.group(2), m2.end()
        name = re.sub(r"\s+", " ", (name or "").strip())
        amount = _digits(amt_s)
        if len(_norm(name)) < 2 or amount <= 0 or 1900 <= amount <= 2100:  # 연도형 금액 제외
            continue
        tail = line[end:].strip()
        coverage_names = [t.strip() for t in re.split(r"[,，]", tail) if 2 <= len(_norm(t)) <= 30][:6]
        covs.append({"type": cov_type, "name": name[:40], "amount": amount, "coverage_names": coverage_names})
    # 중복(같은 이름+금액) 제거
    seen, uniq = set(), []
    for c in covs:
        key = (c["name"], c["amount"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(c)
    return uniq


def _summary(contracts: list[dict]) -> dict:
    total = sum(c.get("monthly_premium") or 0 for c in contracts)
    main: dict[str, int] = {}
    for c in contracts:
        for cov in c.get("coverages") or []:
            nm = cov.get("name") or ""
            if nm:
                main[nm] = main.get(nm, 0) + (cov.get("amount") or 0)
    return {"total_monthly_premium": total, "main_coverages": main}


def _empty_result(doc_type: str, insurer: str, warnings: list[str]) -> dict:
    return {
        "insurer": insurer,
        "doc_type": doc_type,
        "contracts": [],
        "summary": {"total_monthly_premium": 0, "main_coverages": {}},
        "parse_warnings": warnings,
    }


def _parse_current_generic(pages: list[str], insurer: str, warnings: list[str]) -> dict:
    """공통 보장분석서 레이아웃(보험계약현황 표 + 증권별 보장내역)을 범용 파싱.

    한화/KB 형식도 동일 골격을 공유하므로 회사 분기는 이 함수에 위임하고,
    회사별 미세 차이는 추후 보정 레이어에서 처리한다(현재는 best-effort).
    """
    full = "\n".join(pages)
    contracts: list[dict] = []

    # 1) 보험계약현황 표의 계약 행: '회사명 ... 가입년월(YYYY/MM) ... 보험료' 휴리스틱.
    #    상품명이 줄바꿈될 수 있어, 회사명+가입년월이 같은 줄에 있는 행을 1차 후보로 본다.
    insurer_alt = "|".join(re.escape(k) for k in _KNOWN_INSURERS)
    # 행 구조: 회사명 [상품명] [계약자명] 가입년월 납입기간 보장기간 납입방법 보험료
    #   ★ group3(계약자명)은 PII — 캡처하되 저장하지 않는다(product_name과 분리해 누수 방지).
    row_re = re.compile(
        rf"({insurer_alt})\s+(.+?)\s+([가-힣][가-힣*]{{1,4}})\s+(20\d{{2}}/\d{{1,2}})\s+"
        rf"(\d{{1,3}}년납|0년납|일시납|전기납)\s+(\d{{1,3}}세만기|\d{{1,3}}년만기|종신)\s+"
        rf"(월납|연납|일시납)\s+([\d,]+)"
    )
    for m in row_re.finditer(full):
        contracts.append({
            "product_name": re.sub(r"\s+", " ", m.group(2).strip())[:60],
            "contractor": "",  # ★ 계약자(성명)는 PII — 저장하지 않는다(group3 미사용).
            "join_date": m.group(4),
            "coverage_end": m.group(6).strip(),
            "monthly_premium": _digits(m.group(8)),
            "payment_period": m.group(5).strip(),
            "coverages": [],
        })

    # 2) 증권별 보장내역 — 페이지에서 '보장내역' 이후의 담보를 가까운 계약에 귀속(범용).
    #    매핑이 모호하면 첫 계약 또는 단일 가상계약에 합산.
    cov_all: list[dict] = []
    for pg in pages:
        if "보장내역" in pg or "보장유형" in pg:
            cov_all.extend(_extract_coverages(pg))

    if contracts:
        # 단순 귀속: 전체 담보를 계약 수로 정밀 분배하기 어려우므로 첫 계약에 모으되 경고.
        contracts[0]["coverages"] = cov_all
        if len(contracts) > 1 and cov_all:
            warnings.append("담보-계약 정밀 매핑 미구현: 담보를 첫 계약에 합산 표시(증권별 확인 권장).")
    elif cov_all:
        contracts.append({
            "product_name": "(자동 추출)",
            "contractor": "", "join_date": "", "coverage_end": "",
            "monthly_premium": _extract_premium(full), "payment_period": "",
            "coverages": cov_all,
        })
        warnings.append("계약현황 표 인식 실패 — 담보만 추출(상품/보험료 수동 확인 권장).")

    if not contracts:
        warnings.append("계약·담보를 인식하지 못했습니다. PDF 형식을 확인해 주세요.")

    return {
        "insurer": insurer,
        "doc_type": "current",
        "contracts": contracts,
        "summary": _summary(contracts) if contracts else {"total_monthly_premium": _extract_premium(full), "main_coverages": {}},
        "parse_warnings": warnings,
    }


def parse_hanwha_current(pages_text: list[str]) -> dict:
    """한화손보 보장분석서(current). 공통 골격 위임 + 한화 식별."""
    warnings = ["한화손보 전용 보정 미적용(공통 파서로 처리) — 일부 항목 수동 확인 권장."]
    return _parse_current_generic(pages_text, "한화손해보험", warnings)


def parse_kb_current(pages_text: list[str]) -> dict:
    """KB손보 보장분석서(current). 공통 골격 위임 + KB 식별."""
    warnings = ["KB손보 전용 보정 미적용(공통 파서로 처리) — 일부 항목 수동 확인 권장."]
    return _parse_current_generic(pages_text, "KB손해보험", warnings)


def parse_proposal_generic(pages_text: list[str]) -> dict:
    """가입제안서(proposal) 범용 파싱 — 회사/상품 무관 담보·보험료·보험사 추출."""
    full = "\n".join(pages_text)
    warnings: list[str] = []
    insurer = _detect_insurer(full)
    if insurer == "알 수 없음":
        warnings.append("보험사명 자동 감지 실패 — 수동 확인 권장.")
    premium = _extract_premium(full)
    if premium == 0:
        warnings.append("월납보험료 자동 감지 실패 — 수동 확인 권장.")
    coverages = _extract_coverages(full)
    if not coverages:
        warnings.append("담보를 추출하지 못했습니다 — PDF 형식 확인 권장.")

    # 보장기간(세만기/년만기) 1차 추출
    mterm = _TERM.search(full)
    contract = {
        "product_name": "(제안 상품)",
        "contractor": "",
        "join_date": "",
        "coverage_end": (mterm.group(1).replace(" ", "") if mterm else ""),
        "monthly_premium": premium,
        "payment_period": "",
        "coverages": coverages,
    }
    contracts = [contract]
    return {
        "insurer": insurer,
        "doc_type": "proposal",
        "contracts": contracts,
        "summary": _summary(contracts),
        "parse_warnings": warnings,
    }


def parse_coverage_pdf(pdf_bytes: bytes, doc_type: str) -> dict:
    """메인 진입점. doc_type: 'current' | 'proposal'.

    - current → 보험사 감지 후 한화/KB 분기(그 외/실패는 공통 파서).
    - proposal → parse_proposal_generic.
    PDF 열기 실패는 ValueError로 던진다(엔드포인트가 400 처리). 그 외 파싱 이상은 warnings.
    """
    try:
        pages = _pages_text(pdf_bytes)
    except Exception as e:  # 손상·암호 등 열기 실패
        raise ValueError(f"PDF를 열 수 없습니다: {e}")

    if not any((t or "").strip() for t in pages):
        warnings = ["텍스트가 인식되지 않는 PDF입니다(이미지·스캔본일 수 있음). '파일'로 내려받은 PDF를 사용해 주세요."]
        return _empty_result(doc_type, "알 수 없음", warnings)

    if doc_type == "proposal":
        return parse_proposal_generic(pages)

    # current
    full = "\n".join(pages)
    insurer = _detect_insurer(full)
    if insurer == "한화손해보험":
        return parse_hanwha_current(pages)
    if insurer == "KB손해보험":
        return parse_kb_current(pages)
    return _parse_current_generic(pages, insurer, ["회사 전용 파서 미해당 — 공통 파서로 처리."])
