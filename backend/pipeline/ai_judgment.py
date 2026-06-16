"""Gemini AI 호출 일체 — analyzer.py 에서 이동."""
from __future__ import annotations

import asyncio
import json
import re

from google import genai
from google.genai import types

from .helpers import AnalysisError, _worst_insurance_verdict, extract_json

# ── 텍스트 필터링 보조 (BOHUMFIT-ROLLBACK-001) ────────────────────
# 318p PDF 같은 대용량 입력에서 의미 없는 반복 헤더/노이즈/중복을 제거해
# 잘림 상한 내에 실제 진료 데이터가 더 많이 담기도록 한다.

# 반복되는 표 헤더로 판단할 키워드 (한 줄에 2개 이상 동시 등장 시 헤더로 본다)
_REPEAT_HEADER_KEYWORDS = (
    "요양기관명", "상병코드", "상병명", "진료시작일", "진료개시일",
    "진료내역", "처방내역", "조제내역", "투약일수", "1회투약량",
    "1일투약량", "총투약일수", "급여여부", "심사결과", "처방일자",
    "조제일자", "수가코드", "행위명칭", "행위코드", "단가", "수량",
    "금액", "본인부담", "공단부담", "분류", "구분",
)

# 숫자·날짜·코드 신호 (있으면 진료 데이터로 본다)
_SIGNAL_PATTERNS = (
    re.compile(r"\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2}"),  # 날짜
    re.compile(r"[A-Z]\d{2,}"),                       # 상병/행위 코드
    re.compile(r"\d{3,}"),                            # 3자리 이상 숫자
)


def _looks_like_repeated_header(line: str) -> bool:
    """한 줄에 _REPEAT_HEADER_KEYWORDS 키워드가 2개 이상이면 반복 헤더."""
    if not line:
        return False
    norm = line.replace(" ", "").replace("\t", "")
    hits = sum(1 for kw in _REPEAT_HEADER_KEYWORDS if kw in norm)
    return hits >= 2


def _has_signal(line: str) -> bool:
    """숫자·날짜·코드 패턴 중 하나라도 있으면 의미 있는 데이터로 간주."""
    if not line:
        return False
    return any(p.search(line) for p in _SIGNAL_PATTERNS)


def _strengthen_filter(lines: list[str]) -> list[str]:
    """반복 헤더·연속 중복·노이즈 줄을 제거한다.

    BOHUMFIT-ROLLBACK-001: 318p 같은 대용량 PDF에서 잘림 상한 내에 실제 진료
    데이터가 더 많이 들어가도록 텍스트를 압축한다. 정렬은 하지 않는다
    (analyzer 가 이미 시간 역순으로 정렬해서 넘긴다).
    """
    out: list[str] = []
    prev: str = ""
    for raw in lines:
        if raw is None:
            continue
        line = raw.rstrip()
        if not line.strip():
            continue
        # 1) 매우 짧은 줄 (≤2 chars) — 단독으로는 의미 없음
        if len(line.strip()) <= 2:
            continue
        # 2) 반복 헤더 (요양기관명·상병코드 등 키워드 2개↑ 포함)
        if _looks_like_repeated_header(line):
            continue
        # 3) 노이즈 — 신호(숫자·날짜·코드) 전혀 없고 짧은(<10) 줄
        if len(line.strip()) < 10 and not _has_signal(line):
            continue
        # 4) 직전과 동일한 줄(연속 중복)
        if line == prev:
            continue
        out.append(line)
        prev = line
    return out

# ── 의학 판단 전용 시스템 프롬프트 ──────────────────────────────
# BOHUMFIT-VERIFY-001: 결정성 향상 — 주관적 표현("재발 가능성", "재방문 가능성") 을
# 데이터 근거 기반의 결정론 조건으로 치환. 동일 입력에 대해 동일 출력을 강제한다.
MEDICAL_JUDGMENT_SYSTEM_PROMPT = """당신은 한국 보험 언더라이팅 전문 의사입니다.
설계사가 고객의 알릴의무를 판단할 수 있도록 의학적 관점에서 분석합니다.

★ 절대 규칙: 동일한 입력 데이터에 대해 동일한 출력을 내야 합니다.
   - 추측·확률 표현 금지.
   - 입력에 명시된 사실(KCD 코드·날짜·검사명·처방 종료일) 만 근거로 사용.
   - 데이터에 명시되지 않은 미래 사건 추정(향후 재발·향후 재방문 등) 은 모두 false 로 처리.

판단할 항목:
1. 추가검사/재검사 여부 (1년 이내 알릴의무 Q2)
2. 치료 종결 여부 (3개월 이내 알릴의무 Q1)

반드시 JSON 형식으로만 응답하세요.

[판단 1: 추가검사/재검사 여부 — 1년 이내 알릴의무 Q2]
정의:
 - 추가검사 = 선행 검사 결과에 따라 '다른 종류'의 후속 검사가 필요해진 경우 (예: 유방초음파 → 조직검사).
 - 재검사 = 선행 검사 결과가 애매·이상하여 '같은 검사'를 다시 시행한 경우.
detail_test_events 와 same_day_detail_actions 만 근거로 사용. 아래 확정 4기준을 모두 따져 판단:
 ① 선행검사 존재: 후속 검사 이전에 선행 검사가 실제로 있었는가.
 ② 후속검사 필요성: 선행 결과(이상소견/애매)로 후속검사가 필요해졌는가 — reason·검사명에 "이상/의심/추정/재검/추가" 신호가 있거나, 선행과 '다른 종류' 검사가 뒤따랐는가.
 ③ 단순 추적관찰이 아닌가: 병증 변화·치료 없이 정기 간격으로 같은 검사를 반복하는 추적관찰/정기검진/건강검진/스크리닝은 추가검사·재검사가 아니다.
 ④ 같은날 일련검사가 아닌가: 같은 날 동시·연속으로 시행된 검사 묶음(초진 당일 기본 검사 패널 등)은 진단을 위한 '한 과정'이며 추가검사·재검사가 아니다.

판정:
 - true: ①선행검사가 있고 ②결과로 '다른 종류' 후속검사 또는 이상소견 동반 재검사가 발생했으며 ③추적관찰이 아니고 ④같은날 일련검사가 아닌 경우.
 - false (다음은 항상 false):
   · 동일 검사를 반복하나 이상소견·치료 변화가 없는 추적관찰. ※ '동일검사 반복'이라는 사실만으로 true 로 판단하지 말 것 — 이상소견 신호가 없으면 추적관찰로 보아 false.
   · 정기검진·건강검진·스크리닝·예방접종·단순 스케일링.
   · 같은 날 한 번에 시행된 일련의 검사(동시·연속) 묶음.
   · 검사 후 추가 검사 없이 단순 치료만 이어진 경우.
 - 판단 불가 시 false (보수적). 단, 명백히 이상소견을 동반한 후속검사·재검사는 false 로 떨구지 말 것 (고지 누락 방지 — 과소가 과검보다 위험).

[판단 2: 치료 종결 여부]
입력의 last_prescription_end_date(처방 종료일), KCD 코드, 진단일을 근거로 사용:
1) 만성 KCD 코드 → 항상 true (진행 중):
   - E10~E14 (당뇨), I10~I15 (고혈압), J45 (천식), N18 (만성신부전),
     K70~K77 (만성 간질환, K74 포함), F20~F29 (조현병 계열),
     F31~F33 (양극성/주요우울), M05~M14 (만성 류마티스 계열).
2) 처방 종료일이 입력에 명시되고 (today_str - last_prescription_end_date) ≤ 30일 → true.
3) 처방 종료일이 입력에 명시되고 (today_str - last_prescription_end_date) > 30일
   AND 만성 코드 아님 AND 최근 90일 내 신규 진단 없음 → false (종결됨).
4) 일회성/급성 KCD 코드 (J00~J06 감기 계열, S00~S99 외상 등) 이고
   최근 90일 진단·처방 없음 → false.
5) 위 어느 규칙으로도 결정 불가능하면 false (보수적 — 미래 사건 추측 금지)."""


def _finalize_raw_text_for_gemini(
    filtered_lines: list[str],
    visit_count_lines: list[str],
    cross_surgery_hints: list[str],
    first_diag_lines: list[str],
    drug_change_text: str,
    presc_end_text: str,
) -> str:
    # BOHUMFIT-ROLLBACK-001: 잘림 상한 내 데이터 밀도를 높이기 위해 필터 강화.
    # 반복 헤더·연속 중복·짧은 노이즈 줄을 제거.
    # BOHUMFIT-BUG-009: 318p PDF(약 13,000줄 / 293K자) 전체를 커버하도록 상한 대폭 상향.
    # BUG-008 메리츠 간편 제거로 Gemini 호출이 PDF 1건당 1회만 남았고, 타임아웃 한도 300초에
    # 충분한 여유가 있어 가능. 사용자 분기표 X≥8000 티어 적용 (13,000줄 / 300K자).
    cleaned_lines = _strengthen_filter(filtered_lines)
    # 기존: filtered_lines[:800] → 2000 → 3000 → 13_000 (BOHUMFIT-BUG-009 상향, 318p 전체 커버)
    raw_text = "\n".join(cleaned_lines[:13_000])
    if visit_count_lines:
        raw_text = "[10년내 질병코드별 통원횟수 집계 — Q4 7회이상통원 판단 기준]\n" \
                   + "\n".join(visit_count_lines) + "\n\n" + raw_text
    if cross_surgery_hints:
        raw_text = "[기본/세부 동일일자 교차검증 — 수술 추정 근거]\n" \
                   + "\n".join(f"- {h}" for h in cross_surgery_hints[:80]) + "\n\n" + raw_text
    if first_diag_lines:
        raw_text = "[질병별 최초·최종 진단일 — 고지사항 최초진단일 확인]\n" \
                   + "\n".join(first_diag_lines[:100]) + "\n\n" + raw_text
    if drug_change_text:
        raw_text = drug_change_text + "\n" + raw_text
    if presc_end_text:
        raw_text = presc_end_text + "\n" + raw_text
    # 기존: MAX_RAW_TEXT_LEN = 30_000 → 80_000 → 100_000 → 300_000 (BOHUMFIT-BUG-009 상향, 318p 전체 커버)
    MAX_RAW_TEXT_LEN = 300_000
    if len(raw_text) > MAX_RAW_TEXT_LEN:
        raw_text = raw_text[:MAX_RAW_TEXT_LEN] + "\n... (truncated)"
    return raw_text


def _merge_ai_results(parts: list[dict]) -> dict:
    if not parts:
        raise AnalysisError("AI 분석 결과가 없습니다.")
    merged: dict = {
        "flagged_items": [],
        "exempt_items": [],
        "drug_change_hit": False,
        "drug_change_reason": "",
        "total_flagged": 0,
    }
    # BOHUMFIT-BUG-008: 간편심사 제거 — simple_* 키 제외.
    hit_bool_keys = [
        "q1_hit", "q2_hit", "q3_hit", "q4_hit",
    ]
    reason_join_keys = [
        "q1_reason", "q2_reason", "q3_reason", "q4_reason",
    ]
    for p in parts:
        merged["flagged_items"].extend(p.get("flagged_items") or [])
        merged["exempt_items"].extend(p.get("exempt_items") or [])
        if p.get("drug_change_hit"):
            merged["drug_change_hit"] = True

    for k in hit_bool_keys:
        merged[k] = any(bool(x.get(k)) for x in parts)

    for k in reason_join_keys:
        texts = [x.get(k) for x in parts if x.get(k)]
        merged[k] = "; ".join(texts) if texts else ""

    dcr = [x.get("drug_change_reason") for x in parts if x.get("drug_change_reason")]
    merged["drug_change_reason"] = "; ".join(dcr) if dcr else ""

    # BOHUMFIT-BUG-008: 간편심사 제거 — simple_* 병합 로직 삭제.

    merged["health_verdict"] = _worst_insurance_verdict(*(x.get("health_verdict") or "" for x in parts))
    hr = [x.get("health_reason") for x in parts if x.get("health_reason")]
    merged["health_reason"] = "; ".join(hr) if hr else ""

    rec = [x.get("recommend") for x in parts if x.get("recommend")]
    merged["recommend"] = "; ".join(rec) if rec else ""

    summ = [x.get("summary") for x in parts if x.get("summary")]
    merged["summary"] = "\n".join(summ) if summ else ""

    merged["total_flagged"] = len(merged["flagged_items"])
    return merged


async def _call_medical_judgment(
    type1_items: list[dict],
    type2_items: list[dict],
    api_key: str,
) -> dict:
    """추가검사/재검사 + 치료 종결 여부를 단일 Gemini 배치 호출로 판단."""
    if not type1_items and not type2_items:
        return {"additional_tests": {}, "treatment_ongoing": {}}

    parts = []
    if type1_items:
        parts.append(
            "[추가검사/재검사 판단 목록]\n"
            + json.dumps(type1_items, ensure_ascii=False, indent=2)
        )
    if type2_items:
        parts.append(
            "[치료 종결 여부 판단 목록]\n"
            + json.dumps(type2_items, ensure_ascii=False, indent=2)
        )

    contents = "\n\n".join(parts) + """

[추가검사/재검사 판단 원칙]
- detail_test_events는 세부진료 행위 중 검사 후보만 기계적으로 추린 자료입니다. 이 목록이 있다고 해서 곧바로 추가검사/재검사 고지가 아닙니다.
- 같은 질병코드에서 최근 1년 이내 검사 후보가 2회 이상 또는 2종 이상인 경우만 후보로 전달됩니다.
- true 판단: 진찰/검사 후 이상소견 확인, 추적 관찰 중 재검, 추가 진단 목적 검사, 같은 질병에 대한 반복 확인 검사로 보이는 경우.
- false 판단: 초진 당일 한 번에 시행된 기본 검사 묶음, 건강검진/스크리닝/정기 모니터링, 단순 처방·처치 전 확인검사, 검사 후 추가 검사 없이 치료만 이어진 경우.
- same_day_detail_actions를 함께 보고 진찰/처방/처치와 검사 후보가 어떤 관계인지 판단하세요.

반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트 없이 순수 JSON:
{
  "additional_tests": [
    {"disease_code": "코드", "is_additional_test": true또는false, "test_type": "재검사 또는 정기검사", "reason": "판단 근거"}
  ],
  "treatment_ongoing": [
    {"disease_code": "코드", "is_ongoing": true또는false, "reason": "판단 근거"}
  ]
}"""

    try:
        api_client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=120_000),
        )
    except TypeError:
        api_client = genai.Client(api_key=api_key)

    # BOHUMFIT-VERIFY-001: 결정성 보조 (temperature=0 + top_k=1 + seed 고정 + JSON mime).
    # google-genai SDK 가 일부 파라미터를 미지원하면 TypeError → fallback 으로 안전 처리.
    try:
        config = types.GenerateContentConfig(
            system_instruction=MEDICAL_JUDGMENT_SYSTEM_PROMPT,
            temperature=0,
            top_p=1.0,
            top_k=1,
            seed=42,
            response_mime_type="application/json",
        )
    except TypeError:
        config = types.GenerateContentConfig(
            system_instruction=MEDICAL_JUDGMENT_SYSTEM_PROMPT,
            temperature=0,
        )

    def _sync_gen():
        return api_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=config,
        )

    try:
        if hasattr(api_client, "aio") and hasattr(api_client.aio.models, "generate_content"):
            message = await api_client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=config,
            )
        else:
            message = await asyncio.to_thread(_sync_gen)

        raw = message.text if getattr(message, "text", None) else ""
        if not raw.strip():
            return {"additional_tests": {}, "treatment_ongoing": {}}

        result = extract_json(raw)
        at_out = {
            item["disease_code"]: item
            for item in result.get("additional_tests", [])
            if isinstance(item, dict) and "disease_code" in item
        }
        to_out = {
            item["disease_code"]: item
            for item in result.get("treatment_ongoing", [])
            if isinstance(item, dict) and "disease_code" in item
        }
        return {"additional_tests": at_out, "treatment_ongoing": to_out}
    except Exception as e:
        return {"additional_tests": {}, "treatment_ongoing": {}, "_error": str(e)[:120]}



async def _call_q2_health_findings(q2_items: list[dict], reference_date, api_key: str) -> dict:
    """BOHUMFIT-009: Q2 건강체 항목별 '추가검사·재검사 의심 소견' 텍스트 생성.

    q2_items 는 filters._build_q2_health_items 가 만든 결정론 결과 list.
    각 항목에 대해 코드/병명 기반으로 일반적인 의심 추가검사 한 줄을 부착한다.
    temperature=0/seed=42/top_k=1 로 결정성 보장.

    반환: {disease_code: suspicion_text} 매핑. 호출 실패 시 빈 dict.
    """
    if not q2_items:
        return {}

    payload = [
        {
            "disease_code": (it.get("code") or "").upper(),
            "disease_name": it.get("disease") or "",
            "diagnosis_date": it.get("date", ""),
            "hospital": it.get("hospital", ""),
        }
        for it in q2_items
    ]

    contents = (
        f"기준일: {reference_date}\n"
        f"[Q2 건강체 1년이내 확정진단 목록 — 추가검사·재검사 의심 소견 부착]\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + (
            "\n\n[판단 기준]\n"
            "- 추가검사: A검사 시행 후 다른 종류의 B검사로 보완(예: X-ray 후 MRI·CT·혈액검사).\n"
            "- 재검사: 같은 종류의 검사를 다시 시행.\n"
            "- 제외(해당없음): 단순 처방만, 추적관찰, 일련의 진단 과정 일부, 일반인이 인식·기대하기 어려운 경우.\n"
            "- 불확실하면 '낮음' 또는 '해당없음'을 우선(보수적 판단).\n"
            "각 진단코드/병명별로 추가검사·재검사 가능성을 '높음'/'낮음'/'해당없음' 중 하나로 판정하고,\n"
            "의심되는 검사를 한 줄로 적으세요. 반드시 JSON 형식으로만 응답:\n"
            "{\n"
            "  \"findings\": [\n"
            "    {\"disease_code\": \"<코드>\", \"possibility\": \"높음|낮음|해당없음\", \"suspicion\": \"<의심 검사 한 줄>\"}\n"
            "  ]\n"
            "}\n"
        )
    )

    try:
        api_client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=120_000),
        )
    except TypeError:
        api_client = genai.Client(api_key=api_key)

    # BOHUMFIT-VERIFY-001 + BOHUMFIT-009: 결정성 파라미터 유지.
    try:
        config = types.GenerateContentConfig(
            system_instruction=(
                "당신은 한국 보험 심사(언더라이팅) 경험이 풍부한 임상의사입니다. "
                "1년이내 확정진단 항목에 대해 추가검사·재검사 가능성을 보수적으로 판단합니다. "
                "불확실하면 낮음/해당없음을 우선합니다. 동일 입력 → 동일 출력."
            ),
            temperature=0,
            top_p=1.0,
            top_k=1,
            seed=42,
            response_mime_type="application/json",
        )
    except TypeError:
        config = types.GenerateContentConfig(
            system_instruction=(
                "당신은 한국 보험 심사(언더라이팅) 경험이 풍부한 임상의사입니다. "
                "1년이내 확정진단의 추가검사·재검사 가능성을 보수적으로(높음/낮음/해당없음) 판단합니다."
            ),
            temperature=0,
        )

    def _sync_gen():
        return api_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=config,
        )

    try:
        if hasattr(api_client, "aio") and hasattr(api_client.aio.models, "generate_content"):
            message = await api_client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=config,
            )
        else:
            message = await asyncio.to_thread(_sync_gen)
        raw = message.text if getattr(message, "text", None) else ""
        if not raw.strip():
            return {}
        result = extract_json(raw)
        out: dict = {}
        for item in result.get("findings", []) or []:
            if not isinstance(item, dict):
                continue
            code = (item.get("disease_code") or "").upper().strip()
            susp = (item.get("suspicion") or "").strip()
            poss = (item.get("possibility") or "").strip()
            # BOHUMFIT-041: '해당없음'·불명은 부착 안 함(폴백). '높음/낮음'만 가능성 표기와 함께 부착.
            if code and susp and poss in ("높음", "낮음"):
                out[code] = f"[추가검사·재검사 가능성 {poss}] {susp}"
        return out
    except Exception:
        return {}


async def analyze_single_pdf(parsed_data: dict, product_type: str, reference_date, api_key: str) -> dict:
    """파싱된 PDF 1건에 대해 Gemini 분석 (비동기)."""
    _ = reference_date
    fname = parsed_data["filename"]
    today_str = parsed_data["today_str"]
    raw_text = parsed_data["raw_text"]
    system_prompt = parsed_data["system_prompt"]
    retry_local: list[str] = []

    GEMINI_TIMEOUT_SECONDS = 240
    try:
        api_client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_SECONDS * 1000),
        )
    except TypeError:
        api_client = genai.Client(api_key=api_key)

    ai_result = None
    last_error = None
    raw_response = ""
    MAX_RETRIES = 5
    RETRY_DELAYS = [5, 10, 20, 40, 60]
    contents = f"고객 기준일: {today_str}\n심사 유형: {product_type}\n\n진료 데이터:\n{raw_text}"
    # BOHUMFIT-VERIFY-001: 결정성 보조 (temperature=0 + top_k=1 + seed 고정 + JSON mime).
    try:
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0,
            top_p=1.0,
            top_k=1,
            seed=42,
            response_mime_type="application/json",
        )
    except TypeError:
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0,
        )

    def _sync_generate():
        return api_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=config,
        )

    for attempt in range(MAX_RETRIES):
        try:
            if hasattr(api_client, "aio") and hasattr(api_client.aio.models, "generate_content"):
                message = await api_client.aio.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=contents,
                    config=config,
                )
            else:
                message = await asyncio.to_thread(_sync_generate)
            raw_response = message.text if getattr(message, "text", None) else ""
            if not raw_response.strip():
                raise ValueError("AI 응답이 비어있습니다.")
            ai_result = extract_json(raw_response)
            break
        except (ValueError, json.JSONDecodeError) as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                continue
            return {
                "filename": fname,
                "ai_result": None,
                "retry_warnings": retry_local,
                "error": f"AI 응답 파싱 오류: {e}",
                "raw_response_snip": raw_response[:800],
            }
        except Exception as e:
            err_str = str(e)
            _retryable = ("503", "UNAVAILABLE", "high demand", "overloaded",
                          "429", "RESOURCE_EXHAUSTED", "rate limit", "quota")
            if any(s in err_str for s in _retryable) and attempt < MAX_RETRIES - 1:
                wait = RETRY_DELAYS[attempt]
                retry_local.append(
                    f"[{fname}] Gemini 호출이 지연되어 {wait}초 후 재시도합니다... ({attempt + 1}/{MAX_RETRIES - 1})"
                )
                await asyncio.sleep(wait)
                continue
            return {"filename": fname, "ai_result": None, "retry_warnings": retry_local, "error": str(e)}

    if ai_result is None:
        return {
            "filename": fname,
            "ai_result": None,
            "retry_warnings": retry_local,
            "error": str(last_error),
            "raw_response_snip": raw_response[:800] if raw_response else "",
        }

    return {"filename": fname, "ai_result": ai_result, "retry_warnings": retry_local, "error": None}
