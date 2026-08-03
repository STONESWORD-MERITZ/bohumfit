// BOHUMFIT-268b — 분석 진행 폴링(순수 로직).
//   ★핵심 계약: ①완료 시 스스로 멈춘다 ②정리 함수로 즉시 멈춘다(누수 0)
//   ③404·네트워크 오류는 조용히 넘어간다(분석 방해 0) ④퍼센트를 만들지 않는다.
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  createJobId,
  POLL_INTERVAL_MS,
  pollAnalysisProgress,
  tickerLine,
  type AnalysisProgress,
} from "./analysisProgress";

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

const snapshot = (over: Partial<AnalysisProgress> = {}): AnalysisProgress => ({
  job_id: "j1",
  total_files: 3,
  done_files: 1,
  files: [{ filename: "a.pdf", records: 10, ftypes: { basic: 10 }, errors: 0 }],
  total_records: 10,
  finished: false,
  failed: false,
  ...over,
});

describe("createJobId", () => {
  it("호출마다 다른 값을 만든다", () => {
    expect(createJobId()).not.toBe(createJobId());
  });

  it("randomUUID가 없어도 폴백으로 만든다", () => {
    vi.stubGlobal("crypto", {});
    expect(createJobId().length).toBeGreaterThan(5);
  });
});

describe("pollAnalysisProgress", () => {
  it("주기적으로 조회하고 결과를 흘린다", async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn<(input: RequestInfo | URL) => Promise<Response>>(
      async () => new Response(JSON.stringify(snapshot()), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const onUpdate = vi.fn();

    const stop = pollAnalysisProgress({ apiBase: "http://x", jobId: "j1", token: "t", onUpdate });
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(onUpdate).toHaveBeenCalledWith(expect.objectContaining({ done_files: 1 }));

    // 인증 헤더가 실린다.
    expect(String(fetchMock.mock.calls[0][0])).toContain("/api/analyze/progress/j1");
    stop();
  });

  it("★finished가 오면 스스로 멈춘다", async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn(async () => new Response(JSON.stringify(snapshot({ finished: true })), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const stop = pollAnalysisProgress({ apiBase: "http://x", jobId: "j1", token: "t", onUpdate: () => {} });
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS * 5);
    expect(fetchMock).toHaveBeenCalledTimes(1); // 더 묻지 않는다
    stop();
  });

  it("★정리 함수를 부르면 즉시 멈춘다(누수 0)", async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn(async () => new Response(JSON.stringify(snapshot()), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const stop = pollAnalysisProgress({ apiBase: "http://x", jobId: "j1", token: "t", onUpdate: () => {} });
    stop();
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS * 5);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("★404여도 조용히 넘어가고 계속 시도한다(분석 방해 0)", async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ detail: "없음" }), { status: 404 }));
    vi.stubGlobal("fetch", fetchMock);
    const onUpdate = vi.fn();

    const stop = pollAnalysisProgress({ apiBase: "http://x", jobId: "j1", token: "t", onUpdate });
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS * 2);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(onUpdate).not.toHaveBeenCalled(); // 화면에 잘못된 값을 흘리지 않는다
    stop();
  });

  it("★네트워크 오류도 삼키고 계속 시도한다", async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn(async () => {
      throw new TypeError("network");
    });
    vi.stubGlobal("fetch", fetchMock);

    const stop = pollAnalysisProgress({ apiBase: "http://x", jobId: "j1", token: "t", onUpdate: () => {} });
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS * 2);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    stop();
  });

  it("정리 후 도착한 응답은 반영하지 않는다", async () => {
    vi.useFakeTimers();
    let resolveFetch: ((r: Response) => void) | null = null;
    vi.stubGlobal(
      "fetch",
      vi.fn(() => new Promise<Response>((res) => { resolveFetch = res; })),
    );
    const onUpdate = vi.fn();

    const stop = pollAnalysisProgress({ apiBase: "http://x", jobId: "j1", token: "t", onUpdate });
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS);
    stop(); // 응답 도착 전에 정리
    const resolve = resolveFetch as ((r: Response) => void) | null;
    resolve?.(new Response(JSON.stringify(snapshot()), { status: 200 }));
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS);
    expect(onUpdate).not.toHaveBeenCalled();
  });
});

describe("tickerLine — ★실제 값만", () => {
  it("유형별 건수를 한국어 라벨로 보여준다", () => {
    expect(tickerLine({ filename: "a.pdf", records: 30, ftypes: { basic: 10, pharma: 20 }, errors: 0 })).toBe(
      "a.pdf — 기본진료 10건 · 처방조제 20건",
    );
  });

  it("유형 정보가 없으면 전체 건수만 쓴다", () => {
    expect(tickerLine({ filename: "b.pdf", records: 1234, ftypes: {}, errors: 0 })).toBe("b.pdf — 1,234건");
  });

  it("★퍼센트를 만들지 않는다", () => {
    const line = tickerLine({ filename: "c.pdf", records: 5, ftypes: { detail: 5 }, errors: 0 });
    expect(line).not.toContain("%");
  });
});
