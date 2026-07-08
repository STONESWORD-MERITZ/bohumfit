# BOHUMFIT-182 — 회사명 wrap 보정 + [전] 열·계약 수 정합

Owner flow: Claude Chat -> Claude Cowork -> Codex
Current owner: **Codex (구현) — ⚠마운트 손상으로 Cowork 코드 편집 불가, 아래 명세대로 Windows 원본에 구현**

## ⚠환경 블로커 (중요)
`backend/coverage/parser.py`(null 53B)·`constants.py`(null 1845B, byte 5262부터 null 패딩)·`amount.py`(null 715B)의 **마운트 뷰가 손상**(ENV-MOUNT-NOTES: UTF-8 mid-byte truncation → null 패딩). Codex 커밋 Windows 원본은 정상(514 passed). Cowork가 마운트에서 이 파일을 편집하면 정상 원본을 오염시킬 위험 + constants import 불가로 /tmp 검증 불가 → **Cowork 코드 미편집, Codex가 Windows 원본에 구현**. (aggregator/export_excel/export_pdf/schema/service는 마운트 정상.)

## S0 실사 (Cowork, 읽기 가능한 실 데이터 기준)
- 접근 가능 실 자료: `보장분석/김대휘님 상품별 가입 현황.pdf`(2p, 매트릭스만)·`이원록님…`(2p)·`문건주님 kb보장분석 제안서.pdf`(30p, 전체). ※명세의 "황종철"은 오기 — 실제는 김대휘/이원록.
- **BOP(보험료미제공) 확인**: 김대휘 매트릭스 헤더 `(2) DB손보` 상품 "실손의료비보험[계약전환용]2001"의 월보험료 행 = **"보험료미제공"**(금액 아님). 계약기간·만기(예 "40세 만기")만 있고 **납입기간(N년납)·월납 금액이 없음**.
- **8vs7 메커니즘**: 현행 `parser.parse_contract_list`의 `CONTRACT_LINE_RE`는 `월납 + N년 + 만기 + [금액]원`을 요구. BOP 계약은 (a)월보험료가 "보험료미제공", (b)납입기간 N년 부재 → **CONTRACT_LINE_RE 미매치 → p5 계약에서 누락**. 반면 `parse_matrix`의 열 인덱스는 `(n)` 헤더(`PAGE_COL_RE`)에서 BOP 열 포함 → 열수 > 계약수 → `parse_document` L286-289 경고.
- **회사명 wrap 메커니즘**: `CONTRACT_PREFIX_RE=r"^\s*(\d+)\s+(\S+)\s*(.*)"`의 insurer=`(\S+)`(첫 토큰). 회사명이 p5 셀에서 2줄 wrap("메리츠화\n재")되어 날짜행에서 벗어나면, 날짜행 첫 토큰=상품명 접두("무"/"무배당") → insurer가 상품명 접두로 오표기. (메리츠/신한 실 케이스는 접근 자료에 없음 → S1은 메커니즘 기반 + Codex 실 PDF 검증.)
- 회귀 기준선(문건주): 월납 573,227 · 총납입 181,984,128 · 상해사망 5.5억 · 일반암 1억(불변 필수).

## S1 — 회사명 wrap 보정 (parser.py)
1. `constants.py`에 `KNOWN_INSURERS`(despace 비교용) 추가:
   메리츠화재·신한라이프생명·신한라이프·DB손보·KB손보·롯데손보·삼성화재·삼성생명·한화손보·한화생명·현대해상·라이나생명·라이나(에이스)손보·NH농협손보·NH농협생명·흥국화재·흥국생명·MG손보·AIA생명·교보생명·미래에셋생명·동양생명·ABL생명·처브라이프·하나손보·캐롯손보 등(운영 중 확장).
2. `parse_contract_list`에서 각 계약 행 + 인접 continuation 줄(before/after)을 결합한 despace 텍스트에서 `KNOWN_INSURERS` 최장일치 탐색 → insurer 확정, product에서 해당 회사명 제거.
3. 폴백 규칙: KNOWN 미일치 시 `CONTRACT_PREFIX_RE` insurer는 **회사 접미(손보/화재/생명/해상/손해보험/생명보험)로 끝날 때만** 채택, 아니면 `insurer=None`(상품명 접두 누출 금지).

## S2 — [전] 열·계약 수 정합 (BOP 포함)
1. `CONTRACT_LINE_RE` 월보험료 그룹에 `|보험료미제공|미제공` 허용, 파싱 시 `monthly_premium=None`. 납입기간 없는 BOP 대응 **보조 패턴**(날짜+만기+"보험료미제공", 월납·N년 옵셔널) 추가 → BOP 계약도 `contracts`에 포함(idx·insurer 유지, pay_years/pay_months=None).
2. **정합(정책=BOP 열 포함)**: `parse_document`(또는 aggregator)에서 매트릭스 열 인덱스 집합 ⊋ 계약 idx 집합이면, 누락 idx마다 placeholder 계약 합성(idx·insurer=매트릭스 헤더 파싱 가능 시 그 값/불가 시 None·monthly_premium=None·remark 겸용 "보험료 미제공"). → 계약집합 == 열집합.
3. `companies` 정렬: 월납 내림차순, `monthly_premium is None`(BOP)은 **맨 뒤**. BOP 표기 "미제공".
4. 경고: 정합 후에도 불일치할 때만 warning(정상 BOP는 경고 0).
   - ※Human 재확인 포인트: 정책=BOP 열 포함. 만약 Codex 실 PDF 실사에서 "BOP 열 제외"가 KB 양식상 정답이면 반대 정책 채택 + 근거 handoff 기록.

## S3 — 회귀
- 문건주 전체 PDF: 계약 6·월납 573,227·총납입 181,984,128·상해사망 5.5억·일반암 1억·경고 0 불변.
- 김대휘/이원록(전체 제안서 확보 시): 회사명 정상·열수==계약수·경고 0.

## S4 — 테스트 (backend/tests/test_coverage_parser_182.py, 익명·합성)
- 회사명 wrap 결합: 합성 p5(회사명 2줄 wrap "메리츠화"+"재" → insurer "메리츠화재").
- BOP 계약 열 포함: 합성 p5(1계약 보험료미제공·납입기간 없음) → contracts에 포함·monthly_premium None.
- 카운트 정합: 매트릭스 열집합 == 계약 idx집합, 경고 0. BOP 월납 desc 맨 뒤·"미제공".
- 179/179b 회귀 재확인.

## 수정 금지
- 대분류 순서·담보→대분류 매핑(→183)·37담보/집계방식(constants) 값·export/CoverageRemodel 렌더 로직(파싱/집계 정합만).

## 커밋 (Codex)
feat(BOHUMFIT-182): 회사명 wrap 보정 + [전] 열·계약 수 정합
