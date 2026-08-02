// BOHUMFIT-268a — 모바일 업로드 하단 시트(파일 선택 3종 · 동의 · 업로드 진행 실측).
//
//   ★동의는 **각 화면의 기존 게이트를 그대로** 받아 쓴다(조건 신설 0·문구 변경 0).
//     고지 화면은 인라인 체크박스 2종, 보장분석은 ConsentGate로 서로 다르기 때문에
//     이 컴포넌트는 "동의됐는지"와 "동의 UI 자체"를 **호출부에서 받는다**.
//   ★파일 선택은 새 input을 만들지 않고 **호출부의 기존 input을 눌러준다**(`openPicker`).
//     기존 분석 경로(`fileRef.current.files`를 읽는 흐름)를 그대로 살리기 위해서다.
//   ★진행률은 실측 바이트만 — 못 잡으면 퍼센트를 만들지 않고 파일명·개수·용량만 보여준다.
import type { ReactNode } from "react";
import BottomSheet from "./BottomSheet";
import PrimaryAction from "./PrimaryAction";
import { MOBILE_LAYOUT, MOBILE_TOUCH } from "./tokens";
import { formatBytes, type UploadProgress } from "../../lib/uploadWithProgress";

/**
 * 선택 결과 — ★기존 화면이 이미 들고 있는 상태(파일명 목록·총 용량)를 그대로 받는다.
 *   개별 파일 크기를 얻으려면 렌더 중 `fileRef`를 읽어야 하는데 그건 React 규칙 위반이라 하지 않는다.
 */
export type SelectedFilesInfo = { names: string[]; totalBytes: number };

/**
 * 카메라 촬영 항목은 **비활성**이다.
 *   실측(268a Step 1): `/coverage/analyze`는 `.pdf`가 아니면 400을 내고, 고지 `/api/analyze`도
 *   파서가 pdfplumber라 이미지를 파싱하지 못한다. 백엔드를 바꾸는 것은 이 태스크 범위 밖이라
 *   "준비 중"으로 두고 사유를 조사 문서에 남긴다.
 */
export const CAMERA_CAPTURE_ENABLED = false;

function SourceRow({
  title,
  description,
  onPress,
  disabled = false,
  badge,
  testId,
}: {
  title: string;
  description: string;
  onPress?: () => void;
  disabled?: boolean;
  badge?: string;
  testId: string;
}) {
  return (
    <button
      type="button"
      data-testid={testId}
      onClick={onPress}
      disabled={disabled}
      className={`flex w-full items-start gap-3 border-b border-line/60 px-1 py-3 text-left ${
        disabled ? "opacity-50" : ""
      }`}
      style={{ minHeight: MOBILE_TOUCH.tap }}
    >
      <span className="min-w-0 flex-1">
        <span className="flex items-center gap-2">
          <span className="text-[16px] font-bold leading-[1.4] text-ink-900">{title}</span>
          {badge && (
            <span
              className="bg-surface-muted px-2 py-0.5 text-[15px] font-semibold text-ink-soft"
              style={{ borderRadius: MOBILE_LAYOUT.radiusBadge }}
            >
              {badge}
            </span>
          )}
        </span>
        <span className="mt-1 block break-keep text-[15px] leading-[1.55] text-ink-soft">{description}</span>
      </span>
    </button>
  );
}

export default function MobileUploadSheet({
  open,
  onClose,
  title,
  description,
  openPicker,
  selected,
  consentSlot,
  canSubmit,
  onSubmit,
  submitLabel,
  pending = false,
  progress = null,
  maxFileCount,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  /** 호출부의 기존 file input을 연다(새 input을 만들지 않는다). */
  openPicker: () => void;
  selected: SelectedFilesInfo;
  /** ★각 화면의 기존 동의 UI를 그대로 넣는다 — 문구를 여기서 다시 쓰지 않는다. */
  consentSlot: ReactNode;
  /** ★각 화면의 기존 게이트 조건식 결과. */
  canSubmit: boolean;
  onSubmit: () => void;
  submitLabel: string;
  pending?: boolean;
  progress?: UploadProgress | null;
  maxFileCount?: number;
}) {
  const { names, totalBytes } = selected;

  return (
    <BottomSheet
      open={open}
      onClose={onClose}
      title={title}
      description={description}
      footer={
        <PrimaryAction
          label={submitLabel}
          onPress={onSubmit}
          disabled={!canSubmit}
          pending={pending}
          pendingLabel="업로드 중…"
          fixed={false}
        />
      }
    >
      <div>
        <SourceRow
          testId="upload-source-file"
          title="파일에서 선택"
          description={
            maxFileCount && maxFileCount > 1
              ? `기기에 저장된 PDF를 고릅니다(최대 ${maxFileCount}개).`
              : "기기에 저장된 PDF를 고릅니다."
          }
          onPress={openPicker}
        />
        <SourceRow
          testId="upload-source-camera"
          title="카메라로 촬영"
          // ★사유를 화면에서도 숨기지 않는다 — 설계사가 왜 안 되는지 알아야 다른 방법을 찾는다.
          description="현재 분석은 PDF 원본만 읽을 수 있어 사진 파일은 처리하지 못합니다."
          badge="준비 중"
          disabled={!CAMERA_CAPTURE_ENABLED}
        />
        <SourceRow
          testId="upload-source-kakao"
          title="카카오톡에서 받은 파일"
          description="카카오톡에서 파일을 먼저 저장한 뒤, 이 목록에서 선택해 주세요."
          onPress={openPicker}
        />

        {/* 선택 결과 — ★실제 값만(파일명·개수·용량). */}
        {names.length > 0 && (
          <div className="mt-4" data-testid="upload-selected">
            <p className="text-[15px] font-bold leading-[1.55] text-ink-900">
              선택한 파일 {names.length}개 · {formatBytes(totalBytes)}
            </p>
            <ul className="mt-2 space-y-1">
              {names.map((name, index) => (
                <li key={`${name}-${index}`} className="min-w-0 truncate text-[15px] leading-[1.55] text-ink-soft">
                  {name}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* ★기존 동의 UI를 그대로 — 문구·조건을 여기서 다시 만들지 않는다. */}
        <div className="mt-4">{consentSlot}</div>

        {/* 업로드 진행 — 퍼센트를 모르면 만들지 않고 전송량만 보여준다. */}
        {pending && progress && (
          <div className="mt-4" data-testid="upload-progress">
            {progress.percent != null ? (
              <>
                <div className="h-2 w-full overflow-hidden bg-ink-100" style={{ borderRadius: MOBILE_LAYOUT.radiusBadge }}>
                  <div
                    className="h-full bg-accent-600"
                    style={{ width: `${progress.percent}%` }}
                    role="progressbar"
                    aria-valuenow={progress.percent}
                    aria-valuemin={0}
                    aria-valuemax={100}
                  />
                </div>
                <p className="mt-2 text-[15px] leading-[1.55] text-ink-soft">
                  {progress.percent}% · {formatBytes(progress.loaded)} / {formatBytes(progress.total ?? 0)}
                </p>
              </>
            ) : (
              // ★가짜 퍼센트 금지 — 전송된 실제 바이트만 표시한다.
              <p className="text-[15px] leading-[1.55] text-ink-soft">{formatBytes(progress.loaded)} 전송 중…</p>
            )}
          </div>
        )}
      </div>
    </BottomSheet>
  );
}

/* ────────────────────────────────────────────────────────────────
 * ★BOHUMFIT-268b 접합점
 *   업로드(전송) 완료 = 위 `onSubmit`이 반환하는 프라미스가 resolve되는 시점이고,
 *   그 다음부터 **분석 대기**(서버 파싱·AI 판단)가 시작된다. 268b가 추가할 진행 신호
 *   (SSE·폴링·완료 알림)는 **이 경계 이후**를 다루며, 업로드 진행률과 섞지 않는다.
 *   현행 실태와 선택지는 `docs/mobile-analysis-progress-survey.md` 참조.
 * ──────────────────────────────────────────────────────────────── */
