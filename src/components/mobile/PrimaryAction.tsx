// BOHUMFIT-265 — 주 액션 버튼(56px)·하단 고정 패턴. 엄지 도달 영역에 둔다.
//   ★진행 중에도 전체 화면 스피너를 띄우지 않는다 — 버튼 라벨을 바꾸고 비활성화한다.
//   ★적용은 266~ — 265에서는 정의만 한다.
import type { ReactNode } from "react";
import { MOBILE_LAYOUT, MOBILE_TOUCH } from "./tokens";

export interface PrimaryActionProps {
  label: string;
  onPress: () => void;
  /** 처리 중 — 라벨을 교체하고 중복 탭을 막는다. */
  pending?: boolean;
  pendingLabel?: string;
  disabled?: boolean;
  /** true면 화면 하단에 고정(엄지 도달). false면 흐름 안에 배치. */
  fixed?: boolean;
  /** 버튼 위 보조 정보(선택 건수 등). */
  hint?: ReactNode;
}

export default function PrimaryAction({
  label,
  onPress,
  pending = false,
  pendingLabel = "처리 중…",
  disabled = false,
  fixed = true,
  hint,
}: PrimaryActionProps) {
  const button = (
    <button
      type="button"
      onClick={onPress}
      disabled={disabled || pending}
      aria-busy={pending}
      className="w-full bg-accent-600 font-bold text-white disabled:opacity-60"
      style={{
        minHeight: MOBILE_TOUCH.action,
        borderRadius: MOBILE_LAYOUT.radiusBtn,
        fontSize: 16,
      }}
    >
      {pending ? pendingLabel : label}
    </button>
  );

  if (!fixed) return <div>{hint}{button}</div>;

  return (
    <div
      className="m-action-bar fixed inset-x-0 bottom-0 z-40 border-t border-line bg-white"
      style={{ paddingLeft: MOBILE_LAYOUT.gutter, paddingRight: MOBILE_LAYOUT.gutter, paddingTop: 12 }}
      data-testid="primary-action-bar"
    >
      {hint && <p className="mb-2 text-[15px] leading-[1.55] text-ink-soft">{hint}</p>}
      {button}
    </div>
  );
}
