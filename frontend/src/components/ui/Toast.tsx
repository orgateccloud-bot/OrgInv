import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { Icon, type IconName } from "./icons";

type Tone = "ok" | "warn" | "err" | "info";
type Toast = {
  id: number;
  tone: Tone;
  title: string;
  description?: string;
};
type Ctx = {
  push: (t: Omit<Toast, "id">) => void;
};
const ToastCtx = createContext<Ctx | null>(null);

const ICONS: Record<Tone, IconName> = {
  ok:   "check",
  warn: "alert",
  err:  "x",
  info: "info",
};
const TONE_STYLE: Record<Tone, { color: string; bg: string; border: string }> = {
  ok:   { color: "var(--success)", bg: "var(--success-10)", border: "var(--success-20)" },
  warn: { color: "var(--warning)", bg: "var(--warning-10)", border: "var(--warning-20)" },
  err:  { color: "var(--danger)",  bg: "var(--danger-10)",  border: "var(--danger-20)" },
  info: { color: "var(--info)",    bg: "var(--info-10)",    border: "var(--blue-20)" },
};

let nextId = 1;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const push = useCallback((t: Omit<Toast, "id">) => {
    const id = nextId++;
    setToasts((cur) => [...cur, { id, ...t }]);
    setTimeout(() => {
      setToasts((cur) => cur.filter((x) => x.id !== id));
    }, 4500);
  }, []);

  return (
    <ToastCtx.Provider value={{ push }}>
      {children}
      <div
        aria-live="polite"
        className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 pointer-events-none"
      >
        {toasts.map((t) => {
          const s = TONE_STYLE[t.tone];
          return (
            <div
              key={t.id}
              className="toast pointer-events-auto"
              style={{ borderLeft: `3px solid ${s.color}` }}
              role="status"
            >
              <div
                className="w-7 h-7 rounded-full flex items-center justify-center shrink-0"
                style={{ background: s.bg, color: s.color, border: `1px solid ${s.border}` }}
              >
                <Icon name={ICONS[t.tone]} size={14} strokeWidth={2.5} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-semibold leading-tight" style={{ color: "var(--navy)" }}>
                  {t.title}
                </div>
                {t.description && (
                  <div className="text-xs text-muted mt-0.5">
                    {t.description}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </ToastCtx.Provider>
  );
}

export function useToast(): Ctx {
  const v = useContext(ToastCtx);
  return v ?? { push: () => undefined };
}

export function useToastEffect(
  trigger: unknown,
  build: () => { tone: Tone; title: string; description?: string } | null,
) {
  const { push } = useToast();
  useEffect(() => {
    const t = build();
    if (t) push(t);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trigger]);
}
