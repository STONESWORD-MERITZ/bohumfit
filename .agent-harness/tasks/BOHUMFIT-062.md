# BOHUMFIT-062 051 잔여 미커밋 변경 정리 (report_disclosure.html 페이지 구분)

## Owner
- Cowork (잔여 변경 정체·완결성 확인) → Codex (Windows 전체 검증·실 PDF 6페이지 육안·커밋·푸시 — 잔여분 확정) → (Human 불요)

## 배경
- 여러 세션째 워킹트리 미커밋: `backend/templates/report_disclosure.html`·`backend/tests/test_report_pdf.py`. 059 STEP D 판정=마운트 노이즈 아닌 의미있는 변경(051 커밋 누락분, "전체 병력 요약 새 페이지"). 방치 시 유실 위험 → 단독 커밋으로 확정.
- ※ Cowork는 마운트 git 미실행 → `git diff` 대신 실파일(Read/Grep)로 워킹트리 현재 상태의 완결성 확인. 커밋은 Codex.

## STEP 0 진단 (잔여 변경 정체)
- **report_disclosure.html** "전체 병력 요약" 새 페이지 구분 변경이 **완결 상태로 존재**:
  - `<style>` L146~157: `.all-history { page-break-before: always; break-before: page; }`(새 페이지 시작)·`.all-history .sec-h2 { break-after: avoid; page-break-after: avoid; }`(헤더 고아 방지)·`.all-tbl tr { page-break-inside: avoid; break-inside: avoid; }`(행 분할 방지)·`.all-tbl thead { display: table-header-group; }`(페이지별 헤더 반복).
  - HTML L272~295: `{% if all_diseases %}<div class="q-block all-history"><h2 class="sec-h2">전체 병력 요약</h2><table class="all-tbl">…</table></div>{% endif %}` — 블록 정상 개폐(L272 if ~ L295 endif), `</html>`(L315)까지 완결.
  - **051 패턴과 일관**: 간편심사 `.product-sec.page-break { page-break-before: always; break-before: page; }`(L83)와 동일 방식. → **정상 완결 변경(중간/깨짐 아님)**.
- **test_report_pdf.py** 동반 회귀 `test_disclosure_all_history_summary_starts_new_page`(L176~180): 렌더 HTML에 `class="q-block all-history"`·`.all-history { page-break-before: always; break-before: page; }`·`.all-tbl thead { display: table-header-group; }` 존재 단언. `DISCLOSURE_PAYLOAD`에 `all_disease_summary`(질병 1건) 포함 → `render_disclosure_html`가 `all_diseases = payload["all_disease_summary"]`(report_pdf L421)로 매핑 → `{% if all_diseases %}` 분기 렌더 → 3개 단언 충족.

## STEP 1 변경 검증
- STEP0에서 **정상 완결**로 판단 → 완성 작업 불요. 그대로 보존, 검증만.

## STEP 2 검증
- **실파일 정합(Read/Grep)**: 위 3개 단언 문자열이 실 템플릿에 verbatim 존재(L148·L156·L273)·`{% if all_diseases %}…{% endif %}` 정상 개폐·payload 조건 충족 → 테스트는 구성상 통과.
- **권위 증거**: Codex의 **060 전체 pytest=353 passed**가 이 051-잔여 워킹트리 파일들이 트리에 있는 상태에서 수행됨(pytest는 git stage 무관 워킹트리 실행) → `test_disclosure_all_history_summary_starts_new_page`가 353 passed에 **이미 포함·통과**.
- ⚠ **sandbox 한계**: report_disclosure.html·report_pdf.py·test_report_pdf.py가 마운트에서 stale/절단(템플릿 /tmp 복사본은 `{% if %}` 미종료로 TemplateSyntaxError — 051에서도 잦던 손상). /tmp Jinja 실렌더·Chromium 6페이지 육안은 **Codex/Windows 권위**. 실파일 마커는 Read로 확인 완료.
- 코드 변경 **0**(051 잔여분은 이미 트리에 완결). 분석 로직 무변경(PDF 표현만).

## 자체 점검
- ☑ 잔여 변경 정체·완결성 파악(완결·051 패턴 일관) ☑ "전체 병력 요약" 새 페이지(page-break-before always·thead 반복·tr break-inside avoid) ☑ test_report_pdf.py 통과(Codex 060 353 passed에 포함) ☑ 분석 로직 무변경(표현만) ☑ 회귀 0(신규 변경 없음).

## Next
- **Codex(Windows)**: `python -m pytest -q tests/test_report_pdf.py -vv` + 전체 pytest(353 유지)·실 데이터 리포트 PDF 생성 → "전체 병력 요약" 섹션 새 페이지 시작 6페이지 육안 확인 → **이 051 잔여분(report_disclosure.html + test_report_pdf.py)을 단독 커밋·푸시로 확정**. 커밋: `BOHUMFIT-062: 고지 리포트 전체 병력 요약 섹션 새 페이지 구분(051 잔여분 확정)`.
