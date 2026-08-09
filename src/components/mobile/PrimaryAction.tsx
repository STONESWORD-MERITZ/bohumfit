// BOHUMFIT-265 — 주 액션 버튼(56px)·하단 고정 패턴. 엄지 도달 영역에 둔다.
//   ★진행 중에도 전체 화면 스피너를 띄우지 않는다 — 버튼 라벨을 바꾸고 비활성화한다.
//   ★적용은 266~ — 265에서는 정의만 한다.
//
// BOHUMFIT-273: 고정 액션 바와 269b 하단 네비가 **둘 다 `fixed bottom-0 z-40`**이라 같은 자리를 다퉜다.
//   z-index가 같으면 DOM 뒤쪽이 위에 오는데 `Layout`은 `<main>` 다음에 네비를 렌더하므로
//   **네비가 주 액션 버튼의 아래쪽 80%를 덮었다**(실측: 56px 중 45px). 버튼을 누르려다 탭이 눌려
//   의도치 않게 화면이 이탈했다. → 액션 바를 **네비 위로 쌓아** 둘 다 온전히 쓰게 한다.
import type { ReactNode } from "react";
import { MOBILE_LAYOUT, MOBILE_TOUCH } from "./tokens";
// BOHUMFIT-278: 273이 만든 네비 높이 추종 로직을 **공용 계약으로 승격**했다(동작 동일).
import { ACTION_BAR_BELOW, BOTTOM_SURFACE_Z, useBottomSurfaceOffset } from "./bottomSurface";

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
  // BOHUMFIT-273: 고정 배치일 때만 관찰한다(흐름 안 배치는 겹칠 일이 없다 — 268a 시트가 그 경우다).
  const navHeight = useBottomSurfaceOffset(ACTION_BAR_BELOW, fixed);
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
      className="m-action-bar fixed inset-x-0 bottom-0 border-t border-line bg-white"
      style={{
        paddingLeft: MOBILE_LAYOUT.gutter,
        paddingRight: MOBILE_LAYOUT.gutter,
        paddingTop: 12,
        zIndex: BOTTOM_SURFACE_Z.action,   // BOHUMFIT-278: 층위 토큰(네비 위·배너 아래)
        // BOHUMFIT-273: 네비가 있으면 그 위로 올라가고, 인디케이터 여백은 아래 네비가 책임지므로
        //   `.m-action-bar`의 세이프에어리어 패딩을 평상시 값(12px)으로 덮는다(이중 여백 0).
        //   ★네비가 없으면 아무것도 덮지 않아 **현행과 완전히 같은 마크업**이 나온다.
        ...(navHeight > 0 ? { bottom: navHeight, paddingBottom: 12 } : null),
      }}
      data-testid="primary-action-bar"
      data-above-bottom-nav={navHeight > 0 ? "true" : undefined}
    >
      {hint && <p className="mb-2 text-[15px] leading-[1.55] text-ink-soft">{hint}</p>}
      {button}
    </div>
  );
}
