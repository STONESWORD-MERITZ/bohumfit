// BOHUMFIT-131: 브랜드 그린 원형 로딩 스피너(외부 라이브러리 없이 Tailwind animate-spin).
const BRAND_GREEN = "#2d6a4f";

export default function Spinner({ size = 48, label }: { size?: number; label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3">
      <span
        role="status"
        aria-label={label || "로딩 중"}
        className="inline-block animate-spin rounded-full border-[3px] border-current border-t-transparent"
        style={{ width: size, height: size, color: BRAND_GREEN }}
      />
      {label && (
        <p className="text-sm font-semibold" style={{ color: BRAND_GREEN }}>
          {label}
        </p>
      )}
    </div>
  );
}
