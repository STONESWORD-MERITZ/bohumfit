// BOHUMFIT-048: '왜 중요한가' 페이지 콘텐츠 데이터.
// 페이지 파일 비대화·마운트 truncation 리스크를 줄이기 위해 데이터를 분리한다.
// 수치는 출처와 함께 표기하고, 예시는 '재구성 예시'로 명시한다(과장 표현 금지).

import type { BadgeTone } from "../../components/ui/Badge";

/** THE NUMBERS — 정량 통계 카드 */
export interface StatCard {
  figure: string;
  unit?: string;
  label: string;
  source: string;
}

export const STAT_CARDS: ReadonlyArray<StatCard> = [
  {
    figure: "71.2",
    unit: "만 명",
    label: "국내 보험설계사 수 — 대부분의 보험은 사람을 거쳐 가입됩니다.",
    source: "2025년 말 기준 · 금융감독원",
  },
  {
    figure: "99.3 / 71.4",
    unit: "%",
    label: "대면 채널 판매 비중 (생명보험 / 손해보험) — 설명·고지가 대면에서 오갑니다.",
    source: "2024년 · 보험연구원",
  },
];

/** THE NUMBERS — 정성 카드(숫자가 아닌 구조적 사실) */
export interface QualCard {
  title: string;
  body: string;
}

export const QUAL_CARDS: ReadonlyArray<QualCard> = [
  {
    title: "반복되는 분쟁 사유",
    body:
      "계약 전 알릴의무(고지의무)는 금융감독원이 별도의 소비자 유의사항을 반복해 안내할 만큼 " +
      "분쟁이 잦은 영역입니다. 그만큼 많은 사람이 같은 지점에서 어긋납니다.",
  },
  {
    title: "기억에 의존하는 구조",
    body:
      "고지는 보통 가입 시점의 '기억'에 기대 이뤄집니다. 그런데 문제는 몇 년 뒤 보험금을 " +
      "청구하는 시점에 드러납니다 — 기억과 기록이 어긋나는 순간입니다.",
  },
];

/** 알릴의무 메커니즘 — 청약서가 묻는 대표 기준 */
export const DISCLOSURE_CRITERIA: ReadonlyArray<string> = [
  "최근 5년 이내 입원 또는 수술",
  "최근 5년 이내 7일 이상 계속 치료",
  "최근 5년 이내 30일 이상 투약",
  "동일 질병으로 7회 이상 통원",
];

/** 분쟁 3장면 — 일반적 분쟁 유형 재구성 예시 (실제 개별 사건 아님) */
export interface ConflictScene {
  result: string;
  resultTone: BadgeTone;
  title: string;
  body: string;
}

export const CONFLICT_SCENES: ReadonlyArray<ConflictScene> = [
  {
    result: "지급 거절",
    resultTone: "danger",
    title: "과거 진료와의 인과관계로 보험금이 거절됩니다",
    body:
      "청구한 질병이 가입 전 진료 이력과 의학적으로 연결된다고 판단되면, 고지하지 않은 병력을 " +
      "근거로 보험금 지급이 거절될 수 있습니다.",
  },
  {
    result: "분쟁",
    resultTone: "warning",
    title: "“분명히 말했는데” — 기록이 없어 분쟁이 됩니다",
    body:
      "구두로 알린 병력이 청약서·전산에 남지 않으면, 청구 시점에 '고지했다 / 못 들었다'를 두고 " +
      "다투게 됩니다. 입증 책임은 종종 가입자에게 돌아옵니다.",
  },
  {
    result: "계약 해지",
    resultTone: "danger",
    title: "기억나지 않던 병력 하나로 계약이 해지됩니다",
    body:
      "본인도 잊고 있던 과거 진단·처방이 뒤늦게 확인되면, 고지의무 위반으로 계약 자체가 해지되고 " +
      "이미 낸 보험료의 보장도 사라질 수 있습니다.",
  },
];

/** 핵심 메커니즘 — 왜 가입 후(청구 시점)가 중요한가.
 *  통계가 아니라 고지의무의 법·실무 구조(서면 질문 대상·청구 시 서면 확인)에 대한 사실 서술. */
export interface MechanismStep {
  step: string;
  title: string;
  body: string;
}

export const MECHANISM_STEPS: ReadonlyArray<MechanismStep> = [
  {
    step: "01",
    title: "병력이 있다면, 청약서에 성실히 알립니다",
    body:
      "가입 전 알릴의무(고지의무)는 청약서가 서면으로 묻는 질문에 사실대로 답하는 것입니다. " +
      "최근 진단·입원·수술·투약 같은 병력이 질문 대상이며, 빠뜨리면 나중에 문제가 됩니다.",
  },
  {
    step: "02",
    title: "청구할 때, 보험사는 ‘서면 기록’으로 확인합니다",
    body:
      "보험금 청구 시점에 보험사는 진료기록 등 서면 자료로 고지 내용을 대조합니다. 가입할 때 " +
      "설계사에게 구두로만 알린 내용은 청약서·전산에 남지 않으면 ‘고지했다’고 인정받기 어렵습니다.",
  },
  {
    step: "03",
    title: "그래서 ‘가입하는 순간’보다 ‘가입한 뒤’가 중요합니다",
    body:
      "문제는 보통 가입 몇 년 뒤, 보험금을 청구하는 순간에 드러납니다. 그때 기억과 기록이 어긋나면 " +
      "지급 거절·계약 해지로 이어질 수 있습니다. 가입 전에 기록으로 미리 점검하면 이 위험을 줄일 수 있습니다.",
  },
];
