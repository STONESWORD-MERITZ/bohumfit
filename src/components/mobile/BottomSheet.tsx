// BOHUMFIT-265 — 바텀시트(공통). 3종 용도(파일 선택·카톡 문안·내보내기)를 같은 구조로 재사용한다.
//   ★맥락 유지: 화면을 갈아끼우지 않고 현재 화면 위에 얹는다(뒤 배경이 계속 보인다).
//   배경 탭 닫힘 · 드래그 핸들 · Esc 닫힘 · 하단 안전영역 패딩(.m-sheet).
//   ★적용은 266~ — 265에서는 정의만 한다.
import { useEffect, useRef, type ReactNode } from "react";
import { MOBILE_LAYOUT, MOBILE_TOUCH } from "./tokens";

export interface BottomSheetProps {
  open: boolean;
  onClose: () => void;
  /** 시트 제목(스크린리더 라벨 겸용). */
  title: string;
  /** 제목 아래 한 줄 설명(선택). */
  description?: string;
  children: ReactNode;
  /** 하단 고정 액션 영역(선택) — 주 액션은 PrimaryAction을 쓴다. */
  footer?: ReactNode;
}

export default function BottomSheet({
  open,
  onClose,
  title,
  description,
  children,
  footer,
}: BottomSheetProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  // Esc로 닫기 — 열려 있을 때만 리스너를 붙인다.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[9998] flex items-end justify-center bg-ink-900/40"
      // ★배경 탭 닫힘 — 패널 내부 클릭은 아래에서 전파를 막는다.
      onClick={onClose}
      data-testid="bottom-sheet-backdrop"
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
        className="m-sheet w-full max-w-[560px] bg-white"
        style={{
          borderTopLeftRadius: MOBILE_LAYOUT.radiusCard,
          borderTopRightRadius: MOBILE_LAYOUT.radiusCard,
          paddingLeft: MOBILE_LAYOUT.gutter,
          paddingRight: MOBILE_LAYOUT.gutter,
        }}
      >
        {/* 드래그 핸들 — 시각 4px, 터치 영역은 44px(.m-tap). */}
        <button
          type="button"
          aria-label="닫기"
          onClick={onClose}
          className="m-tap mx-auto my-3 block h-1 w-10 rounded-full bg-ink-300"
          style={{ minHeight: 4 }}
          data-testid="bottom-sheet-handle"
        />
        <h2 className="text-[20px] font-bold leading-[1.35] text-ink-900">{title}</h2>
        {description && <p className="mt-1 text-[15px] leading-[1.55] text-ink-soft">{description}</p>}
        <div className="mt-4 max-h-[60vh] overflow-y-auto">{children}</div>
        {footer && (
          <div className="mt-4" style={{ minHeight: MOBILE_TOUCH.action }}>
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
