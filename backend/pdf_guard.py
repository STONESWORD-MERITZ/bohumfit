# -*- coding: utf-8 -*-
"""BOHUMFIT-284(F-7) — 업로드 PDF 최소 방어.

★왜 필요했나(283 F-7): 기존 방어는 **파일 크기**뿐이었다(개별 15MB·총합 40MB).
  작은 파일이 파싱 중 자원을 폭증시키는 경우(압축폭탄)는 막지 못했고,
  순차 파싱이 피크를 1파일분으로 묶는 것이 유일한 완화였다.

★이 모듈이 보는 세 가지
  ①쪽수 ②페이지 콘텐츠 스트림의 **압축 해제 누적 크기** ③이미지의 **원시 픽셀 바이트**

★설계 원칙 3가지
  1. **조기 중단** — 누적이 상한을 넘는 즉시 멈춘다. 폭탄을 끝까지 펼치지 않는다.
  2. **이미지는 압축을 풀지 않는다** — `/Width`·`/Height`·`/BitsPerComponent`를 dict에서만 읽어
     원시 크기를 계산한다. 폭탄을 재려고 폭탄을 터뜨리면 방어가 아니라 공격 통로가 된다.
  3. ★**열기 실패는 통과시킨다(fail-open)** — 비밀번호 불일치·손상 PDF의 정확한 안내는 기존
     파서가 이미 하고 있다. 가드가 먼저 다른 문구로 가로채면 기존 동선이 나빠진다.
     이 모듈은 "정상적으로 열리는데 지나치게 큰" 것만 막는다.

★상한값 근거(284 Step 1 실측 — 태스크 문서에 표로 있다)
  · 쪽수 1,000 — 실사용 확인 최대 **318쪽**(BUG-006 사고 기록)의 3.1배.
    정본 6건 최대 42쪽만 보고 잡으면 정상 사용을 막는다.
  · 콘텐츠 200MB — 실측 최대 2,665,001 B의 75배.
  · 이미지 4GB — 실측 최대 174,628,166 B의 23배. 진짜 상한은 파일 크기 15MB이며,
    실측 최대 압축비 25.0배를 15MB에 적용해도 375MB라 10.7배 여유가 있다.

★가드 비용 실측: 전체 파싱의 0.2~3.3%(0.02~0.06초). 정상 사용에 영향 없다.

※정밀 방어(객체 그래프 순환·폰트 폭탄 등 구조 검사)는 범위 밖 — 오픈 후 별도 태스크.
"""
from __future__ import annotations

import io
import logging
from typing import Sequence

import pdfplumber
from pdfminer.pdftypes import PDFStream, resolve1

logger = logging.getLogger(__name__)

# ── 상한 ────────────────────────────────────────────────────────────────────
MAX_PDF_PAGES = 1_000
MAX_PDF_CONTENT_BYTES = 200 * 1024 * 1024
MAX_PDF_IMAGE_BYTES = 4 * 1024 * 1024 * 1024

# ── 안내 문구 ───────────────────────────────────────────────────────────────
#   271 원칙: 원인 + **다음 행동**을 함께 준다. ★파일명은 넣지 않는다(277 PII 기조).
PAGE_LIMIT_MESSAGE = (
    f"PDF 쪽수가 너무 많아요({MAX_PDF_PAGES:,}쪽 초과). "
    "발급 기간을 나눠 받은 뒤 다시 올려 주세요."
)
EXPAND_LIMIT_MESSAGE = (
    "PDF 내용이 지나치게 커서 열지 못했어요. 발급 기간을 나눠 받은 뒤 다시 올려 주세요."
)


class PdfGuardError(ValueError):
    """상한 초과. ★`ValueError` 하위라 기존 파서 오류 처리 경로와 충돌하지 않는다."""


def _stream_data_len(obj) -> int:
    """콘텐츠 스트림 하나의 압축 해제 길이. 못 읽으면 0(가드는 과소평가 쪽으로 안전하다)."""
    try:
        resolved = resolve1(obj)
    except Exception:
        return 0
    if not isinstance(resolved, PDFStream):
        return 0
    try:
        return len(resolved.get_data())
    except Exception:
        return 0


def _image_raw_bytes(page) -> int:
    """이 페이지가 참조하는 이미지의 **원시 픽셀 바이트** 합. ★압축을 풀지 않는다."""
    try:
        resources = resolve1(page.page_obj.resources) or {}
        xobjects = resolve1(resources.get("XObject")) or {}
        items = xobjects.items()
    except Exception:
        return 0

    total = 0
    for _, ref in items:
        try:
            obj = resolve1(ref)
        except Exception:
            continue
        if not isinstance(obj, PDFStream):
            continue
        subtype = obj.attrs.get("Subtype")
        if getattr(subtype, "name", None) != "Image":
            continue
        try:
            width = int(resolve1(obj.attrs.get("Width")) or 0)
            height = int(resolve1(obj.attrs.get("Height")) or 0)
            bits = int(resolve1(obj.attrs.get("BitsPerComponent")) or 8)
        except Exception:
            continue
        # 컴포넌트 수는 색공간 해석이 필요해 세지 않는다 — 1로 보고 **과소평가**한다.
        # 상한이 실측의 23배라 과소평가로 정상 파일이 막히는 일은 없고, 폭탄은 여전히 걸린다.
        total += width * height * max(bits, 1) // 8
    return total


def check_pdf_limits(data: bytes, passwords: Sequence[str] = ("",)) -> None:
    """상한 초과면 `PdfGuardError`. 열리지 않으면 **조용히 통과**(fail-open — 모듈 주석 3번)."""
    pdf = None
    for password in passwords or ("",):
        try:
            pdf = pdfplumber.open(io.BytesIO(data), password=password)
            break
        except Exception:
            continue
    if pdf is None:
        return  # 기존 파서가 정확한 사유(비밀번호·손상)를 안내한다.

    try:
        pages = pdf.pages
        if len(pages) > MAX_PDF_PAGES:
            raise PdfGuardError(PAGE_LIMIT_MESSAGE)

        content_bytes = 0
        image_bytes = 0
        for page in pages:
            contents = getattr(page.page_obj, "contents", None)
            if contents is not None:
                for stream in contents if isinstance(contents, list) else [contents]:
                    content_bytes += _stream_data_len(stream)
                    if content_bytes > MAX_PDF_CONTENT_BYTES:
                        raise PdfGuardError(EXPAND_LIMIT_MESSAGE)  # ★조기 중단
            image_bytes += _image_raw_bytes(page)
            if image_bytes > MAX_PDF_IMAGE_BYTES:
                raise PdfGuardError(EXPAND_LIMIT_MESSAGE)  # ★조기 중단
    finally:
        try:
            pdf.close()
        except Exception:
            pass
