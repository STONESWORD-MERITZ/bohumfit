# BOHUMFIT-159 — 무료/Pro 경계 업셀 UX

Owner flow: Claude Chat -> Claude Cowork -> Codex
Current owner: Cowork

## 배경
148 감사 P1 항목. 무료 사용량 소진·샘플 열람 시점이 Pro 전환의 핵심 접점인데
현재는 단순 문구("무료 체험 5회를 모두 사용했습니다. 구독 후 계속 이용하세요.")만 노출됨.
156에서 히스토리 한도 409 → Pro 안내 1줄이 추가된 상태 — 이와 톤·패턴을 통일한다.

## 브랜드 원칙 (FIT v1.1)
- 브랜드 보이스: 수치와 근거로, 한 문장 한 메시지, 버튼은 동사로 끝, 지시 아닌 제안 톤 ("즉시 가입하십시오" ✗)
- 라임 CTA는 에메랄드/다크 서피스 위 화면당 1회만
- v1.1 토큰만 사용 (raw gray 금지)

## Step 0 — 진단 (구현 전 필수)
1. 무료 사용량 판정·소진 상태의 프런트 노출 지점 전수 매핑
   (Disclosure 분석 버튼 영역·billing_status 소비 지점·ReportSample·Subscription 유입 동선)
2. 백엔드 사용량 API(billing_status 등)가 "잔여 횟수"를 내려주는지, 소진 여부만 내려주는지 확인
   — 잔여 횟수가 없으면 백엔드 최소 수정으로 remaining 필드 추가 (분석 로직 무접촉)

## Step 1 — 소진 전 인지 (잔여 표시)
- 분석 화면에 잔여 횟수 배지: "무료 분석 N회 남음" (remaining ≤ 2부터 노출, 그 전엔 숨김 — 과노출 금지)
- v1.1 캡션 위계(600·12), 그린티 틴트 면 허용

## Step 2 — 소진 시점 전환 카드
- 기존 빨간 경고 문구를 전환 카드로 교체:
  · 헤드라인: 근거 수치 포함 (예: "무료 분석 5회를 모두 사용했어요")
  · 본문 1줄: Pro 가치 제안 (실제 혜택만 — 발명 금지, Subscription.tsx 실제 플랜 내용과 대조)
  · CTA: "요금제 보기" (프라이머리, /subscription 이동)
- 에러 톤(red) → 안내 톤 전환. 단 접근성 대비 AA 유지

## Step 3 — 샘플 리포트 전환 동선
- ReportSample 하단에 전환 섹션 1개: 비로그인 "가입하고 분석 시작하기" → /signup,
  로그인 "내 PDF로 분석하기" → /disclosure
- 딱 1개 섹션만 — 샘플 열람을 방해하는 중간 삽입 금지

## Step 4 — Subscription 페이지 정합
- 유입 시 문구가 위 카드의 가치 제안과 일치하는지 확인, 불일치만 최소 수정
- 결제 로직·토스 빌링 코드 절대 무접촉

## 수정 금지
- 결제/빌링 로직 일체 (문구·스타일만)
- 분석 파이프라인 / 사용량 차감 판정 로직 (remaining 응답 필드 추가만 예외 허용)
- NAV 구조 / 신규 라우트 추가 금지

## 검증 체크리스트
- [ ] Step 0 매핑 + remaining 필드 필요 여부 handoff 기록
- [ ] 라임 CTA 화면당 1회 원칙 준수 / raw gray 0
- [ ] 가치 제안 문구가 Subscription 실제 플랜과 일치 (발명 0)
- [ ] 백엔드 수정 시 관련 테스트 추가, tsc/build/pytest는 Codex 권위 (기준선 473 passed, 8 skipped)

## Stage 예정 (Codex)
- src/pages/Disclosure.tsx·ReportSample.tsx·Subscription.tsx (+ Step 0 판단에 따라 backend/main.py + 테스트)
- .agent-harness/tasks/BOHUMFIT-159-upsell-ux.md, handoff.md, locks.md

## 커밋 메시지 (Codex)
feat(BOHUMFIT-159): 무료/Pro 경계 업셀 UX (잔여 표시·전환 카드·샘플 동선)
