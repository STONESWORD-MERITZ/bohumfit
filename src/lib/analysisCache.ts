// BOHUMFIT-265 — 오프라인 열람용 분석 결과 캐시(★Human 확정 A안).
//
//   정책(요약):
//     · 최근 분석 **5건**만 보관(초과분은 저장 시각 오래된 것부터 제거)
//     · **24시간 자동 만료** — 읽을 때마다 만료분을 지우고, 만료된 항목은 없는 것으로 취급
//     · **로그아웃/계정 전환 시 전량 삭제**(`clearAnalysisCache()`), 다른 사용자 캐시 열람 0
//     · **로그인 상태에서만** 저장·조회(비로그인은 무조건 빈 결과)
//
//   저장 방식: **IndexedDB**(실측 판단).
//     - localStorage는 5MB 안팎 문자열 한계 + 동기 blocking이라 분석 결과 5건에 부적합.
//     - Cache Storage는 264의 `bohumfit-shell-*`(앱 셸)과 같은 저장소를 공유해 정리 규칙이 얽힌다.
//       264의 `isCacheableRequest()`는 `/api/`·`/coverage/`·`/analyze` 응답을 **전면 차단**하고 있고,
//       그 계약을 그대로 두기 위해 분석 결과는 ★별도 IndexedDB 스토어에 앱이 직접 넣는다(SW 무관).
//
//   ★서버 전송 0 — 이 파일은 기기 로컬 저장만 다룬다.

const DB_NAME = "bohumfit-offline";
const DB_VERSION = 1;
const STORE = "analyses";

/** 최근 N건만 보관. */
export const MAX_ENTRIES = 5;
/** 24시간 만료. */
export const TTL_MS = 24 * 60 * 60 * 1000;

export type CachedAnalysis = {
  /** 분석 식별자(같은 분석을 다시 저장하면 덮어쓴다). */
  id: string;
  /** 소유자 — 로그아웃/계정 전환 시 전량 삭제하지만, 조회 때도 한 번 더 대조한다. */
  userId: string;
  /** 저장 시각(ms). 만료·정렬 기준. */
  savedAt: number;
  /** 목록 표기용 라벨(고객 실명 금지 — 호출부가 마스킹해서 넣는다). */
  label: string;
  /** 화면 재구성에 필요한 분석 결과 payload. */
  payload: unknown;
};

function idbAvailable(): boolean {
  return typeof indexedDB !== "undefined";
}

function openDb(): Promise<IDBDatabase | null> {
  if (!idbAvailable()) return Promise.resolve(null);
  return new Promise((resolve) => {
    let req: IDBOpenDBRequest;
    try {
      req = indexedDB.open(DB_NAME, DB_VERSION);
    } catch {
      resolve(null); // 프라이빗 모드 등 — 캐시는 선택 기능이라 조용히 비활성.
      return;
    }
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE)) {
        const store = db.createObjectStore(STORE, { keyPath: "id" });
        store.createIndex("savedAt", "savedAt");
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => resolve(null);
  });
}

function tx<T>(db: IDBDatabase, mode: IDBTransactionMode, run: (store: IDBObjectStore) => IDBRequest<T>): Promise<T | null> {
  return new Promise((resolve) => {
    try {
      const t = db.transaction(STORE, mode);
      const req = run(t.objectStore(STORE));
      req.onsuccess = () => resolve(req.result as T);
      req.onerror = () => resolve(null);
    } catch {
      resolve(null);
    }
  });
}

/** 만료·소유자 판정(순수) — 테스트가 직접 단언한다. */
export function isEntryValid(entry: CachedAnalysis, userId: string, now: number = Date.now()): boolean {
  if (!entry || entry.userId !== userId) return false;
  return now - entry.savedAt < TTL_MS;
}

/** 보관 상한 적용(순수) — 최신 MAX_ENTRIES건만 남긴다. */
export function pickRetained(entries: CachedAnalysis[]): CachedAnalysis[] {
  return [...entries].sort((a, b) => b.savedAt - a.savedAt).slice(0, MAX_ENTRIES);
}

async function readAll(db: IDBDatabase): Promise<CachedAnalysis[]> {
  const rows = await tx<CachedAnalysis[]>(db, "readonly", (store) => store.getAll() as IDBRequest<CachedAnalysis[]>);
  return Array.isArray(rows) ? rows : [];
}

/**
 * 저장 — ★로그인 상태(userId)에서만. 저장 후 만료분 제거 + 상한 정리를 함께 수행한다.
 *  실패는 조용히 무시(오프라인 열람은 부가 기능이라 본 동선을 막지 않는다).
 */
export async function saveAnalysis(
  entry: Omit<CachedAnalysis, "savedAt"> & { savedAt?: number },
  now: number = Date.now()
): Promise<boolean> {
  if (!entry.userId) return false; // ★비로그인 저장 금지
  const db = await openDb();
  if (!db) return false;
  const record: CachedAnalysis = { ...entry, savedAt: entry.savedAt ?? now };
  await tx(db, "readwrite", (store) => store.put(record));

  // 만료·상한 정리
  const rows = await readAll(db);
  const alive = rows.filter((r) => isEntryValid(r, r.userId, now));
  const retainedIds = new Set(pickRetained(alive.filter((r) => r.userId === entry.userId)).map((r) => r.id));
  const dropIds = rows
    .filter((r) => (r.userId === entry.userId ? !retainedIds.has(r.id) : !isEntryValid(r, r.userId, now)))
    .map((r) => r.id);
  for (const id of dropIds) await tx(db, "readwrite", (store) => store.delete(id));
  db.close();
  return true;
}

/**
 * 목록 조회 — ★로그인 상태에서만. 만료분은 반환하지 않고 즉시 삭제한다.
 *  비로그인(userId 없음)이면 저장소를 열지 않고 빈 배열을 돌려준다(노출 0).
 */
export async function listAnalyses(userId: string | null | undefined, now: number = Date.now()): Promise<CachedAnalysis[]> {
  if (!userId) return []; // ★비로그인 차단
  const db = await openDb();
  if (!db) return [];
  const rows = await readAll(db);
  const expired = rows.filter((r) => !isEntryValid(r, r.userId, now));
  for (const r of expired) await tx(db, "readwrite", (store) => store.delete(r.id));
  const mine = rows.filter((r) => isEntryValid(r, userId, now));
  db.close();
  return pickRetained(mine);
}

/** 단건 조회 — 만료·타 사용자 항목은 null. */
export async function getAnalysis(
  id: string,
  userId: string | null | undefined,
  now: number = Date.now()
): Promise<CachedAnalysis | null> {
  if (!userId) return null;
  const list = await listAnalyses(userId, now);
  return list.find((r) => r.id === id) ?? null;
}

/**
 * 전량 삭제 — ★로그아웃·계정 전환 시 호출한다(AuthContext.signOut).
 *  스토어 자체를 비우므로 다른 사용자의 잔재도 남지 않는다.
 */
export async function clearAnalysisCache(): Promise<void> {
  const db = await openDb();
  if (!db) return;
  await tx(db, "readwrite", (store) => store.clear());
  db.close();
}
