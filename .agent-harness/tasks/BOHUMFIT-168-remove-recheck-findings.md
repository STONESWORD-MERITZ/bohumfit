# BOHUMFIT-168 — 추가검사/재검사 소견 항목 결과에서 완전 제거

## 배경 (Human 확정 스펙)
추가검사/재검사 소견으로 잡힌 병력 항목을 분석 결과에서 **완전 제거**한다. 조건부 판정 없이 무조건 미출력.
(128 exam_check_only·[A]/[B] 분리, 142 접기/펼치기 UI가 현행.)

## 설계 원칙
- ★backend/pipeline/ 수정 허용(예외 태스크).
- 되돌림 위해 **감지 로직 삭제가 아니라 출력 차단**(결과 조립 단계 최소 절개점).
- 소견"만"으로 잡힌 항목만 제거. 실제 치료/투약/수술/입원 등 다른 근거 항목은 절대 영향 없음.

## Step 0 진단(구현 전 필수·handoff 기록)
- 소견 감지→집계→출력 경로(disease_aggregator/result_builder/filters/main) 매핑.
- 프런트 렌더(Disclosure 142 examOpen)+카카오(_build_kakao_message)+PDF 전 채널.
- ★외부 API 호출(requests/httpx/aiohttp/fetch/genai) 여부 grep→handoff 명시.
- 최소 절개점 근거 기록.

## Step 1 백엔드
- 절개점서 소견 유래 항목 출력 차단(소견만=제외 / 타 근거 병존=항목 유지+소견 필드 미출력).
- 전 채널 일관: 화면 결과 + standard/easy 카카오 + PDF.
- 신규 `backend/tests/test_recheck_removal_168.py`: (a)소견만→미출력 (b)소견+치료→병력 유지·소견필드 미출력 (c)소견없음→불변.
- 소견 출력 전제 기존 테스트(142 등) 신규 스펙에 맞게 수정 → 수정 목록 handoff.

## Step 2 프런트
- Disclosure.tsx 142 접기 UI·뱃지·examOpen 상태·미사용 타입 제거. ★스타일 토큰 교체 금지(167b 별도).

## 수정 금지
- 소견 무관 감지 로직(수술/투약/입원). 질병 집계 타 경로. Disclosure 소견 무관 영역.

## 검증(샌드박스)
- Step0 진단+API 여부 handoff / 신규 3케이스 자체검토 / 프런트 소견 문구 grep 소거 / 전체 pytest·tsc·build=Codex(기준선 458/8 변동 시 신규 기준선 handoff 명시).

## 커밋(Codex)
feat(BOHUMFIT-168): 추가검사/재검사 소견 항목 분석 결과에서 완전 제거
