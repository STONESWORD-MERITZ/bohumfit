// BOHUMFIT-268a — 업로드 진행률 실측 유틸.
//
//   ★가짜 퍼센트를 만들지 않는다. `fetch`로는 요청 본문 전송 진행률을 알 수 없어 XHR을 쓰되,
//     **요청 헤더·엔드포인트·에러 처리 계약은 현행 fetch 경로와 동일**하게 유지한다
//     (실패 시 응답 JSON의 `detail`을 그대로 메시지로 쓰는 것까지 같다).
//   ★`lengthComputable`이 false인 환경에서는 퍼센트를 만들지 않고 `null`을 흘린다 — 호출부는
//     그 경우 파일명·개수·용량 같은 **실제 값만** 보여준다.

export type UploadProgress = {
  /** 전송된 바이트. */
  loaded: number;
  /** 전체 바이트 — 브라우저가 계산할 수 없으면 null. */
  total: number | null;
  /** 0~100 — total을 모르면 null(★추정치를 만들지 않는다). */
  percent: number | null;
};

export type UploadOptions = {
  url: string;
  body: FormData;
  /** Authorization 등 — 현행 fetch 경로가 보내던 것과 같은 값을 그대로 넘긴다. */
  headers?: Record<string, string>;
  onProgress?: (progress: UploadProgress) => void;
  /** 취소용(선택). */
  signal?: AbortSignal;
};

/** 현행 fetch 경로와 같은 오류 메시지 규약: 응답 JSON의 `detail`이 있으면 그것, 없으면 fallback. */
export class UploadError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "UploadError";
    this.status = status;
  }
}

/**
 * XHR 업로드 — 성공 시 응답 본문을 JSON으로 파싱해 돌려준다.
 *   ★분석 파이프라인·엔드포인트는 건드리지 않는다. 전송 계층만 바꾼 것이다.
 */
export function uploadWithProgress<T = unknown>({
  url,
  body,
  headers = {},
  onProgress,
  signal,
}: UploadOptions): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", url);
    xhr.timeout = 350_000; // 데스크톱 fetch의 AbortSignal.timeout과 동일 — 무한 대기/스피너 방지.
    // ★Content-Type은 지정하지 않는다 — FormData 경계(boundary)를 브라우저가 붙여야 한다.
    for (const [key, value] of Object.entries(headers)) xhr.setRequestHeader(key, value);

    if (xhr.upload && onProgress) {
      xhr.upload.onprogress = (event) => {
        const total = event.lengthComputable ? event.total : null;
        onProgress({
          loaded: event.loaded,
          total,
          // ★lengthComputable이 아니면 퍼센트를 만들지 않는다.
          percent: total && total > 0 ? Math.min(100, Math.round((event.loaded / total) * 100)) : null,
        });
      };
    }

    const parseDetail = (fallback: string): string => {
      try {
        const payload = JSON.parse(xhr.responseText) as { detail?: string };
        return payload.detail || fallback;
      } catch {
        return fallback;
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as T);
        } catch {
          reject(new UploadError("서버 응답을 읽지 못했습니다.", xhr.status));
        }
        return;
      }
      reject(new UploadError(parseDetail("업로드에 실패했습니다."), xhr.status));
    };
    xhr.onerror = () => reject(new UploadError("네트워크 오류로 업로드하지 못했습니다.", 0));
    xhr.ontimeout = () => reject(new UploadError("업로드 시간이 초과되었습니다.", 0));
    xhr.onabort = () => reject(new UploadError("업로드를 취소했습니다.", 0));

    if (signal) {
      if (signal.aborted) {
        xhr.abort();
        return;
      }
      signal.addEventListener("abort", () => xhr.abort(), { once: true });
    }

    xhr.send(body);
  });
}

/** 사람이 읽는 용량 표기(실제 바이트만 — 추정 없음). */
export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}
