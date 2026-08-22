# -*- coding: utf-8 -*-
"""BOHUMFIT-300 — 실 정본 문서 경로 해석을 **한 곳**에 모은 테스트 헬퍼.

★PII 0 계약: 실 고객명·실파일명을 테스트 소스에 쓰지 않는다. 대신 **익명 라벨(정본A~D)**로
  참조하고, 실제 파일은 gitignore 폴더 안에서 **패턴 + 구조 지표**로 식별한다.
  (296b `_real_q6_paths()`가 같은 방식을 먼저 썼다 — 그 선례를 공용화한 것이다.)

★식별 규칙 — 파일명 문자열이 아니라 **문서 구조**로 고른다.
  · 정본A = 표준형(매트릭스 보유) `*-INPUT.pdf`
  · 정본B = overview형(매트릭스 없음) `*INPUT.pdf` 중 A가 아닌 것
  · 정본C = 계약 5건인 날짜형 보장분석
  · 정본D = 계약 6건인 날짜형 보장분석
  파일이 없으면(CI·타 개발기) `None`을 돌려 호출측이 skip 하게 한다.

★기대값은 바꾸지 않는다 — 같은 파일을 같은 순서로 고르므로 테스트 단언은 종전 그대로다.
"""
from __future__ import annotations

import glob
import os
from pathlib import Path

#: 실 문서 폴더(gitignore) — 레포에 파일을 두지 않는다.
REAL_DIR = Path(__file__).resolve().parents[2] / "보장분석" / "비교분석표"

#: 익명 라벨 — 문서·handoff·테스트가 같은 체계를 쓴다(정본A~D).
LABELS = ("정본A", "정본B", "정본C", "정본D")


def _contracts_of(path: Path) -> int | None:
    from coverage.parser import KBFormatError, parse_document

    try:
        raw = parse_document(path.read_bytes())
    except (KBFormatError, Exception):  # noqa: BLE001 - 형식 불일치·손상 전부 후보 제외
        return None
    return len(raw.get("contracts") or [])


def real_doc(label: str) -> Path | None:
    """익명 라벨 → 실 문서 경로. 폴더·파일이 없으면 None(호출측 skip)."""
    if not REAL_DIR.is_dir():
        return None
    if label in ("정본A", "정본B"):
        standard = sorted(REAL_DIR.glob("*-INPUT.pdf"))
        overview = [p for p in sorted(REAL_DIR.glob("*INPUT.pdf")) if not p.name.endswith("-INPUT.pdf")]
        picked = standard if label == "정본A" else overview
        return picked[0] if picked else None
    want = {"정본C": 5, "정본D": 6}.get(label)
    if want is None:
        return None
    for path in sorted(REAL_DIR.glob("*_*.pdf")):
        if "제안서" in path.name or "INPUT" in path.name:
            continue
        if _contracts_of(path) == want:
            return path
    return None


def real_docs() -> dict[str, Path]:
    """존재하는 정본만 담은 {라벨: 경로}."""
    found = {}
    for label in LABELS:
        path = real_doc(label)
        if path is not None and path.exists():
            found[label] = path
    return found


def real_proposals(label: str = "정본C") -> list[Path]:
    """해당 정본에 딸린 가입제안서들(파일명 접두를 실측 문서에서 유도 — 실명 미기재)."""
    doc = real_doc(label)
    if doc is None:
        return []
    stem = doc.name.split("_")[1] if "_" in doc.name else ""
    prefix = stem.replace("님", "") if stem else ""
    if not prefix:
        return []
    return [Path(p) for p in sorted(glob.glob(os.path.join(str(REAL_DIR), f"{prefix}_*가입제안서*.pdf")))]
