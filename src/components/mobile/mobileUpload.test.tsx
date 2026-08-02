/// <reference types="node" />
// BOHUMFIT-268a — 모바일 업로드 시트 + 업로드 진행률 실측 유틸.
//   ★핵심 계약: ①동의 UI·조건식은 호출부 것을 그대로 쓴다 ②카메라 항목은 비활성(사유 노출)
//   ③진행률은 실측 바이트만 — `lengthComputable`이 아니면 **퍼센트를 만들지 않는다**.
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import MobileUploadSheet, { CAMERA_CAPTURE_ENABLED } from "./MobileUploadSheet";
import { formatBytes, uploadWithProgress, UploadError, type UploadProgress } from "../../lib/uploadWithProgress";
import { MOBILE_TOUCH } from "./tokens";

afterEach(() => {
  if (screen.queryByRole("dialog")) {
    expect(document.body.style.overflow).toBe("hidden");
    expect(document.body.style.position).toBe("fixed");
    expect(document.documentElement.style.overflow).toBe("hidden");
  }
  cleanup();
  expect(document.body.style.overflow).not.toBe("hidden");
  expect(document.body.style.position).not.toBe("fixed");
  expect(document.documentElement.style.overflow).not.toBe("hidden");
});

const baseProps = {
  open: true,
  onClose: () => {},
  title: "진료자료 올리기",
  openPicker: () => {},
  selected: { names: [], totalBytes: 0 },
  consentSlot: <label data-testid="consent-slot">동의 문구(호출부 것)</label>,
  canSubmit: false,
  onSubmit: () => {},
  submitLabel: "AI 고지 리스크 점검",
};

describe("업로드 시트 — 파일 선택 3종", () => {
  it("파일에서 선택·카카오톡 항목은 호출부의 기존 피커를 연다", () => {
    const openPicker = vi.fn();
    render(<MobileUploadSheet {...baseProps} openPicker={openPicker} />);

    fireEvent.click(screen.getByTestId("upload-source-file"));
    expect(openPicker).toHaveBeenCalledTimes(1);
    // ★카카오톡은 별도 API 없이 같은 피커를 연다(안내 문구만 다르다).
    fireEvent.click(screen.getByTestId("upload-source-kakao"));
    expect(openPicker).toHaveBeenCalledTimes(2);
    expect(screen.getByTestId("upload-source-kakao").textContent).toContain("파일을 먼저 저장한 뒤");
  });

  it("★카메라 항목은 비활성이고 사유를 화면에 밝힌다(백엔드가 PDF만 받는다)", () => {
    render(<MobileUploadSheet {...baseProps} />);
    const camera = screen.getByTestId("upload-source-camera") as HTMLButtonElement;
    expect(CAMERA_CAPTURE_ENABLED).toBe(false);
    expect(camera.disabled).toBe(true);
    expect(camera.textContent).toContain("준비 중");
    expect(camera.textContent).toContain("PDF 원본만");
  });

  it("터치 타깃 44px·주 액션 56px을 지킨다", () => {
    render(<MobileUploadSheet {...baseProps} />);
    expect((screen.getByTestId("upload-source-file") as HTMLElement).style.minHeight).toBe(`${MOBILE_TOUCH.tap}px`);
    const submit = screen.getByRole("button", { name: "AI 고지 리스크 점검" });
    expect(submit.style.minHeight).toBe(`${MOBILE_TOUCH.action}px`);
  });
});

describe("동의 — 호출부 것을 그대로 쓴다", () => {
  it("consentSlot을 그대로 렌더한다(문구를 다시 만들지 않는다)", () => {
    render(<MobileUploadSheet {...baseProps} />);
    expect(screen.getByTestId("consent-slot").textContent).toBe("동의 문구(호출부 것)");
  });

  it("★canSubmit이 false면 주 액션이 비활성이다(조건식은 호출부가 판단)", () => {
    const onSubmit = vi.fn();
    render(<MobileUploadSheet {...baseProps} canSubmit={false} onSubmit={onSubmit} />);
    const submit = screen.getByRole("button", { name: "AI 고지 리스크 점검" }) as HTMLButtonElement;
    expect(submit.disabled).toBe(true);
    fireEvent.click(submit);
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("canSubmit이 true면 눌러서 업로드를 시작한다", () => {
    const onSubmit = vi.fn();
    render(<MobileUploadSheet {...baseProps} canSubmit onSubmit={onSubmit} />);
    fireEvent.click(screen.getByRole("button", { name: "AI 고지 리스크 점검" }));
    expect(onSubmit).toHaveBeenCalledTimes(1);
  });
});

describe("선택 결과·진행 표시 — ★실제 값만", () => {
  it("파일명·개수·총 용량을 그대로 보여준다", () => {
    render(
      <MobileUploadSheet
        {...baseProps}
        selected={{ names: ["2024진료.pdf", "2023진료.pdf"], totalBytes: 3_500_000 }}
      />,
    );
    const box = screen.getByTestId("upload-selected");
    expect(box.textContent).toContain("선택한 파일 2개");
    expect(box.textContent).toContain(formatBytes(3_500_000));
    expect(box.textContent).toContain("2024진료.pdf");
  });

  it("퍼센트를 알 때는 진행 바를 보여준다", () => {
    const progress: UploadProgress = { loaded: 500_000, total: 1_000_000, percent: 50 };
    render(<MobileUploadSheet {...baseProps} pending progress={progress} />);
    const bar = screen.getByRole("progressbar");
    expect(bar.getAttribute("aria-valuenow")).toBe("50");
    expect(screen.getByTestId("upload-progress").textContent).toContain("50%");
  });

  it("★퍼센트를 모를 때는 가짜 퍼센트를 만들지 않고 전송량만 보여준다", () => {
    const progress: UploadProgress = { loaded: 123_456, total: null, percent: null };
    render(<MobileUploadSheet {...baseProps} pending progress={progress} />);
    expect(screen.queryByRole("progressbar")).toBeNull();
    const box = screen.getByTestId("upload-progress");
    expect(box.textContent).toContain(formatBytes(123_456));
    expect(box.textContent).not.toContain("%");
  });
});

describe("uploadWithProgress — 진행률·오류 규약", () => {
  class MockXHR {
    static instances: MockXHR[] = [];
    upload: { onprogress: ((e: ProgressEvent) => void) | null } = { onprogress: null };
    onload: (() => void) | null = null;
    onerror: (() => void) | null = null;
    ontimeout: (() => void) | null = null;
    onabort: (() => void) | null = null;
    status = 200;
    responseText = "{}";
    headers: Record<string, string> = {};
    constructor() {
      MockXHR.instances.push(this);
    }
    open() {}
    setRequestHeader(key: string, value: string) {
      this.headers[key] = value;
    }
    send() {}
    abort() {
      this.onabort?.();
    }
  }

  const withMockXHR = () => {
    MockXHR.instances = [];
    vi.stubGlobal("XMLHttpRequest", MockXHR as unknown as typeof XMLHttpRequest);
    return () => MockXHR.instances[0];
  };

  afterEach(() => vi.unstubAllGlobals());

  it("전송 진행률을 실측 바이트로 전달하고 응답 JSON을 돌려준다", async () => {
    const getXhr = withMockXHR();
    const onProgress = vi.fn();
    const promise = uploadWithProgress<{ ok: boolean }>({
      url: "/api/analyze",
      body: new FormData(),
      headers: { Authorization: "Bearer t" },
      onProgress,
    });

    const xhr = getXhr();
    expect((xhr as unknown as XMLHttpRequest).timeout).toBe(350_000);
    expect(xhr.headers.Authorization).toBe("Bearer t");
    // ★Content-Type을 직접 넣지 않는다(FormData 경계는 브라우저가 붙인다).
    expect(xhr.headers["Content-Type"]).toBeUndefined();

    xhr.upload.onprogress?.({ lengthComputable: true, loaded: 50, total: 200 } as ProgressEvent);
    expect(onProgress).toHaveBeenCalledWith({ loaded: 50, total: 200, percent: 25 });

    // ★lengthComputable이 false면 퍼센트를 만들지 않는다.
    xhr.upload.onprogress?.({ lengthComputable: false, loaded: 80, total: 0 } as ProgressEvent);
    expect(onProgress).toHaveBeenLastCalledWith({ loaded: 80, total: null, percent: null });

    xhr.responseText = JSON.stringify({ ok: true });
    xhr.onload?.();
    await expect(promise).resolves.toEqual({ ok: true });
  });

  it("★오류 메시지 규약이 기존 fetch 경로와 같다(응답 detail 우선)", async () => {
    const getXhr = withMockXHR();
    const promise = uploadWithProgress({ url: "/api/analyze", body: new FormData() });
    const xhr = getXhr();
    xhr.status = 402;
    xhr.responseText = JSON.stringify({ detail: "무료 분석 5회를 모두 사용했습니다." });
    xhr.onload?.();

    await expect(promise).rejects.toThrow("무료 분석 5회를 모두 사용했습니다.");
    await promise.catch((error) => {
      expect(error).toBeInstanceOf(UploadError);
      expect((error as UploadError).status).toBe(402); // 402 전환 처리에 필요
    });
  });

  it("detail이 없으면 기본 메시지를 쓴다", async () => {
    const getXhr = withMockXHR();
    const promise = uploadWithProgress({ url: "/api/analyze", body: new FormData() });
    const xhr = getXhr();
    xhr.status = 500;
    xhr.responseText = "<html>500</html>";
    xhr.onload?.();
    await expect(promise).rejects.toThrow("업로드에 실패했습니다.");
  });

  it("네트워크 오류를 UploadError로 감싼다", async () => {
    const getXhr = withMockXHR();
    const promise = uploadWithProgress({ url: "/api/analyze", body: new FormData() });
    getXhr().onerror?.();
    await expect(promise).rejects.toThrow("네트워크 오류");
  });
});

describe("formatBytes", () => {
  it("실제 값만 표기한다", () => {
    expect(formatBytes(512)).toBe("512B");
    expect(formatBytes(2048)).toBe("2KB");
    expect(formatBytes(3_500_000)).toBe("3.3MB");
  });
});
