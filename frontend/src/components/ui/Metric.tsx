import type { ReactNode } from "react";

const TONE_COLOR: Record<string, string> = {
  default: "var(--navy)",
  ok:      "var(--success)",
  warn:    "var(--warning)",
  err:     "var(--danger)",
};

const TONE_ACCENT: Record<string, string> = {
  default: "var(--blue)",
  ok:      "var(--success)",
  warn:    "var(--warning)",
  err:     "var(--danger)",
};

export function Metric({
  label,
  value,
  hint,
  tone = "default",
  serif = false,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: "default" | "ok" | "warn" | "err";
  serif?: boolean;
}) {
  return (
    <div
      className="card p-4 flex flex-col gap-1.5 relative overflow-hidden"
      style={{
        borderTop: `2px solid ${TONE_ACCENT[tone] ?? TONE_ACCENT.default}`,
      }}
    >
      <div className="metric-label">{label}</div>
      <div
        className="metric-value"
        style={{
          color: TONE_COLOR[tone] ?? TONE_COLOR.default,
          fontFamily: serif ? "var(--font-serif)" : undefined,
          fontStyle: serif ? "italic" : undefined,
          fontWeight: serif ? 400 : 800,
          fontSize: serif ? "2.1rem" : undefined,
        }}
      >
        {value}
      </div>
      {hint && <div className="text-xs text-muted">{hint}</div>}
    </div>
  );
}
