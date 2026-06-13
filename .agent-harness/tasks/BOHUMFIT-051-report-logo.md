# BOHUMFIT-051 리포트 PDF 헤더 브랜드 로고 적용 — 고지/실손

## Owner
Cowork(Claude) — 구현 1차. 검증·커밋·푸시는 Codex(Windows), 실제 리포트 출력 육안은 Human.

## 목표
backend가 생성하는 리포트 PDF(고지의무 점검·실손 예상 보험금)의 헤더/표지 영역에
BOHUMFIT 워드마크를 삽입한다. 산식·레이아웃·문구는 무수정, 로고만 추가.

## 에셋 배치
- `backend/assets/brand/bohumfit_logo.svg` — 컬러(잉크 #000000 + 포인트 #5955DE), 밝은 배경용.
- `backend/assets/brand/bohumfit_logo_white.svg` — 흰색(#FFFFFF) + 포인트 #5955DE, 어두운 배경용.
- src/assets/brand/ 정식 에셋을 복사. viewBox "190 407 1099 263" (≈4.18:1).
- 프런트 @/assets import 불가 → 백엔드에서 파일 읽어 base64 data-URI(`data:image/svg+xml;base64,...`)로 임베드.

## PDF 렌더 함정 (반드시 준수)
- SVG data-URI <img> 사용 시 `<?xml?>`/`<!DOCTYPE>` 선언 제거본 필요(외부 DTD 참조가 data-URI 로드 차단).
  → 복사본 확인 결과 정식 에셋과 동일하게 이미 제거돼 있음(xmldecl=0, doctype=0).
- Chromium PDF 생성 전 이미지 디코드 완료 보장(`img.decode()` 대기 + 짧은 지연). 디코드 전 캡처 시 로고 누락.
- 로고 크기: 헤더 높이에 맞춰 가로 워드마크 적정 폭, viewBox 비율 4.18:1 유지(잘림·왜곡 없게 width:auto).

## 적용 범위
- 고지(report_disclosure.html)·실손(report_insurance.html) 헤더 모두 일관 적용.
- 기존 톤(네이비 #1F3A5F + 골드 #C9A227) 유지. 헤더 배경 라이트 → **컬러 로고** 사용.
- 헤더의 텍스트 워드마크(`.wordmark` "BOHUMFIT.")를 `<img>` 로고로 교체.
- 푸터(`.biz-foot`)에 브랜드/연락처가 이미 있으므로 **로고 중복 표기 금지** — 푸터 무수정.

## 범위 밖 / 금지
- 금액·판정·산식 재계산 0. payload passthrough 유지.
- 레이아웃·문구·요약·면책 무수정(헤더 워드마크 1줄만 교체).
- white 로고는 현 노출처(라이트 헤더)에서 미사용 — 어두운 헤더 생기면 후속.

## ENV
- 신규 에셋/경로 추가, 마운트 git 금지, 검증 /tmp.

## 검증
- /tmp에서 고지/실손 샘플 PDF 1건씩 생성 → 로고 표시 확인(PNG 변환 육안 또는 PDF 내 이미지 임베드 마커).
- Codex(Windows): `cd backend && python -m pytest -q`(report_pdf 회귀) → 커밋·푸시.
- Human: 실제 리포트 출력 육안.

## 산출 기록
- handoff: 에셋 경로, 임베드 방식(base64 data-URI), 적용 리포트 종류, 톤 처리. Next: Codex → Human.
