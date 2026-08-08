# -*- coding: utf-8 -*-
"""BOHUMFIT-277 — PII 경계 유틸(서버 측 익명화 정본).

★설계 원칙(275 B 섹션 → 277): **서버에서 익명화한다.**
  271은 화면 표시 직전에만 파일명을 지웠고, 그 결과 서버 응답 raw·운영 로그·DB 저장분에는
  원본 파일명이 그대로 남았다(B-F1·B-F2). 파일명에는 환자 실명이 들어간다는 것이 271의 실측이다.
  → 응답·로그·저장 **이전**에 파일 식별자를 익명 slot으로 정규화하고,
    271의 표시 직전 sanitization은 **방어 2선**으로 남긴다(제거하지 않는다).

★slot 규칙은 이미 두 곳에 선례가 있고 서로 같다 — 여기서 그대로 따른다:
  - 268b `progress.py`: ``f"서류 {N}"`` (1-based 등장 순서)
  - 271 `errorMessages.ts`: ``서류 ${index + 1}``
  같은 규칙을 서버가 **먼저** 적용하면 프런트의 재정규화가 멱등이 되어 두 겹이 충돌하지 않는다.
"""
from __future__ import annotations

import re

DOCUMENT_SLOT_PREFIX = "서류"


def document_slot(index: int) -> str:
    """0-based 파일 index → 사용자에게 보여줄 익명 라벨(1-based).

    268b·271과 같은 문자열을 만든다 — 규칙이 갈라지면 같은 파일이 화면마다 다른 번호로 보인다.
    """
    return f"{DOCUMENT_SLOT_PREFIX} {index + 1}"


def _variants(filename: str) -> list[str]:
    """같은 파일을 가리키는 표기 변형(확장자 유무·공백 제거)을 모은다."""
    name = (filename or "").strip()
    if not name:
        return []
    out = {name}
    stem = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", name)
    if stem and stem != name:
        out.add(stem)
    # 긴 것부터 지워야 부분 치환으로 잔재가 남지 않는다.
    return sorted((v for v in out if v), key=len, reverse=True)


def mask_filename(text: str, filename: str, index: int) -> str:
    """`text` 안의 원본 파일명을 익명 slot으로 바꾼다.

    ★파일명을 지우되 **몇 번째 서류인지는 남긴다** — 사용자가 어느 파일을 다시 받아야 할지
    알아야 행동할 수 있다(271이 같은 이유로 slot을 남겼다).
    """
    if not text:
        return text
    slot = document_slot(index)
    masked = str(text)
    for variant in _variants(filename):
        masked = masked.replace(variant, slot)
    return masked


def mask_filenames(text: str, filenames: list[str] | tuple[str, ...]) -> str:
    """여러 파일명을 한 문자열에서 모두 마스킹한다(로그·예외 문자열용).

    ★BOHUMFIT-277b(R2): 예전에는 **파일 단위로 순회**하며 각자의 변형만 길이순 정렬했다.
      그래서 `["a.pdf", "a long.pdf"]`에서 첫 파일의 stem `a`가 먼저 치환돼
      `"🔒 a long.pdf: 오류"` → `"🔒 서류 1 long.pdf: 오류"`로 **`long.pdf`가 남았다**(Codex 재현).
      272b 상품명 절삭에서 겪은 부분 문자열 함정과 같은 형태다.
      → **전체 파일의 모든 후보를 모아 전역 길이 내림차순으로 치환**한다. 긴 이름이 항상 먼저 잡히므로
        짧은 이름이 긴 이름의 앞부분을 갉아먹지 못한다.
    ★slot 번호는 **원본 파일 index**를 유지한다(정렬은 치환 순서만 바꾼다).
    """
    masked = str(text or "")
    candidates: list[tuple[str, int]] = []
    for index, filename in enumerate(filenames or []):
        for variant in _variants(filename):
            candidates.append((variant, index))
    # ★전역 길이 내림차순. 같은 길이면 원본 순서를 지켜 결정적으로 만든다.
    candidates.sort(key=lambda item: (-len(item[0]), item[1]))
    for variant, index in candidates:
        masked = masked.replace(variant, document_slot(index))
    return masked


def anonymize_parse_errors(errors, filenames) -> list:
    """`parse_errors` 배열에서 원본 파일명을 전부 slot으로 교체한다.

    응답·저장 이전에 호출한다. 어떤 파일명이 어느 항목에 들어갔는지 모르므로 전체 목록으로 훑는다.
    """
    names = list(filenames or [])
    return [mask_filenames(str(item), names) for item in (errors or [])]


def scrub_result_filenames(payload, filenames):
    """분석 결과 payload 전체(중첩 포함)에서 파일명을 마스킹한다.

    ★B-F1 대응: history 저장은 최상위 ``customer_name``만 제거해 왔다. 중첩된 ``parse_errors``
    안의 파일명이 7일/90일 저장되던 경로를 막는다.
    ※건강정보(상병코드·병명·기관명) 보관 정책은 이 함수가 다루지 않는다 — 275 B-1 3항의
      기존 정책 그대로이며 변경은 별도 Human 결정 사안이다.
    """
    names = [n for n in (filenames or []) if n]
    if not names:
        return payload

    def walk(node):
        if isinstance(node, dict):
            return {key: walk(value) for key, value in node.items()}
        if isinstance(node, list):
            return [walk(item) for item in node]
        if isinstance(node, str):
            return mask_filenames(node, names)
        return node

    return walk(payload)


def contains_any_filename(text: str, filenames) -> bool:
    """검증용 — 문자열에 원본 파일명이 남아 있는지."""
    haystack = str(text or "")
    return any(name and name in haystack for name in (filenames or []))


# ★저장 직전 최후 방어선 — 원본 파일명 목록을 모르는 지점(history 저장 등)에서 쓴다.
#   서버는 이미 `analyzer`에서 slot으로 정규화하지만, 어떤 경로로든 `*.pdf` 토큰이 흘러왔다면
#   DB에 7일/90일 남는다(275 B-F1). 이 함수는 그 마지막 구멍을 막는다.
# ★한글 파일명에는 공백이 들어간다("가상고객A 최근 3개월.pdf"). 공백으로 끊는 토큰 정규식만으로는
#   앞의 실명이 그대로 남는다(실측). 그래서 두 규칙을 쓴다:
#   ①`{이모지} {파일명}.pdf: {사유}` **접두 구간 통째로** — 271 `sanitizeParseErrors`와 같은 형태다.
#   ②그 밖의 위치에 박힌 `*.pdf` 토큰.
_PDF_ERROR_PREFIX_RE = re.compile(r"^\s*\S*\s*[^:]*\.pdf\s*:\s*", re.IGNORECASE)
_PDF_NAME_RE = re.compile(r"[^\s:/\\\"']*\.pdf", re.IGNORECASE)


def _scrub_pdf_text(text: str) -> str:
    scrubbed = _PDF_ERROR_PREFIX_RE.sub(f"{DOCUMENT_SLOT_PREFIX}: ", text)
    return _PDF_NAME_RE.sub(DOCUMENT_SLOT_PREFIX, scrubbed)


def scrub_pdf_filenames_deep(payload):
    """중첩 구조 전체에서 `*.pdf` 파일명을 익명 라벨로 바꾼다(멱등).

    ★최후 방어선이다 — 정상 경로에서는 `analyzer`가 이미 slot으로 정규화한다.
    """

    def walk(node):
        if isinstance(node, dict):
            return {key: walk(value) for key, value in node.items()}
        if isinstance(node, list):
            return [walk(item) for item in node]
        if isinstance(node, str):
            return _scrub_pdf_text(node)
        return node

    return walk(payload)


# ── BOHUMFIT-277b(R1) — 건강정보 scrub ────────────────────────────────────
# ★277은 **파일명만** 지웠다. 그러나 파일명은 간접 식별자이고 **상병코드·병명은 건강정보 그 자체**다.
#   Codex 재현: `"가상고객A 최근 3개월.pdf I10 고혈압 서울병원"` → 파일명만 바뀌고 나머지는 그대로였다.
#
# ★★병명(진단명)은 **패턴으로 식별할 수 없다.** `keywords.json`에는 상병코드 목록과 수술·검사 키워드만
#   있고 **병명 사전이 없다**(전수 확인). `고혈압`·`상세불명의 만성 폐쇄성 폐질환` 같은 임의 한글을
#   안전하게 골라낼 방법이 없다.
#   → 그래서 임의 raw 문자열은 **애초에 내보내지 않는 계약**(`safe_error_summary`)이 1선이고,
#     아래 정규식 scrub은 그 위의 **방어 2선**이다. 정규식만으로 안전을 주장하지 않는다.
#
# ★과잉 scrub 금지: 사유 문구(`PDF 비밀번호 해제 실패` 등)와 `서류 N`·레코드 수는 **남긴다**.
#   277이 확보한 운영 진단 가능성을 되돌리지 않는다.
REDACTED = "[제거됨]"

#: 상병코드 — ICD-10 형식(영문 1자 + 숫자 2자 + 선택 소수점). `keywords.json`의 코드 목록과 같은 형태다.
_ICD_RE = re.compile(r"(?<![A-Za-z0-9])[A-Z]\d{2}(?:\.\d{1,2})?(?![A-Za-z0-9])")
#: 의료기관명 — 접미사 기반(앞 단어까지 함께 지운다).
_ORG_RE = re.compile(r"[가-힣A-Za-z0-9]*(?:병원|의원|한의원|클리닉|보건소|의료원|치과|약국)")


def scrub_health_terms(text: str) -> str:
    """상병코드·의료기관명을 지운다(병명은 사전이 없어 여기서 다루지 못한다 — 위 주석 참조)."""
    scrubbed = _ICD_RE.sub(REDACTED, str(text or ""))
    return _ORG_RE.sub(REDACTED, scrubbed)


def scrub_text(text: str) -> str:
    """운영 로그·Sentry로 나갈 문자열의 **방어 2선** — 파일명 + 건강정보."""
    return scrub_health_terms(_scrub_pdf_text(str(text or "")))


def scrub_deep(payload):
    """중첩 구조 전체에 `scrub_text`를 적용한다(멱등)."""

    def walk(node):
        if isinstance(node, dict):
            return {key: walk(value) for key, value in node.items()}
        if isinstance(node, list):
            return [walk(item) for item in node]
        if isinstance(node, str):
            return scrub_text(node)
        return node

    return walk(payload)


def safe_error_summary(error: BaseException | str, index: int | None = None) -> dict:
    """★1선 계약 — 예외에서 **안전한 구조화 필드만** 뽑는다(raw 본문은 담지 않는다).

    운영자가 "몇 번째 파일이 어떤 종류로 실패했는지"는 알 수 있어야 하므로
    `slot`·`kind`·`length`를 남긴다. 본문은 길이만 남기고 버린다.
    """
    kind = type(error).__name__ if isinstance(error, BaseException) else "str"
    raw = str(error)
    out = {"kind": kind, "length": len(raw)}
    if index is not None:
        out["slot"] = document_slot(index)
    return out
