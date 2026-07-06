# BOHUMFIT-171a — 업로드 영역 UI 개선 (파일 목록 압축·중복 제거·미리보기 삭제)

Owner flow: Claude Chat -> Claude Cowork -> Codex
Current owner: Cowork

## Human 확정 요구 3건
1. 파일 10개 업로드 시 목록이 공간을 과도하게 차지 → 압축
2. "PDF 파일을 여기에 드래그하거나 클릭하세요" 문구와 "파일선택 / 선택된 파일 없음" 네이티브 UI가 중복 → 정리
3. 업로드한 PDF 미리보기 기능 제거 (불필요)

## Step 0 — 진단
- Disclosure.tsx의 업로드 카드 구조 파악: 드롭존·파일 목록·네이티브 input 노출 방식·
  PDF 미리보기(138에서 추가된 것) 코드 위치 매핑

## Step 1 — 드롭존 단일화
- 네이티브 "파일선택/선택된 파일 없음" 노출 제거 (input type=file은 sr-only/hidden 처리, 드롭존 전체를 클릭 타깃으로)
- 드롭존 문구 1개만: "PDF를 드래그하거나 클릭해 업로드 (최대 10개)"
- 키보드 접근성 유지: 드롭존에 role="button"·tabIndex·Enter/Space 처리 + aria-label (기존 137 접근성 기준 후퇴 금지)

## Step 2 — 파일 목록 압축
- 파일 1~2개: 파일명 그대로 표시 (현행 유사)
- 3개 이상: 컴팩트 모드 — 요약 행 "파일 N개 · 총 M MB" + 접기/펼치기
  · 펼치면 파일명 리스트 (각 행 높이 축소: 아이콘+파일명+삭제 X 버튼 한 줄)
  · 개별 삭제 가능 유지
- 업로드 상태 체크 아이콘은 유지하되 행 높이 안에서

## Step 3 — PDF 미리보기 제거
- 미리보기 렌더 컴포넌트·상태·관련 라이브러리 import 제거
- 제거로 인한 미사용 코드 정리 (138 도입분 — 공유 코드인지 확인 후 안전 제거, 공유 시 호출부만 제거)
- 번들 영향 handoff에 기록

## 수정 금지
- 업로드 검증 로직(개수·용량 제한 값)·분석 실행 흐름
- 동의 체크박스 로직 (문구는 171b에서)

## Verification
- grep raw gray 0 / 미리보기 잔재(previewFiles·previewUrls 등) 0 / 접근성 후퇴 0
- tsc/build는 Codex/Windows 권위

## 커밋 (Codex)
feat(BOHUMFIT-171a): 업로드 UI 개선 (드롭존 단일화·파일 목록 압축·미리보기 제거)
