# BOHUMFIT-049 메인(Home) 창업 미션·회사소개 섹션 추가 — Mercury

## Owner
Cowork(Claude) — 구현 1차. 검증·커밋·푸시 Codex(Windows), 확인 Human.

## 목표
별도 회사소개 페이지 대신 메인 히어로 아래 '미션/창업 스토리' 섹션(id="mission") 추가.
기능·라우팅 변경 없음. 다른 페이지 무수정.

## 락 충돌 처리 (중요)
- 착수 시점 `BOHUMFIT-048`(Codex)가 `WhyDisclosure.tsx`를 **Active 락** 보유(검증·퍼블리시 중).
- 절대 규칙(active lock 파일 중복 편집 금지)에 따라 **049는 WhyDisclosure 무수정**.
- 048에서 임시로 둔 /why '회사소개' 링크(`/`)를 `/#mission` 앵커로 바꾸는 건 **048 락 해제 후 후속**으로 미룬다(handoff 명시). 049는 앵커 타깃(id="mission")만 Home에 마련.

## 추가 섹션 — OUR MISSION (히어로 바로 아래, id="mission")
- 기존 Home의 일반 'Our Mission' 섹션(generic 카피)을 **창업 스토리 섹션으로 교체**(미션 섹션 2개 중복 방지). 위치: 히어로 직후, scroll-scrub 커버 래퍼(`relative z-10 bg-canvas`) 내부.
- eyebrow: OUR MISSION / 제목: "보험은 가입보다 점검이 먼저입니다"
- 본문(대표 1인칭, 태스크 제공 원문 그대로) + 서명 "— 보험핏 대표 이민규"
- 신뢰 지표 1회: "메리츠화재 정규직 지점장 · 1만 명 이상 설계사 업무 지원"(사실 진술·과장 없음, Badge/보조 라인).
- 가치 3카드: 고객 권리 보호 / 중립적 점검(가입권유 아님) / 데이터 기반(심평원 원자료).
- 보조 CTA: "왜 중요한가 →"(/why), "지금 점검하기 →"(/disclosure).

## 디자인
- 045 토큰·ui(Card/Button/Callout/Badge) 재사용. 라이트 캔버스, 다크 섹션 남발 금지. 대표 사진 없음(텍스트 중심).
- 회사 기본정보(상호·대표·연락처)는 푸터에 이미 있으므로 **중복 표기 금지**(미션 본문 서명·신뢰지표만, 사업자번호/연락처 미표기).

## ENV
- Home 대형 → 섹션을 `HomeMission.tsx`로 분리(마운트 truncation 회피). 마운트 git 금지, 검증 /tmp.
- 스크린샷: 직전 태스크에서 샌드박스 libXdamage1 부재로 Chromium 불가 이력 — 가능 시 시도, 불가 시 SSR 마커 검증 + handoff ⚠.

## 검증
- /tmp tsc + Home SSR 마커(미션 제목·서명·신뢰지표·가치 3카드·id="mission"·CTA /why·/disclosure).
- Codex(Windows): tsc/lint/test/build + Home 육안(미션 섹션·앵커 스크롤).

## 산출 기록
- handoff: 섹션 구성·앵커 id·신뢰지표 문구·CTA 라우트·WhyDisclosure 링크 후속. Next: Codex → Human.
