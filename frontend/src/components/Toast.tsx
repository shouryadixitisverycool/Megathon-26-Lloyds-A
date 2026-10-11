import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { CheckCircle2, Copy, Info, OctagonX, X } from "lucide-react";

interface Toast { id: number; kind: "success" | "error" | "info"; title: string; detail?: string; auditId?: string }

const ToastContext = createContext<(toast: Omit<Toast, "id">) => void>(() => {});

export function useToast() {
  return useContext(ToastContext);
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const dismiss = useCallback((id: number) => setToasts((items) => items.filter((item) => item.id !== id)), []);
  const push = useCallback((toast: Omit<Toast, "id">) => {
    const id = Date.now() + Math.random();
    setToasts((items) => [...items.slice(-2), { ...toast, id }]);
    window.setTimeout(() => dismiss(id), toast.kind === "error" ? 9000 : 6000);
  }, [dismiss]);

  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="toasts" aria-live="polite" aria-atomic="false">
        {toasts.map((toast) => {
          const Icon = toast.kind === "success" ? CheckCircle2 : toast.kind === "info" ? Info : OctagonX;
          return (
            <div key={toast.id} className="toast" data-kind={toast.kind} role={toast.kind === "error" ? "alert" : "status"}>
              <Icon className="lead" size={18} aria-hidden="true" />
              <div>
                <b>{toast.title}</b>
                {toast.detail && <small>{toast.detail}</small>}
                {toast.auditId && (
                  <small className="row" style={{ gap: 6 }}>
                    Audit event <code>{toast.auditId}</code>
                    <button type="button" className="btn-quiet btn btn-sm" aria-label="Copy audit event ID"
                      onClick={() => navigator.clipboard?.writeText(toast.auditId!)}>
                      <Copy size={12} aria-hidden="true" /> Copy
                    </button>
                  </small>
                )}
              </div>
              <button type="button" className="icon-btn" style={{ width: 28, height: 28 }} onClick={() => dismiss(toast.id)} aria-label="Dismiss">
                <X size={16} aria-hidden="true" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}
