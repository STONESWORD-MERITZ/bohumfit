// BOHUMFIT-269b — 하단 네비 탭 정의(상수 전용 모듈).
//   ★컴포넌트 파일과 분리한 이유: 같은 파일에서 상수를 내보내면 fast-refresh가 깨진다(lint 규칙).
//   ★탭은 **모바일 개편이 끝난 화면**만 담는다 — 덜 다듬어진 화면으로 유도하지 않기 위해서다.
//     실손 계산·요금제·히스토리·자료 받기를 뺀 사유는 269b 태스크 문서에 있다.
//   ★라우트를 신설하지 않는다 — 전부 기존 `Layout` NAV에 있던 경로다.
import { Home, FileSearch, ShieldCheck, Link2, type LucideIcon } from "lucide-react";

export type BottomNavTab = {
  to: string;
  label: string;
  Icon: LucideIcon;
  /** 활성 판정용 경로(쿼리스트링이 붙는 탭 때문에 분리). */
  match: string;
};

export const BOTTOM_NAV_TABS: BottomNavTab[] = [
  { to: "/dashboard", label: "홈", Icon: Home, match: "/dashboard" },
  { to: "/disclosure?mode=agent", label: "고지의무", Icon: FileSearch, match: "/disclosure" },
  { to: "/coverage-compare", label: "보장분석", Icon: ShieldCheck, match: "/coverage-compare" },
  { to: "/insurance-links", label: "보험사", Icon: Link2, match: "/insurance-links" },
];

/** 네비 높이(px) — 본문 하단 여백 계산에 쓰인다(마지막 요소 가림 방지). */
export const BOTTOM_NAV_HEIGHT = 60;
