# -*- coding: utf-8 -*-
"""BOHUMFIT-284 — 오픈 게이트 마감(283 F-6·F-3·F-7).

★이 파일이 고정하는 계약
  T1 ①283이 지목한 4종에 limiter가 붙어 있다 ②한도는 **기존 유사 엔드포인트와 같은 값**이다
     ③초과 시 429 + 271 사전이 아는 문구다 ④정상 사용 패턴이 한도에 걸리지 않는다
  T2 ⑤`registry_hints`가 **응답에서** 사라진다 ⑥**서버 내부 반환값에는 남는다**
  T3 ⑦쪽수·압축 해제 크기 상한이 걸린다 ⑧**정상 PDF는 통과한다** ⑨열기 실패는 fail-open이다
"""
from __future__ import annotations

import io
import zlib

import pytest

import main
from pdf_guard import (
    EXPAND_LIMIT_MESSAGE,
    MAX_PDF_CONTENT_BYTES,
    MAX_PDF_IMAGE_BYTES,
    MAX_PDF_PAGES,
    PAGE_LIMIT_MESSAGE,
    PdfGuardError,
    check_pdf_limits,
)


# ── T1: rate limit 4종 ──────────────────────────────────────────────────────
#   283 F-6이 지목한 목록 그대로. 값은 기존 유사 엔드포인트와 같아야 한다(새 정책 금지).
F6_ENDPOINTS = {
    "/billing/webhook": "60/minute",
    "/billing/status": "60/minute",
    "/admin/tier/list": "20/minute",
    "/admin/tier/set": "20/minute",
}


def _endpoint_source(path: str) -> str:
    """`main.py`에서 해당 라우트의 데코레이터 블록을 읽는다.

    ★런타임 API 대신 소스를 보는 이유: slowapi는 버전마다 한도를 보관하는 위치가 달라
      (`_route_limits` / 함수 속성 / 클로저) 런타임 조회가 조용히 빈 값을 돌려줄 수 있다.
      빈 값을 "한도 없음"으로 오판하면 **이 테스트가 아무것도 지키지 못한다**.
    """
    import pathlib

    text = pathlib.Path(main.__file__).read_text(encoding="utf-8")
    method = "post" if path in ("/billing/webhook", "/admin/tier/set") else "get"
    marker = f'@app.{method}("{path}")'
    start = text.index(marker)
    return text[start : text.index("async def", start)]


@pytest.mark.parametrize("path", sorted(F6_ENDPOINTS))
def test_f6_endpoints_now_have_a_rate_limit(path):
    """★283 F-6: 이 4종만 limiter가 없었다. 이제 전부 있다."""
    assert "@limiter.limit(" in _endpoint_source(path), f"{path}에 limiter가 없다"


@pytest.mark.parametrize("path", sorted(F6_ENDPOINTS))
def test_f6_endpoints_accept_request_argument(path):
    """★slowapi는 시그니처에 `request`가 없으면 동작하지 않는다 — 붙였는데 무력한 상태 방지."""
    import inspect

    endpoint = next(r for r in main.app.routes if getattr(r, "path", None) == path).endpoint
    assert "request" in inspect.signature(endpoint).parameters


@pytest.mark.parametrize("path,expected", sorted(F6_ENDPOINTS.items()))
def test_f6_limits_match_existing_tiers(path, expected):
    """★한도는 새로 만들지 않고 기존 계층을 그대로 쓴다(조회 60 / 관리·쓰기 20)."""
    assert f'@limiter.limit("{expected}")' in _endpoint_source(path)


def test_existing_limits_are_untouched():
    """★기존 적용분은 건드리지 않는다(추가만) — 대표 4개를 고정한다."""
    import pathlib

    text = pathlib.Path(main.__file__).read_text(encoding="utf-8")
    assert '@limiter.limit("5/minute,30/hour")' in text      # /api/analyze
    assert '@limiter.limit("120/minute")' in text            # 진행 폴링(268b)
    assert '@limiter.limit("10/minute")' in text             # 결제 발급
    assert 'default_limits=["60/minute"]' in text            # Limiter 생성 인자 무변경


def test_rate_limit_message_is_known_to_the_271_dictionary():
    """★429 문구가 프런트 사전과 정합한다 — `errorMessages.ts` 규칙 조각과 일치해야 한다."""
    import pathlib

    backend_text = pathlib.Path(main.__file__).read_text(encoding="utf-8")
    assert "요청이 너무 잦습니다" in backend_text
    front = (
        pathlib.Path(main.__file__).resolve().parents[1] / "src" / "lib" / "errorMessages.ts"
    ).read_text(encoding="utf-8")
    assert '"요청이 너무 잦"' in front, "429가 사전에 없으면 화면에는 폴백만 뜬다"


# ── T1: 실제 요청으로 429 확인 ──────────────────────────────────────────────
#   ★소스 grep만으로는 "붙였는데 동작하지 않는" 상태를 못 잡는다(slowapi는 `request` 인자가
#     없으면 조용히 예외를 내고, 데코레이터 순서가 틀리면 아예 걸리지 않는다).
@pytest.fixture
def limited_client():
    from fastapi.testclient import TestClient

    previous = main.limiter.enabled
    main.limiter.enabled = True
    main.limiter.reset()
    main.app.dependency_overrides[main.verify_jwt] = lambda: "u-284"
    try:
        yield TestClient(main.app)
    finally:
        main.app.dependency_overrides.pop(main.verify_jwt, None)
        main.limiter.reset()  # ★다른 테스트의 한도를 잠식하지 않는다
        main.limiter.enabled = previous


def _call(client, path: str):
    if path in ("/billing/webhook", "/admin/tier/set"):
        return client.post(path, json={"email": "a@b.c", "tier": "internal"})
    return client.get(path)


@pytest.mark.parametrize("path,limit", sorted((p, int(v.split("/")[0])) for p, v in F6_ENDPOINTS.items()))
def test_f6_endpoint_returns_429_after_limit(limited_client, path, limit):
    """★한도 직후 요청이 429가 되고, 문구는 271 사전이 아는 그것이다."""
    main.limiter.reset()
    for _ in range(limit):
        assert _call(limited_client, path).status_code != 429, f"{path}: 한도 이내인데 막혔다"

    blocked = _call(limited_client, path)
    assert blocked.status_code == 429
    assert blocked.json()["detail"] == "요청이 너무 잦습니다. 잠시 후 다시 시도해 주세요."


def test_normal_usage_pattern_is_not_throttled(limited_client):
    """★정상 사용 패턴은 걸리지 않는다 — `/billing/status`는 화면 진입마다 1회 부른다
    (UsageBadge·Dashboard·Subscription). 20회면 현실적인 상한을 크게 넘는다."""
    main.limiter.reset()
    codes = [limited_client.get("/billing/status").status_code for _ in range(20)]
    assert 429 not in codes


# ── T2: registry_hints 응답 제거 ────────────────────────────────────────────
BARE_ALPHA = """
(무) 메리츠 The좋은 알파Plus종합보장보험2607(2.0)
계약사항 : 20년납 20년만기 | 월납
"""


def test_registry_hints_are_stripped_from_the_response():
    """★283 F-3: 소비처 0인 키가 응답으로 나가지 않는다."""
    from coverage.proposal_parser import parse_proposal_texts

    response = parse_proposal_texts([("bare.pdf", BARE_ALPHA)])
    for proposal in response["proposals"]:
        assert "registry_hints" not in proposal["metadata"]


def test_internal_parser_still_exposes_hints():
    """★데이터 자체는 유지 — 서버 내부(276b 수기 확인)는 계속 접근한다."""
    from coverage.proposal_parser import parse_proposal_text

    result = parse_proposal_text(BARE_ALPHA, "bare.pdf")
    assert result["metadata"]["registry_hints"], "내부 반환값까지 지우면 276b 근거가 사라진다"


def test_sibling_metadata_keys_survive():
    """★함께 지우지 않는다 — `bundle_subbenefits`(276b)·`unresolved_coverages`(276a 근거)."""
    from coverage.proposal_parser import parse_proposal_texts

    response = parse_proposal_texts([("bare.pdf", BARE_ALPHA)])
    metadata = response["proposals"][0]["metadata"]
    assert "unresolved_coverages" in metadata
    assert "bundle_subbenefits" in metadata
    assert metadata["unresolved_coverages"], "276a의 '지어내지 않고 알린다' 근거가 사라지면 안 된다"


# ── T3: 업로드 상한 ─────────────────────────────────────────────────────────
def _make_pdf(pages: int, content: bytes = b"BT ET", compress: bool = False) -> bytes:
    """상한 검사용 최소 PDF. `compress=True`면 콘텐츠 스트림을 Flate로 압축한다."""
    objects: list[bytes] = []
    kids = " ".join(f"{3 + i * 2} 0 R" for i in range(pages))
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(f"<< /Type /Pages /Count {pages} /Kids [{kids}] >>".encode())
    for i in range(pages):
        stream = zlib.compress(content) if compress else content
        filt = b" /Filter /FlateDecode" if compress else b""
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Contents {4 + i * 2} 0 R >>".encode()
        )
        objects.append(
            b"<< /Length " + str(len(stream)).encode() + filt + b" >>\nstream\n" + stream + b"\nendstream"
        )

    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for index, body in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(f"{index} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n".encode())
    out.write(b"0000000000 65535 f \n")
    for offset in offsets:
        out.write(f"{offset:010d} 00000 n \n".encode())
    out.write(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    )
    return out.getvalue()


def test_normal_pdf_passes():
    """★정상 사용을 막지 않는다 — 소형 문서는 그냥 통과한다."""
    check_pdf_limits(_make_pdf(3))


def test_page_limit_blocks_and_explains():
    """쪽수 초과 → 상한 문구(행동 지침형)."""
    pdf = _make_pdf(MAX_PDF_PAGES + 1)
    with pytest.raises(PdfGuardError) as excinfo:
        check_pdf_limits(pdf)
    assert str(excinfo.value) == PAGE_LIMIT_MESSAGE


def test_page_limit_boundary_is_inclusive():
    """★경계는 포함 — 정확히 상한이면 통과한다(`>` 비교)."""
    check_pdf_limits(_make_pdf(MAX_PDF_PAGES))


def test_decompressed_content_limit_blocks(monkeypatch):
    """★압축폭탄: 파일은 작지만 펼치면 거대한 경우 — 크기 상한만으로는 못 막던 것이다.

    ★상한을 낮춰 재현한다. 실제 200MB를 만들면 **테스트가 스스로 폭탄이 된다**(메모리·시간).
      비교 로직은 동일하고, 실제 상한값은 `test_limits_have_headroom_over_measured_real_usage`가 지킨다.
    """
    monkeypatch.setattr("pdf_guard.MAX_PDF_CONTENT_BYTES", 4096)
    payload = b"\x00" * 65536
    pdf = _make_pdf(1, content=payload, compress=True)
    assert len(pdf) < 4096, "압축 후에는 4KB도 안 된다 — 기존 크기 상한을 그냥 통과한다"
    with pytest.raises(PdfGuardError) as excinfo:
        check_pdf_limits(pdf)
    assert str(excinfo.value) == EXPAND_LIMIT_MESSAGE


def test_guard_is_fail_open_when_pdf_cannot_be_opened():
    """★열기 실패는 통과 — 기존 파서가 '비밀번호 해제 실패'를 정확히 안내한다."""
    check_pdf_limits(b"not a pdf at all")
    check_pdf_limits(b"%PDF-1.4\n<<broken>>")


def test_guard_error_messages_carry_no_pii():
    """★277 기조 — 문구에 파일명·환자명이 섞이지 않는다(상한 안내만 한다)."""
    for message in (PAGE_LIMIT_MESSAGE, EXPAND_LIMIT_MESSAGE):
        assert ".pdf" not in message
        assert "서류" not in message
        assert "발급 기간을 나눠" in message, "원인만 말하고 끝내지 않는다(271 원칙)"


def test_limits_have_headroom_over_measured_real_usage():
    """★상한 근거 고정(284 Step 1 실측) — 값이 조용히 조여지면 정상 사용이 막힌다."""
    assert MAX_PDF_PAGES >= 318 * 3, "실사용 확인 최대 318쪽(BUG-006)의 3배 이상"
    assert MAX_PDF_CONTENT_BYTES >= 2_665_001 * 50, "실측 최대 콘텐츠의 50배 이상"
    assert MAX_PDF_IMAGE_BYTES >= 174_628_166 * 20, "실측 최대 이미지의 20배 이상"


def test_guard_is_wired_into_every_upload_endpoint():
    """★네 곳 전부에 걸려 있다 — 한 곳만 빠져도 그 경로가 무방비다."""
    import pathlib

    text = pathlib.Path(main.__file__).read_text(encoding="utf-8")
    assert text.count("_guard_pdf") >= 5  # 정의 1 + 호출 4
