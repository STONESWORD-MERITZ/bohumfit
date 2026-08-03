// BOHUMFIT-268b — 분석 진행 폴링(순수 로직).
//
//   ★분석 자체와 완전히 분리된 **부가 기능**이다. 폴링이 실패하든 404가 나든
//     분석은 그대로 진행되고, 화면은 티커만 조용히 감춘다.
//   ★퍼센트를 만들지 않는다 — "N개 중 M개 완료"는 서버가 준 실제 값이라 그대로 쓴다.

export type ProgressFile = {
  filename: string;
  records: number;
  ftypes: Record<string, number>;
  errors: number;
};

export type AnalysisProgress = {
  job_id: string;
  total_files: number;
  /** 완료된 파일 수 — ★파일 순서가 아니라 완료 순서로 쌓인다(병렬 파싱). */
  done_files: number;
  files: ProgressFile[];
  total_records: number;
  finished: boolean;
  failed: boolean;
};

/** 작업 ID — 서버는 이 값을 소유자와 함께 저장한다(추측 방지를 위해 UUID). */
export function createJobId(): string {
  try {
    if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") return crypto.randomUUID();
  } catch {
    /* 아래 폴백 */
  }
  // randomUUID가 없는 환경(구형·비보안 컨텍스트) 폴백.
  return `job-${Math.random().toString(36).slice(2)}${Date.now().toString(36)}`;
}

/** 폴링 간격(ms) — 1.5초. 서버 rate limit(120/분)에 여유가 있다. */
export const POLL_INTERVAL_MS = 1500;

export type PollOptions = {
  apiBase: string;
  jobId: string;
  token: string;
  onUpdate: (progress: AnalysisProgress) => void;
  /** 테스트에서 주입 가능(기본 window.setInterval). */
  intervalMs?: number;
};

/**
 * 진행 폴링을 시작하고 **정리 함수**를 돌려준다.
 *   ★호출부는 분석 완료·에러·언마운트 어느 경우에도 이 함수를 반드시 부른다(누수 방지).
 *   서버가 `finished`를 주면 스스로도 멈춘다.
 */
export function pollAnalysisProgress({
  apiBase,
  jobId,
  token,
  onUpdate,
  intervalMs = POLL_INTERVAL_MS,
}: PollOptions): () => void {
  let stopped = false;
  let timer: ReturnType<typeof setTimeout> | null = null;

  const stop = () => {
    stopped = true;
    if (timer !== null) {
      clearTimeout(timer);
      timer = null;
    }
  };

  const tick = async () => {
    if (stopped) return;
    try {
      const response = await fetch(`${apiBase}/api/analyze/progress/${encodeURIComponent(jobId)}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = (await response.json()) as AnalysisProgress;
        if (!stopped) {
          onUpdate(data);
          // 서버가 끝났다고 하면 더 물어보지 않는다.
          if (data.finished) {
            stop();
            return;
          }
        }
      }
      // ★404·403·5xx는 조용히 넘어간다 — 아직 등록 전이거나 이미 만료된 것뿐이고,
      //   분석 자체와는 무관하다. 재시도가 분석을 방해하지 않도록 간격도 그대로 둔다.
    } catch {
      // 네트워크 오류도 마찬가지 — 티커만 갱신되지 않는다.
    }
    if (!stopped) timer = setTimeout(() => void tick(), intervalMs);
  };

  timer = setTimeout(() => void tick(), intervalMs);
  return stop;
}

/** 티커 한 줄 문구 — ★서버가 준 실제 값만 쓴다(추정·퍼센트 금지). */
export function tickerLine(file: ProgressFile): string {
  const kinds: Record<string, string> = { basic: "기본진료", detail: "세부진료", pharma: "처방조제" };
  const parts = Object.entries(file.ftypes || {})
    .filter(([, count]) => count > 0)
    .map(([kind, count]) => `${kinds[kind] || kind} ${count.toLocaleString("ko-KR")}건`);
  const detail = parts.length > 0 ? parts.join(" · ") : `${file.records.toLocaleString("ko-KR")}건`;
  return `${file.filename} — ${detail}`;
}
