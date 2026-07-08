# BOHUMFIT-184 — [전] 보유 계약 리스트 표기

Owner flow: Claude Chat -> Claude Cowork -> Codex
Current owner: **Codex (구현) — ⚠마운트 손상(parser/constants)으로 Cowork 코드 편집 불가, 아래 명세대로 Windows 원본에 구현**

## ⚠환경 블로커
182/183과 동일 — parser.py·constants.py 마운트 뷰 손상 + constants import 불가로 통합 테스트 불가. Codex가 182·183 위에 누적하여 Windows 원본에 구현.

## 목적
[전] 섹션에 계약별 {회사명·상품명·납입기간/만기·월보험료·비고} **보유 계약 리스트 블록** 추가(하단 비고를 정식 리스트로 승격). 요청1(보험사명·상품명·보험료·납/만기 명시) 충족.

## S0 실사 (Cowork)
- 현행 `parse_contract_list`는 `CONTRACT_LINE_RE`에 **`maturity` 그룹 이미 존재**(`종신|\d+세|\d{4}`) → `contracts[].maturity` 캡처됨. `pay_years`·`pay_months`·`monthly_premium`·`insurer`·`product`·`remark`(계피)도 이미 `build_before`의 `companies[]`에 존재. → **S1 만기 캡처는 대부분 불필요**(schema Contract에 maturity 필드 존재 확인만; 없으면 추가).
- 즉 184는 주로 **렌더 추가**(export_excel [전] 시트·export_pdf·CoverageRemodel [전])이며, 데이터는 companies[]에 이미 있음.
- BOP(182): monthly_premium=None → "미제공" 표기 계승.

## 구현 지시 (Codex)
1. `schema.py`(정상 파일): Contract에 `maturity` 필드 존재 확인, 없으면 추가(파서가 이미 채움).
2. `aggregator.py`: `build_before`가 [전] 렌더용 계약 리스트를 companies[]로 이미 제공 — 필요 시 `contract_list` 별칭만 추가(회사·상품·pay_years·maturity·monthly_premium·remark). 월납 내림차순·BOP 맨 뒤(182 정합 계승).
3. `export_excel.py` "전 회사별세부" 시트 상단(또는 별도 구획)에 **보유 계약 리스트 표**: [번호·회사명·상품명·납입기간(예 "20년납")·만기(예 "90세"/"종신")·월보험료·비고]. 현행 하단 계약 비고 행을 이 표로 승격.
4. `export_pdf.py`: [전] 섹션에 동일 계약 리스트 표(매트릭스 앞) — FIT v1.1 스타일.
5. `CoverageRemodel.tsx`: [전] 섹션 회사 카드에 **납입기간·만기** 추가(현행 회사·상품·월납·remark에 이어) → 정식 "보유 계약 리스트". 월보험료 None은 "미제공".

## S4 — 테스트 (backend/tests/test_coverage_contract_list_184.py, 익명·합성)
- 계약별 필드 존재·표기: 회사·상품·납입기간·만기·월보험료·비고. BOP "미제공". 월납 내림차순·BOP 맨 뒤.
- 182(회사명/카운트)·183(대분류) 회귀 + 담보 집계값 불변.

## 수정 금지
- 대분류 로직(183) 변경 · 회사명/카운트 정합(182) 회귀 · 담보 집계값 불변.

## 커밋 (Codex)
feat(BOHUMFIT-184): [전] 보유 계약 리스트(회사·상품·납만기·보험료) 표기
