// BOHUMFIT-277(B-F3) — 고지 분석 결과의 **세션 임시 보관** 계약 정본.
//
//   ★왜 모듈로 뽑았나: 이 저장소는 전체 `AnalyzeResult`(고객명·상병코드·기관명·raw parse_errors)를
//     10분간 들고 있는데, 265가 세운 **단일 삭제 지점**(`AuthContext`의 auth 구독) 밖에 있었다.
//     275 B-F3 실측: 저장 레코드에 소유자 id가 없고 복원 시 대조도 없어서
//     **A 분석 → 로그아웃 → 10분 내 B 로그인 → A 결과 복원**이 성립했다.
//     저장·복원·삭제를 한 파일에 모아 두면 삭제 계약에서 다시 빠질 수 없다.
//
//   ★삭제는 두 겹이다: ①`AuthContext` 단일 지점(사용자 id 전이 — 265 선례로 5경로 자동 포섭)
//     ②복원 시점의 소유자 대조(①이 어떤 이유로 못 돌았어도 남의 결과는 절대 복원하지 않는다).
//   ★비로그인 상태에서는 아예 읽지 않고 지운다.

/** 저장 키 — 138이 쓰던 키를 그대로 유지한다(기존 세션 호환). */
export const SESSION_RESULT_KEY = "bohumfit_result";

/** BOHUMFIT-138(항목7): 10분 재보기. */
export const SESSION_RESULT_TTL_MS = 10 * 60 * 1000;

type StoredRecord<T> = {
  result: T;
  ts: number;
  /** ★소유자 — 이 필드가 없던 것이 B-F3의 원인이다. */
  uid?: string | null;
};

function storage(): Storage | null {
  try {
    if (typeof sessionStorage === "undefined") return null;
    return sessionStorage;
  } catch {
    return null; // 프라이빗 모드 등에서 접근 자체가 던질 수 있다.
  }
}

/** 어떤 이유로든 조용히 실패한다 — 저장 실패가 분석 흐름을 막지 않는다. */
export function clearSessionResult(): void {
  try {
    storage()?.removeItem(SESSION_RESULT_KEY);
  } catch {
    /* 무시 */
  }
}

export function saveSessionResult<T>(result: T, userId: string | null | undefined, now: number): void {
  try {
    const store = storage();
    if (!store) return;
    // ★비로그인 상태에서는 저장하지 않는다(주인이 없는 건강정보를 남기지 않는다).
    if (!userId) {
      clearSessionResult();
      return;
    }
    const record: StoredRecord<T> = { result, ts: now, uid: userId };
    store.setItem(SESSION_RESULT_KEY, JSON.stringify(record));
  } catch {
    /* 저장소 비활성·용량 초과 — 무시 */
  }
}

export type RestoredSessionResult<T> = { result: T; ts: number };

/**
 * 현재 사용자의 결과만 돌려준다.
 *   ★다음 중 하나라도 해당하면 **읽지 않고 삭제**한다: 비로그인 / 소유자 불일치 /
 *     소유자 미기록(277 이전 레코드) / TTL 초과 / 파싱 실패.
 */
export function readSessionResult<T>(
  userId: string | null | undefined,
  now: number,
): RestoredSessionResult<T> | null {
  try {
    const store = storage();
    if (!store) return null;
    const raw = store.getItem(SESSION_RESULT_KEY);
    if (!raw) return null;
    if (!userId) {
      // 비로그인 진입 — 남의 것일 수 있으므로 즉시 폐기한다.
      clearSessionResult();
      return null;
    }
    const saved = JSON.parse(raw) as StoredRecord<T> | null;
    if (!saved || typeof saved.ts !== "number") {
      clearSessionResult();
      return null;
    }
    // ★소유자 대조 — 277 이전에 저장된 uid 없는 레코드도 여기서 폐기된다.
    if (!saved.uid || saved.uid !== userId) {
      clearSessionResult();
      return null;
    }
    if (now - saved.ts >= SESSION_RESULT_TTL_MS) {
      clearSessionResult();
      return null;
    }
    return { result: saved.result, ts: saved.ts };
  } catch {
    clearSessionResult();
    return null;
  }
}
