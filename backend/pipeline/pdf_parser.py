"""PDF 파싱 — analyzer.py 에서 이동."""
from __future__ import annotations

import functools
import gc
import io
import logging
import re

import pdfplumber

logger = logging.getLogger(__name__)

from .helpers import (
    _FTYPE_KW,
    AnalysisError,
    _is_surgery_match,
    get_val,
    normalize_code,
    parse_date,
    row_is_junk,
    nhis_surg_keywords,
    test_keywords,
)


@functools.lru_cache(maxsize=512)
def _strong_header_ftype(headers) -> str:
    """표 헤더가 _FTYPE_KW 키워드와 '명확히' 일치하는 경우의 타입.

    헤더 OCR이 정상 추출된 강(强)신호에 해당한다. 키워드 일치가 없으면 ""
    (= 신호 약함)을 돌려준다. BOHUMFIT-002: 분류 우선순위 판정에 사용.
    """
    h_joined = " ".join(str(h) for h in headers)
    h_norm = h_joined.replace(" ", "").replace("\n", "")
    for ftype in ("pharma", "detail", "basic"):
        if any(k in h_joined or k in h_norm for k in _FTYPE_KW[ftype]):
            return ftype
    return ""


@functools.lru_cache(maxsize=512)
def detect_file_type(headers):
    # 1순위: _FTYPE_KW 키워드 명시 일치 (헤더 OCR 성공 — 강신호)
    strong = _strong_header_ftype(headers)
    if strong:
        return strong

    # 2순위: 컬럼명 구조 휴리스틱 추정 (헤더 신호 약함 — 약신호)
    n_cols = len(headers)
    has_date_col = any(re.search(r"일$|날짜|일자|개시", str(h)) for h in headers)
    has_code_like = any(re.search(r"코드|기호|분류", str(h)) for h in headers)
    has_drug_like = any(re.search(r"약|처방|조제|투약", str(h)) for h in headers)
    has_act_like = any(re.search(r"행위|내역|명칭|처치|급여", str(h)) for h in headers)

    if has_drug_like:
        return "pharma"
    if has_act_like and n_cols >= 5:
        return "detail"
    if has_date_col and has_code_like:
        return "basic"

    return "unknown"


def _detect_ftype_by_page_text(text: str) -> str:
    """페이지 본문 텍스트의 심평원 섹션 표제어로 PDF 표 타입을 추정한다.

    표제어가 줄바꿈·공백으로 끊겨도 인식되도록 공백을 제거한 뒤 대조한다
    (BOHUMFIT-002: 헤더 OCR 누락 시 신뢰할 본문 신호의 견고성 보강).
    """
    if not text:
        return ""
    norm = re.sub(r"\s+", "", text)
    if "기본진료정보" in norm:
        return "basic"
    if "세부진료정보" in norm:
        return "detail"
    if "처방조제" in norm:
        return "pharma"
    # BOHUMFIT-094: 섹션 표제어(처방조제정보)까지 OCR 누락된 처방 페이지 보강.
    #   '투약일수'는 심평원 처방조제 표 전용 컬럼어로 기본·세부 진료 섹션엔 없다.
    #   표제어가 사라져도 본문에 남으면 처방 신호로 신뢰한다(최후순위 — 표제어가 있으면 위에서 먼저 결정).
    #   공단 NHIS는 parse_single_pdf의 is_nhis 분기로 별도 처리되어 이 함수 영향권 밖.
    if "투약일수" in norm:
        return "pharma"
    # BOHUMFIT-139: 섹션 표제어·전용 컬럼어까지 모두 OCR 누락된 경우, 본문 신호 다수결로 타입 추정(최후 fallback).
    #   정상 표제어/헤더 판별은 위에서 먼저 결정되므로 이 분기는 헤더·표제어가 모두 사라진 페이지에만 도달한다.
    #   norm은 공백 제거본 — '입원/외래' → '입원외래' 처럼 컬럼어가 붙어도 매칭된다.
    _sig = {
        "pharma": sum(norm.count(k) for k in ("약품명", "성분명", "1일투여횟수", "1회투약량", "조제일자")),
        "basic": sum(norm.count(k) for k in ("주상병", "상병코드", "입원외래", "진료일수", "진료개시일")),
        "detail": sum(norm.count(k) for k in ("진료내역", "코드명", "초진", "재진", "처치및수술")),
    }
    _best = max(_sig.values())
    if _best > 0:
        # 동점 우선순위: pharma > basic > detail (처방 전용어가 변별력 가장 높음)
        for _t in ("pharma", "basic", "detail"):
            if _sig[_t] == _best:
                return _t
    return ""


def _resolve_ftype(headers, page_ftype: str) -> str:
    """표 헤더 신호와 페이지 본문 신호를 종합해 표 타입을 최종 결정한다.

    우선순위 (BOHUMFIT-002 — 헤더 OCR 누락 시 처방 PDF가 진료내역으로
    오분류되던 문제 보정):
      1) 헤더가 _FTYPE_KW 키워드와 명확히 일치(강신호) → 기본적으로
         헤더를 신뢰한다.
         예외: 페이지 본문이 처방조제(pharma)이고 헤더 강신호가 detail/basic
         인 경우에는 처방 PDF가 진료내역으로 굳는 방향의 오분류를 막기 위해
         본문 신호를 우선한다. 반대 방향(detail/basic 본문이 pharma 헤더를
         이기는 일반화)은 적용하지 않는다.
      2) 헤더 신호가 약하면(구조 휴리스틱 추정 또는 unknown) 페이지 본문
         섹션 신호(page_ftype)를 우선한다. 헤더 OCR이 누락·왜곡됐을 때
         처방표가 detail로 잘못 굳는 것을 막는다.
      3) 본문 신호도 없으면 약한 헤더 추정값(없으면 "unknown")을 사용한다.

    변경 전: 헤더가 unknown일 때만 본문 신호로 fallback → 헤더가 약신호로
    오분류돼도 본문 신호가 무시됐다. 변경 후: 약신호 헤더는 본문 신호에 양보.
    """
    strong_ftype = _strong_header_ftype(headers)
    if strong_ftype:
        if page_ftype == "pharma" and strong_ftype in {"detail", "basic"}:
            return "pharma"
        return strong_ftype
    if page_ftype:
        return page_ftype
    return detect_file_type(headers)


def _pw_candidates(bdate_str: str | None) -> list[str]:
    """BOHUMFIT-053: 생년월일 비번 후보 목록.

    발급기간별로 PDF 비번 자리수가 다르다(0~5년=생년월일 8자리, 5~10년=6자리 YYMMDD).
    사용자는 8자리만 입력해도 되도록, 8자리 입력 시 뒤 6자리(YYMMDD)를 자동 재시도한다.
    6자리 직접 입력·빈 비번(비번 불요 PDF)·하이픈 포함 입력 모두 안전하게 동작한다.
    순서: [빈값, 입력원본, 숫자만, 8→6(YYMMDD) | 6→8(prefix)].
    """
    bd = (bdate_str or "").strip()
    bd_digits = re.sub(r"\D", "", bd)
    candidates = [""]                       # 비번 불요 PDF
    if bd:
        candidates.append(bd)               # 입력값 그대로(8자리 등)
    if bd_digits and bd_digits != bd:
        candidates.append(bd_digits)        # 하이픈 등 제거한 숫자만
    if len(bd_digits) == 8:
        candidates.append(bd_digits[2:])    # 8자리 → 뒤 6자리(YYMMDD) 자동 재시도
    elif len(bd_digits) == 6:
        yy = int(bd_digits[:2])
        prefix = "20" if yy <= 24 else "19"
        candidates.append(prefix + bd_digits)  # 6자리 → 8자리
    return list(dict.fromkeys(candidates))


def _open_pdf(data, bdate_str):
    candidates = _pw_candidates(bdate_str)
    for pw in candidates:
        try:
            pdf = pdfplumber.open(io.BytesIO(data), password=pw)
            # BOHUMFIT-053: 어느 자리수 비번으로 풀렸는지만 로깅(PII 주의 — 값 미기록, 자리수만).
            logger.info("BOHUMFIT-053 PDF 해제: pw_len=%d", len(pw))
            return pdf
        except Exception:
            continue
    raise ValueError("PDF 비밀번호 해제 실패 — 생년월일을 확인해 주세요.")


# BOHUMFIT-033: 공단 요양급여내역 발급기간(조회기간) 추출용.
_NHIS_PERIOD_RE = re.compile(
    r'(?:발급|조회|진료|작성)\s*기간[^\d]{0,6}'
    r'(\d{4}[.\-]\d{2}[.\-]\d{2})\s*[~\-]\s*(\d{4}[.\-]\d{2}[.\-]\d{2})'
)
_NHIS_PERIOD_FALLBACK_RE = re.compile(
    r'(\d{4}\.\d{2}\.\d{2})\s*~\s*(\d{4}\.\d{2}\.\d{2})'
)
# 금액 토큰: 4자리 이상(콤마 허용). 일수·순번 같은 소수 자릿수는 제외.
_NHIS_AMOUNT_RE = re.compile(r'\d[\d,]{3,}')


def _extract_nhis_issue_period(text: str) -> str:
    """발급/조회기간 'YYYY.MM.DD ~ YYYY.MM.DD' 를 추출(없으면 '')."""
    m = _NHIS_PERIOD_RE.search(text)
    if not m:
        m = _NHIS_PERIOD_FALLBACK_RE.search(text)
    if not m:
        return ""
    norm = lambda d: d.replace("-", ".")
    return f"{norm(m.group(1))} ~ {norm(m.group(2))}"


def _extract_nhis_total_cost(line: str) -> int:
    """공단 행에서 총진료비(=진료비총액, 공단부담+본인부담의 합)를 추정.

    같은 줄의 금액 토큰(4자리+) 중 최댓값을 진료비총액으로 본다(공단+본인 = 총액).
    """
    vals = []
    for tok in _NHIS_AMOUNT_RE.findall(line):
        try:
            vals.append(int(tok.replace(",", "")))
        except ValueError:
            continue
    return max(vals) if vals else 0


def parse_nhis_text(text, fname):
    records = []
    issue_period = _extract_nhis_issue_period(text)
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    # BOHUMFIT-056: 1줄에서 '입내원일수'(group2)도 캡처 — 공단 입원 '입원일수'의 정답 컬럼.
    #   (기존엔 비캡처 \d+ 로 버려, 2줄 '요양(투약)일수'를 입원일수로 오인했음.)
    date_re  = re.compile(r'^(\d{4}\.\d{2}\.\d{2})\s+(\d+)\s+(.+?)\s+\d{2,4}-\d{3,4}-\d{4}')
    visit_re = re.compile(r'^(외래|입원|약국)\s+(\d+)\s*(.*)')
    seq_re   = re.compile(r'^\d+$')
    cur_date, cur_hospital = None, None
    cur_visit_days, cur_gongdan = "", 0   # BOHUMFIT-056: 1줄 입내원일수·공단부담금
    i = 0
    while i < len(lines):
        line = lines[i]
        m_d = date_re.match(line)
        if m_d:
            cur_date       = m_d.group(1)
            cur_visit_days = m_d.group(2)                    # BOHUMFIT-056: 입내원일수(1줄)
            cur_hospital   = m_d.group(3).strip()
            cur_gongdan    = _extract_nhis_total_cost(line)  # BOHUMFIT-056: 공단부담금(1줄)
            i += 1
            continue
        if seq_re.match(line) and cur_date:
            i += 1
            if i < len(lines):
                visit_line = lines[i]
                m_v = visit_re.match(visit_line)
                if m_v:
                    in_out_v = m_v.group(1)
                    if in_out_v == "약국":
                        i += 1
                        continue
                    days_v = m_v.group(2)
                    rest   = m_v.group(3).strip()
                    parts  = rest.split()
                    code_v = ""
                    name_v = ""
                    for pi, p in enumerate(parts):
                        if re.match(r'^[A-Z]\d', p):
                            code_v = p
                            name_v = " ".join(parts[:pi])
                            break
                    if not name_v and not code_v:
                        name_v = rest
                    # BOHUMFIT-056: 총진료비 = 공단부담금(1줄) + 본인부담금(2줄) 합산.
                    #   (기존엔 2줄 본인부담금만 읽어 수술의심 금액 기준이 과소했음 → 입원 고액 건 누락.)
                    bonin_cost = _extract_nhis_total_cost(visit_line)
                    total_cost = (cur_gongdan or 0) + bonin_cost
                    if name_v or code_v:
                        records.append({
                            "진료개시일": cur_date,
                            "요양기관명": cur_hospital or "",
                            "입내원구분": in_out_v,
                            "내원일수":   cur_visit_days or "",   # BOHUMFIT-056: 입내원일수(1줄)=입원/내원 일수
                            "투약일수":   days_v,                 # BOHUMFIT-056: 요양(투약)일수(2줄) 별도 유지
                            "상병명":     name_v,
                            "상병코드":   code_v,
                            "총진료비":   str(total_cost),  # BOHUMFIT-056: 공단+본인 합(수술의심 기준)
                            "_issue_period": issue_period,  # BOHUMFIT-033: 파일별 발급기간
                            "_ftype":     "nhis",
                            "_fname":     fname,
                        })
                i += 1
            continue
        i += 1
    return records


def _empty_result_message(fname: str, n_pages: int, first_text: str) -> str:
    """PDF가 정상적으로 열렸으나 진료 레코드가 0건일 때 원인별 안내.

    비밀번호 문제로 오인되지 않도록 '비밀번호'를 언급하지 않는다.
    """
    if n_pages == 0:
        return f"⚠️ {fname}: 페이지가 없는 빈 PDF입니다."
    if not (first_text or "").strip():
        return (
            f"🖼️ {fname}: 이 파일은 이미지로 저장된 PDF라 분석할 수 없습니다. "
            f"같은 요양급여내역이라도 텍스트가 포함된 원본 PDF만 분석됩니다.\n"
            f"정부24 또는 The건강보험(건강보험공단) 앱/웹에서 '요양급여내역'을 조회한 뒤 "
            f"[PDF 저장/다운로드]로 받은 원본 파일을 업로드해 주세요.\n"
            f"인쇄 후 PDF 저장·화면 캡처·사진·스캔본은 이미지형이라 인식되지 않습니다."
        )
    return (
        f"⚠️ {fname}: PDF는 열렸으나 인식 가능한 진료 표를 찾지 못했습니다. "
        f"심평원 '진료받은내역' 또는 '건강보험 요양급여내역' PDF가 맞는지 확인해 주세요."
    )


_PATIENT_NAME_RE = re.compile(r"성\s*명\s+([가-힣]{2,5})\s+주민등록번호")


def _extract_patient_name(text: str) -> str:
    """BOHUMFIT-065: 공단/심평원 PDF 1페이지의 '성명 ○○○ 주민등록번호 …'에서 성명만 추출.
    출력용 파일명에 쓰기 위함 — 주민등록번호 등 다른 PII는 절대 추출하지 않는다. 없으면 ''.
    """
    m = _PATIENT_NAME_RE.search(text or "")
    return m.group(1).strip() if m else ""


def parse_single_pdf(uploaded_file, birthdate_pw) -> dict:
    """PDF 1개 파싱. pdfplumber 동기 I/O."""
    fname = getattr(uploaded_file, "name", None) or getattr(uploaded_file, "filename", None) or "unknown.pdf"
    file_recs: list = []
    parse_errors_local: list = []
    patient_name = ""
    pdf_data = uploaded_file.read()
    try:
        with _open_pdf(pdf_data, birthdate_pw or "") as pdf:
            first_text = pdf.pages[0].extract_text() or "" if pdf.pages else ""
            patient_name = _extract_patient_name(first_text)  # BOHUMFIT-065: 파일명용 성명
            is_nhis = "건강보험 요양급여내역" in first_text

            if is_nhis:
                # BOHUMFIT-056: 페이지별 파싱은 공단 표의 2줄 1세트(날짜줄+순번+내역줄)가 페이지
                #   경계에서 끊겨 입원 행이 누락됐다(예: M512/K605 입원). 전체 페이지 텍스트를 모아
                #   한 번에 파싱해 경계를 보존한다(텍스트만 누적 — 페이지 캐시는 즉시 flush, 메모리 안전).
                nhis_texts = []
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    nhis_texts.append(page_text)
                    del page_text
                    page.flush_cache()  # OOM 핫픽스: 페이지 레이아웃 캐시 즉시 해제
                file_recs.extend(parse_nhis_text("\n".join(nhis_texts), fname))
                del nhis_texts
            else:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    page_ftype = _detect_ftype_by_page_text(page_text)
                    tables = page.extract_tables()
                    for table in tables:
                        if not table or len(table) < 2:
                            continue
                        raw_headers = table[0]
                        headers = [
                            str(h).replace("\n", "").replace(" ", "") if h else f"col_{i}"
                            for i, h in enumerate(raw_headers)
                        ]
                        ftype = _resolve_ftype(tuple(headers), page_ftype)
                        for row in table[1:]:
                            if not any(row):
                                continue
                            if "순번" in str(row[0]):
                                continue
                            rec = {h: str(v).replace("\n", " ").strip() if v else "" for h, v in zip(headers, row)}
                            rec["_ftype"] = ftype
                            rec["_fname"] = fname
                            # BOHUMFIT-126: 세부진료 진료내역의 초진/재진을 is_first_visit로 추출
                            #   (초진=새 상해 에피소드, 재진=직전 에피소드 연속). S코드 그룹 분리에 사용.
                            if ftype == "detail":
                                _rowtxt = " ".join(str(v) for v in rec.values())
                                rec["is_first_visit"] = (
                                    True if "초진" in _rowtxt
                                    else (False if "재진" in _rowtxt else None)
                                )
                            file_recs.append(rec)
                    del page_text
                    del tables
                    page.flush_cache()  # OOM 핫픽스: 페이지 레이아웃 캐시 즉시 해제

            if not file_recs:
                parse_errors_local.append(
                    _empty_result_message(fname, len(pdf.pages), first_text)
                )
    except ValueError as e:
        parse_errors_local.append(f"🔒 {fname}: {e}")
    except Exception as e:
        err_str = str(e)
        if "password" in err_str.lower() or "encrypted" in err_str.lower():
            parse_errors_local.append(f"🔒 {fname}: 비밀번호가 걸린 PDF입니다. 생년월일을 입력해 주세요.")
        elif "pdf" in err_str.lower() or "syntax" in err_str.lower():
            parse_errors_local.append(f"⚠️ {fname}: 손상되었거나 지원하지 않는 PDF 형식입니다.")
        else:
            parse_errors_local.append(f"⚠️ {fname}: 파일 읽기 실패 — {err_str[:80]}")
    finally:
        del pdf_data
        gc.collect()
    return {"filename": fname, "records": file_recs, "parse_errors": parse_errors_local,
            "patient_name": patient_name}
