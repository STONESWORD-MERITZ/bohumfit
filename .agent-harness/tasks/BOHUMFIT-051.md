# BOHUMFIT-051 알릴의무 고지 리포트 PDF 개선(KST·페이지구분·로고·소재지·브랜딩)
## Owner
- Cowork (구현+회귀) → Codex (Windows 검증·실 PDF 재현·git)

## 범위
- 표현(PDF 출력)만 변경. 분석 로직(filters/aggregator/result_builder) **무변경**.
- 파일: `backend/pipeline/report_pdf.py`, `backend/templates/report_disclosure.html`, `backend/tests/test_report_pdf_branding.py`(신규 7).

## A. 사용자 명시 4건
- **A-1 로고**: 경로 SVG(`_logo_data_uri`)의 보조 텍스트가 path로 깨져 렌더 → 디스클로저는 `logo_data_uri=""`로 override해 **깔끔한 CSS 텍스트 워드마크** 사용. `.wordmark` 브랜드 그린(#15663D)+`.wordmark-sub`("보험핏 · 알릴의무 분석", 그레이 보조라인).
- **A-2 KST**: `from zoneinfo import ZoneInfo`·`_now_kst()` 추가. `render_report_html`·`generate_report_pdf`의 기본 `generated_at = datetime.now()` → `_now_kst()`. 문서번호(`BF-{%Y%m%d-%H%M%S}`)는 generated_at 파생이라 KST 통일. 서버 TZ 무관.
- **A-3 페이지 구분**: `product_section` 매크로에 `break_before` 파라미터 추가, 간편심사 호출에 `true`. `.product-sec.page-break{page-break-before:always}`. 헤더 고아 방지 `.product-head/.q-head{break-after:avoid}`. 카드 분리 방지 `.item{page-break-inside:avoid}`(기존)·`.q-block` 무조건-avoid 제거(큰 블록 공백 방지).
- **A-4 소재지**: `_split_address()`로 첫 쉼표 기준 도로명/상세 2줄 분리 → 템플릿 `biz_address_lines[0]`+`<br>`+`.addr-detail`(상세 들여쓰기). `.biz-foot>div:first-child{max-width:74%}`로 자연 줄바꿈.

## B. 점검 기준일 누락
- **B-1**: report_pdf는 `reference_date`를 정상 렌더(`점검 기준일 <b>{{ reference_date }}</b>`). 비는 원인 = **프런트(`src/pages/Disclosure.tsx` L1045 보고 payload)가 reference_date를 안 보냄** → `payload.get("reference_date") or "-"` → "-". report 측은 이미 정상.
  - **수정 필요(범위 외)**: Disclosure.tsx 보고 payload에 `reference_date: refDate` 1줄 추가(refDate는 L1455에서 이미 보유). 의도적 공란 아님 → Codex/후속 소태스크로 프런트 1줄.

## C. 브랜딩 CSS
- **C-1 토큰**: `:root`에 `--brand-green #15663D · --brand-green-soft · --brand-green-line · --brand-ink #1F2937 · --brand-gray #6D747D` 정의. 종전 **미정의 `--accent`** → `#B45309`(주의 강조, `.v.warn`) 보정.
- **C-2 가독성**: 질문 배지(`.q-badge`) 그린(남색 섹션 헤더와 위계 구분). 고지권고 뱃지(`.badge-reco`) 그린 채움(시인성·신뢰). 핵심 수치 칩은 텍스트 라벨 유지(흑백 출력 식별). 과한 장식 없음.

## 검증
- /tmp pytest **299 passed**(신규 7 포함, 회귀 0; `test_main_launch_guardrails`만 sandbox app-import 제외 → Codex/Windows). 기준선 050 후 +7.
- HTML 렌더(Jinja) 마커 10/10 OK: 생성일시 KST(11:15)·문서번호 BF-20260617-111500·점검기준일 값·워드마크 보조라인·그린 토큰·간편 page-break·소재지 2줄(addr-detail)·고지권고 그린·--accent·Noto 폰트.
- ⚠ **Chromium PDF 변환·6페이지 육안은 sandbox 불가(libX 부재)** → Codex/Windows 재현 필수. report_pdf.py/템플릿 마운트 view 절단은 tail/본문 재구성으로 렌더 검증.
- 자체 점검: ☑KST ☑점검기준일(존재 시) ☑간편 새페이지 ☑카드 비분할 ☑로고 정리 ☑소재지 줄바꿈 ☑토큰 일관화 ☑한글 폰트 ☑분석 로직 무변경 ☑회귀0.

## Next
- **Codex(Windows)**: 전체 pytest·tsc/lint/test/build·**실 데이터 PDF 1회 생성→6페이지 육안**(KST/페이지구분/로고/소재지/점검기준일/브랜딩) → 커밋·푸시.
- **후속(프런트 1줄)**: Disclosure.tsx 보고 payload에 `reference_date` 추가(B-1 완결). 별도 소태스크 권장.

## Codex Follow-up
- B-1 완료: `src/pages/Disclosure.tsx` 보고서 생성 payload에 `reference_date`(화면 `refDate`) 전송.
- A-2 추가 완료: 간편심사 라벨 `유병자 3-5-5 기준` → `유병자 3-10-5 기준`으로 프런트 표시 경로·백엔드 리포트/상품 라벨 일괄 교정.
