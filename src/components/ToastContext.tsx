/* eslint-disable react-refresh/only-export-components */
// BOHUMFIT-131: 토스트 전역 컨텍스트 + useToast 훅 + ToastProvider(우하단 컨테이너, 최대 3개).
import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { ToastItem, type ToastData, type ToastType } from "./Toast";

type ToastContextValue = { showToast: (message: string, type?: ToastType) => void };

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  // Provider 미장착 환경(테스트 등)에서도 호출부가 죽지 않도록 no-op 폴백.
  return ctx ?? { showToast: () => {} };
}

let _seq = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastData[]>([]);

  const remove = useCallback((id: number) => {
    setToasts((list) => list.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback((message: string, type: ToastType = "info") => {
    setToasts((list) => [...list, { id: ++_seq, type, message }].slice(-3)); // 동시 최대 3개
  }, []);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-[9999] flex w-[min(92vw,360px)] flex-col gap-2">
        {toasts.map((t) => (
          <ToastItem key={t.id} toast={t} onClose={remove} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}
