# BOHUMFIT-157 — 고객 전달용 리포트 파일 다운로드 (공유 링크 금지)

Owner flow: Claude Chat -> Claude Cowork -> Codex
Current owner: Cowork

## 배경 (Human 확정)
감사 157 원안(공유 URL)은 폐기 — 링크 제공 금지.
대신 리포트를 파일(PDF)로 저장해 설계사가 직접 고객에게 전달하는 방식으로 확정.
기존 report_pdf 생성 경로가 존재하므로 신규 발명이 아니라 재사용·확장이 원칙.

## Step 0 — 진단 (구현 전 필수)
1. 기존 리포트 PDF 생성 경로 매핑: report_pdf 엔드포인트·호출 프런트 위치·인증 방식·생성물 구성
2. 히스토리 재열람(171b) result jsonb → PDF 입력 형식 호환성
3. PDF 파일명 규칙 확인 (현행)

## Step 1 — 히스토리에서 PDF 다운로드
- /history 목록·재열람 화면에 "PDF 저장" 버튼 (세컨더리)
- saved 트랙만 허용 — recent는 "저장 후 PDF로 내려받을 수 있어요" 안내
- 백엔드: 기존 report_pdf 경로 최소 확장 (분석 파이프라인 무접촉 — result 렌더만)
- 소유권 검사 필수 (본인 히스토리만)

## Step 2 — 고객 전달용 다듬기
- 파일명: BohumFit_고지의무리포트_{별칭}_{YYYYMMDD}.pdf (금지 문자 제거)
- PDF 표지/헤더 FIT v1.1 브랜드 확인, 구 브랜드 잔재 교체
- 하단 면책: "본 리포트는 참고용이며, 최종 고지의무 판단은 청약서 기준" 취지 확인/추가

## Step 3 — 분석 직후 흐름 정합
- 분석 결과 화면 PDF 버튼과 히스토리 PDF 버튼의 스타일·동작 통일 (핸들러 재사용)

## 수정 금지
- 분석 파이프라인 (PDF는 result 렌더만) / 공유 URL·외부 링크 일체 / 히스토리 트랙 정책(171b) / 카카오 복사

## 검증
- recent 차단+안내 / 파일명 sanitize / 소유권(타인 차단) 테스트
- 전체 pytest·tsc·build = Codex 권위 (기준선 480/8 → 증가 예상, 신규 기준선 명시)

## 커밋 (Codex)
feat(BOHUMFIT-157): 히스토리 리포트 PDF 다운로드 (고객 전달용 파일 방식)
