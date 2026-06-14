# BOHUMFIT-047 영업용 PDF 리포트 — 브랜딩·면책 강화·색 정리

## Owner
Cowork(Claude) — 구현. 검증·커밋은 Codex(Windows). 산식·결과값 무수정, 텍스트/브랜딩/색만.

## 전제
- 046(3색 토큰) 위에서. 051에서 리포트 헤더 로고는 이미 적용됨.

## 반영
### 브랜딩
- 헤더 로고 유지. 푸터에 회사명·연락처 + 도메인 `BOHUMFIT.AI` 추가.
- 사업자 정보(상호 보험핏·대표 이민규·사업자번호 174-29-01975·주소 env) 현재 값 유지 — '통합 사업자' 확정 전. 주소 미설정 placeholder는 handoff '확정 필요'.

### 면책 강화(영업 자료 수준)
- 본 자료 = 보험 가입 권유·모집이 아니라 보유/제안 보험의 점검·분석 참고자료.
- 점검 결과는 추정이며 보험사 심사·지급을 확정하지 않음.
- 결과는 저장하지 않으며 출력물은 고객 본인이 보유.
- 모집 비주체 고지 기조 유지.

### 색(신뢰 문서 = 색 최소화)
- 골드(#C9A227/#8C6D1F/#FBF6E7/#E5D9AE) 전면 제거. 네이비도 짙은 슬레이트로.
- 흰 배경 + 짙은회색 본문 + 헤어라인 테두리 위주. 보라는 헤더 브랜드바 1포인트만(절제). 헤더 로고가 브랜드색 담당.
- :root CSS 변수 repoint(단일 소스): --navy→슬레이트, --gold→중립 회색, brand-bar 골드부분→보라.

## PDF 렌더 함정(051 동일)
- SVG data-URI는 <?xml?>/<!DOCTYPE> 제거본(이미 적용), 이미지 디코드 대기 후 PDF 생성(이미 적용) — 무변경.

## 범위
- `backend/pipeline/report_pdf.py`(면책 상수·BUSINESS_FOOTER domain), `backend/templates/report_disclosure.html`·`report_insurance.html`(색 var·footer 도메인). 산식·결과·레이아웃 무수정.

## 자체검증
- /tmp 샘플 PDF 1건 생성해 면책·브랜딩·색 마커/육안 + report 관련 pytest. tsc/build 영향 없음.

## 산출
- handoff: 면책 문구 전문·사업자 placeholder 확정 필요·색 전후. Next: Codex 검증·커밋 → 048.
