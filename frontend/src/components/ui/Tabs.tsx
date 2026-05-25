import { useState } from "react";

export type TabDef = {
  id: string;
  label: string;
  icon?: React.ReactNode;
  badge?: React.ReactNode;
  render: () => React.ReactNode;
};

export function Tabs({
  tabs,
  initial,
  active,
  onChange,
}: {
  tabs: TabDef[];
  initial?: string;
  active?: string;
  onChange?: (id: string) => void;
}) {
  const [internal, setInternal] = useState(initial ?? tabs[0]?.id ?? "");
  const cur = active ?? internal;
  const setCur = (id: string) => {
    if (active === undefined) setInternal(id);
    onChange?.(id);
  };
  const found = tabs.find((t) => t.id === cur) ?? tabs[0];

  return (
    <div className="flex flex-col gap-5">
      {/* Tab bar — Aurora glass */}
      <div
        className="rounded-md p-1 flex gap-0.5 overflow-x-auto"
        style={{
          background: "var(--glass-bg)",
          border: "1px solid var(--border-solid)",
          backdropFilter: "var(--glass-blur-sm)",
          WebkitBackdropFilter: "var(--glass-blur-sm)",
          boxShadow: "var(--shadow-sm)",
        }}
        role="tablist"
        aria-label="Seções do espólio"
      >
        {tabs.map((t) => {
          const isActive = t.id === cur;
          return (
            <button
              key={t.id}
              role="tab"
              aria-selected={isActive}
              onClick={() => setCur(t.id)}
              className="flex items-center gap-2 whitespace-nowrap px-4 py-2 rounded-sm transition-all duration-200 outline-none"
              style={
                isActive
                  ? {
                      background: "var(--blue)",
                      color: "#FFFFFF",
                      boxShadow: "var(--shadow-cta)",
                      fontWeight: 600,
                      fontSize: "0.85rem",
                    }
                  : {
                      color: "var(--muted)",
                      background: "transparent",
                      fontWeight: 500,
                      fontSize: "0.85rem",
                    }
              }
            >
              {t.icon && (
                <span
                  className="flex items-center justify-center"
                  style={{
                    opacity: isActive ? 1 : 0.85,
                    transition: "all 0.2s",
                  }}
                  aria-hidden
                >
                  {t.icon}
                </span>
              )}
              <span>{t.label}</span>
              {t.badge}
            </button>
          );
        })}
      </div>

      {/* Tab panel */}
      <div role="tabpanel" className="flex flex-col gap-4 fade-in">
        {found?.render()}
      </div>
    </div>
  );
}
