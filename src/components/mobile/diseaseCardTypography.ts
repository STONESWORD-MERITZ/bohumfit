// BOHUMFIT-270 — DiseaseCard 모바일 폰트 오버라이드(B안)의 **모바일 클래스 정본**.
//
//   ★B안 = 모바일에서만 폰트를 올리고 데스크톱은 무변경. A안(공통 상향)은 데스크톱 레이아웃에
//     영향이 가서 채택하지 않았다(Human 확정).
//   ★이 파일이 `src/components/mobile/` 안에 있는 것은 의도다 — 265 하한 가드
//     (`mobileTokens.test.ts` "15px 미만 폰트 지정이 없다")가 이 폴더 전체를 스캔하므로,
//     모바일 값이 **가드 안으로 들어와** 자동으로 검사받는다. 269b에서 라벨 11px가 이 가드에
//     걸렸을 때 우회하지 않고 15px로 올린 것과 같은 태도다.
//   ★반대로 **데스크톱 원문 값(10~13px)은 여기 두지 않는다** — 두면 가드가 정당하게 실패한다.
//     데스크톱 맵은 `src/pages/Disclosure.tsx`가 갖고, 이 파일의 키 타입으로 고정된다
//     (키가 갈라지면 tsc가 잡는다).
//   ★쓰는 값은 265 토큰 3단 중 body(16)·sub(15)뿐이다. title(20)은 쓰지 않는다 —
//     카드 병명이 모바일 화면 요약 헤더(20px)와 동급이 되어 계층이 뒤집히기 때문.
import { MOBILE_TYPO } from "./tokens";

/** 카드 안에서 크기를 지정하는 요소 키(데스크톱 맵과 공유하는 계약). */
export const DISEASE_CARD_TYPO_KEYS = [
  "name",
  "code",
  "insuranceOnly",
  "meta",
  "detail",
  "chip",
  "medToggle",
  "medNote",
  "evidenceToggle",
  "evidenceBody",
  "evidenceNote",
  "suspectNote",
  "bottom",
] as const;

export type DiseaseCardTypoKey = (typeof DISEASE_CARD_TYPO_KEYS)[number];

/**
 * 모바일 폰트 크기 클래스.
 *  계층: 병명 16(bold) ≥ 판정 상세 16(medium) ≥ 그 외 15 — 역전 0.
 *  ★굵기·색은 호출부가 그대로 유지한다(이 맵은 **크기만** 책임진다).
 */
export const DISEASE_CARD_MOBILE_TYPO: Record<DiseaseCardTypoKey, string> = {
  /** 병명 — 카드 최상위 식별자. */
  name: "text-[16px]",
  /** 상병코드 — 청약서에 그대로 옮겨 적는 값이라 오독 비용이 가장 크다(I10/M51.9 등). */
  code: "text-[15px]",
  /** 실손 전용 고지 안내 — 고지 여부를 가르는 정보. */
  insuranceOnly: "text-[15px]",
  /** 진료기간·입원기간·최초진단 — 고지서 전기 대상 날짜(정보 밀도 최대). */
  meta: "text-[15px]",
  /** 판정 상세 — 카드의 결론 문장. */
  detail: "text-[16px]",
  /** Chip(입원·통원·수술·투약 수치). */
  chip: "text-[15px]",
  /** 투약 산식 토글(183) — ★문구는 무변경, 크기만 올린다. */
  medToggle: "text-[15px]",
  /** 투약 산식 문구(183) — ★문구 무변경. */
  medNote: "text-[15px]",
  /** 근거 상세 토글(213). */
  evidenceToggle: "text-[15px]",
  /** 근거 상세 내용(진료일·병의원). */
  evidenceBody: "text-[15px]",
  /** 근거 각주. */
  evidenceNote: "text-[15px]",
  /** 수술 의심 설명 문단. */
  suspectNote: "text-[15px]",
  /** 하단 블록(의심 행위·치료 사유). */
  bottom: "text-[15px]",
};

/** 265 토큰과의 정합 — 이 맵이 쓰는 px는 body(16)·sub(15)뿐이다. */
export const DISEASE_CARD_MOBILE_PX_ALLOWED = [MOBILE_TYPO.body.px, MOBILE_TYPO.sub.px] as const;
