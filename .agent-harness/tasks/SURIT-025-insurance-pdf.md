# SURIT-025 — 실손 청구 리포트 PDF 출력 (브라우저 인쇄)

- Owner: Cowork (구현) → 검증·푸시 Codex
- 기준 문서: `.agent-harness/docs/BOHUMFIT_실비기능_설계_v3.md` (v3-1)
- 생성: 2026-06-06
- 전제: SURIT-023 실손 탭 완료(`InsuranceSection`).

## 범위 (잠금)
- `src/pages/Disclosure.tsx` — 실손 탭에 "PDF로 저장(인쇄)" + 인쇄 영역 + @media print CSS, §4-1 검증완료 문구 갱신
- `.agent-harness/tasks/SURIT-025-insurance-pdf.md`
- ※ `backend/insurance/calculator.py` 는 이미 `COPAY_RATE_VERIFIED` 로 일관 갱신됨(사용자/린터) — 수정 불필요.

## 방식 (클라이언트, 새 의존성 없음)
- `window.print()` + 인쇄 전용 CSS(@media print). jsPDF/html2canvas 등 새 라이브러리 금지(의존성 고정, 한글 깨짐 회피).
- 실손 탭에 "PDF로 저장(인쇄)" 버튼 → 클릭 시 실손 결과 영역(`#insurance-print-area`)만 인쇄.
- 완전 클라이언트 생성 — 서버 PDF·데이터 저장 없음(비저장 원칙).

## 인쇄 내용 (실손 탭 결과만)
- 입력 요약: 실손 세대, (3세대 비급여 옵션), 소득분위, 비급여 입력액, 조회 연도
- ① 실손 청구 가능성(추정 범위)
- ② 실손 자기부담금 상한제(세대별 합산범위, 4~5세대 비급여 제외 안내)
- ③ 건보 본인부담상한제(분위별, 기준연도 2026)
- 면책 문구 그대로: "추정"/"확정 금액 아님"/"보험사·공단 확인 필요"/"보험 모집·상품추천·가입권유 아님"
- 추가: "본 문서는 진료기록 기반 민감정보를 포함합니다 — 취급에 주의하세요."
- 생성 시점(날짜) 표시

## 인쇄 CSS
- @media print 로 `#insurance-print-area` 만 표시(헤더·네비·입력폼·버튼·다른 탭 숨김).
- 한 페이지에 깔끔히(여백·폰트). 화면 표시 불변(print 전용 분리).
- 버튼 라벨 "PDF로 저장(인쇄)"로 인쇄→PDF 흐름 명확화.

## 하지 말 것
- 새 npm 의존성 금지. 서버 PDF 생성/저장 금지(클라이언트만).
- 실손 계산 로직·알릴의무 로직 변경 금지(출력만 추가).
- 개인정보 저장 금지(인쇄 트리거만). 알릴의무(건강체/간편) 결과는 PDF 미포함(실손만).

## 검증
- `npx tsc -p tsconfig.app.json --noEmit` / `tsconfig.node.json` / `npm run build`
- 실손 탭 인쇄 미리보기로 면책 포함 깔끔히 나오는지 + 화면 표시 안 깨지는지 수동 확인.

## 완료 조건
- 인쇄 버튼 + 인쇄 영역 + @media print, 화면 불변. tsc/build 통과.
- handoff 표준 기록, Next=Codex 검증·푸시. locks 해제.

## Codex Windows 검증 결과 (2026-06-07)
- `npx tsc -p tsconfig.app.json --noEmit` 통과.
- `npx tsc -p tsconfig.node.json --noEmit` 통과.
- `npm run build` 통과(기존 Vite chunk-size warning only).
- `cd backend && python -m pytest -q` 통과: 160 passed, 7 skipped.
- Chrome headless print-media PDF render 검증 통과: 실제 `INS_PRINT_CSS` 추출 후 PDF 생성, ①②③/입력요약/생성일/민감정보 경고/면책 포함 및 헤더·네비·입력폼·건강체·간편심사 제외 확인.
