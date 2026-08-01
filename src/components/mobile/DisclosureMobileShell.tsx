// BOHUMFIT-267 P1 — 고지 결과 모바일 껍데기(헤더 요약 · 카톡 문안 시트 · 하단 고정 주 액션).
//
//   ★질병 카드는 **기존 `DiseaseCard`를 그대로** children으로 받는다. 모바일용으로 다시 그리면
//     251의 수술 건별 전개·동일일자 복수코드·미특정 블록이 새는데, 그건 고지 실무에서 치명적이다.
//     이 파일이 만드는 것은 카드를 감싸는 껍데기뿐이라 **정보 동등성이 구조적으로 보장**된다.
//   ★카톡 문안도 호출부가 만든 문자열(`memo`)을 **그대로** 보여주고 복사한다 — 재구성 0
//     (251 골든 픽스처 동등성 유지).
//   ★배지는 현행 Q 판정(Q1~Q5)·기간 라벨을 그대로 쓴다. 265의 4단으로 접으면 Q2/Q4/Q5의 기간이
//     사라지거나 **다른 기간으로 잘못 표기**되므로 매핑하지 않는다 — 267 태스크 "전제 반전 1" 참조.
//     (질문별 실제 기간은 `Disclosure.tsx`의 windowLabels가 정본이다.)
import { useState, type ReactNode } from "react";
import BottomSheet from "./BottomSheet";
import PrimaryAction from "./PrimaryAction";
import { useToast } from "../ToastContext";
import { MOBILE_LAYOUT, MOBILE_TOUCH, STATE_SURFACES } from "./tokens";

export type DisclosureGroupSummary = {
  /** Q1~Q5 등 질문 번호. */
  qNum: string;
  /** 화면에 쓰는 질문 제목(데스크톱 섹션 헤더와 같은 문자열). */
  title: string;
  /** 이 질문에 걸린 질병 건수(기간 필터 적용 후 — 데스크톱과 같은 배열 길이). */
  count: number;
};

export function DisclosureMobileSummary({
  groups,
  referenceDate,
  windowYears,
  productLabel,
  customerName,
  fileCount,
}: {
  groups: DisclosureGroupSummary[];
  referenceDate?: string;
  windowYears: number;
  productLabel?: string;
  customerName?: string;
  fileCount?: number;
}) {
  const total = groups.reduce((sum, group) => sum + group.count, 0);

  return (
    <section
      data-testid="d-summary"
      className="border border-line bg-white"
      style={{ borderRadius: MOBILE_LAYOUT.radiusCard, padding: MOBILE_LAYOUT.gutter }}
    >
      <h2 className="text-[20px] font-bold leading-[1.35] text-ink-900">
        고지 대상 <span className="text-accent-600">{total}건</span>
      </h2>
      <p className="mt-1 text-[15px] leading-[1.55] text-ink-soft">
        {[
          customerName ? `${customerName} 고객` : null,
          productLabel || null,
          fileCount ? `서류 ${fileCount}건` : null,
          referenceDate ? `기준일 ${referenceDate}` : null,
          `조회기간 ${windowYears}년`,
        ]
          .filter(Boolean)
          .join(" · ")}
      </p>

      {/* 질문별 집계 — ★기간 표기를 접지 않는다(Q별 판정 기간이 곧 고지 의미). */}
      {groups.length > 0 && (
        <ul className="mt-4 flex flex-wrap gap-2" data-testid="d-summary-groups">
          {groups.map((group) => (
            <li
              key={group.title}
              data-q={group.qNum}
              className="inline-flex items-baseline gap-1.5 px-2.5 py-1 text-[15px] leading-[1.4] text-ink-800"
              style={{ background: STATE_SURFACES.warning, borderRadius: MOBILE_LAYOUT.radiusBadge }}
            >
              <span className="font-bold">{group.qNum}</span>
              <span className="font-semibold">{group.count}건</span>
            </li>
          ))}
        </ul>
      )}
      {groups.length === 0 && (
        <p className="mt-4 text-[15px] leading-[1.55] text-ink-soft">선택한 기간에 고지 대상 기록이 없습니다.</p>
      )}
    </section>
  );
}

/**
 * 카톡 문안 시트 + 하단 고정 주 액션.
 *   ★복사 성공 시에만 되돌리기 토스트(scope `copy-done` — 265 허용 3곳 중 하나)를 띄운다.
 *   되돌리기는 클립보드를 이전 내용으로 되돌린다(복사 전 값을 읽어 두었을 때만).
 */
export function DisclosureMobileMemo({ memo, label }: { memo: string; label: string }) {
  const [open, setOpen] = useState(false);
  const [copying, setCopying] = useState(false);
  const { showToast, showUndoToast } = useToast();

  const copy = async () => {
    setCopying(true);
    // 되돌리기용 이전 클립보드 — 읽기 권한이 없으면 조용히 포기한다(복사 자체는 진행).
    let previous: string | null = null;
    try {
      previous = await navigator.clipboard.readText();
    } catch {
      previous = null;
    }
    try {
      await navigator.clipboard.writeText(memo);
      if (previous != null) {
        showUndoToast({
          scope: "copy-done",
          message: "카카오톡 문안을 복사했습니다.",
          onUndo: () => void navigator.clipboard.writeText(previous as string).catch(() => {}),
        });
      } else {
        showToast("복사되었습니다", "success");
      }
      setOpen(false);
    } catch {
      showToast("복사에 실패했습니다. 문안을 길게 눌러 직접 복사해 주세요.", "error");
    } finally {
      setCopying(false);
    }
  };

  return (
    <>
      <BottomSheet
        open={open}
        onClose={() => setOpen(false)}
        title={label}
        description="그대로 복사해 고객에게 보낼 수 있습니다."
        footer={
          <PrimaryAction
            label="문안 복사"
            pending={copying}
            pendingLabel="복사 중…"
            onPress={() => void copy()}
            fixed={false}
          />
        }
      >
        {/* ★문안은 호출부가 만든 문자열 그대로 — 여기서 가공하지 않는다. */}
        <pre
          data-testid="d-memo-text"
          className="whitespace-pre-wrap bg-canvas px-3 py-3 font-sans text-[15px] leading-[1.65] text-ink-800"
          style={{ borderRadius: MOBILE_LAYOUT.radiusBadge }}
        >
          {memo}
        </pre>
      </BottomSheet>

      {/* 하단 고정 주 액션 — 시트가 열려 있을 때는 겹치지 않게 숨긴다. */}
      {!open && (
        <PrimaryAction label="카카오톡 문안 보기" onPress={() => setOpen(true)} hint={null} />
      )}
    </>
  );
}

/**
 * 모바일 셸 — 헤더 요약 + (기존 질병 카드 그대로) + 문안 시트/하단 액션.
 *   하단 고정 액션이 마지막 카드를 가리지 않도록 아래 여백을 둔다.
 */
export default function DisclosureMobileShell({
  groups,
  referenceDate,
  windowYears,
  productLabel,
  customerName,
  fileCount,
  memo,
  memoLabel,
  children,
}: {
  groups: DisclosureGroupSummary[];
  referenceDate?: string;
  windowYears: number;
  productLabel?: string;
  customerName?: string;
  fileCount?: number;
  memo: string;
  memoLabel: string;
  children: ReactNode;
}) {
  return (
    <div data-testid="d-mobile-shell">
      <DisclosureMobileSummary
        groups={groups}
        referenceDate={referenceDate}
        windowYears={windowYears}
        productLabel={productLabel}
        customerName={customerName}
        fileCount={fileCount}
      />
      <div className="mt-4">{children}</div>
      {/* 하단 고정 바(56px) + 안전영역만큼 자리를 비워 둔다. */}
      <div style={{ height: MOBILE_TOUCH.action + 24 }} aria-hidden="true" />
      {memo && <DisclosureMobileMemo memo={memo} label={memoLabel} />}
    </div>
  );
}
