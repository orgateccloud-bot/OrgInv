import { useState } from "react";
import { useEspolio } from "../state";
import { Icon } from "./ui/icons";

/**
 * Único componente de auditoria SHA-256, exibido no rodapé.
 * Substitui as 4+ instâncias duplicadas que existiam nas tabs.
 * Mostra o hash da apuração atual (resumo.audit_hash) quando disponível.
 */
export function AuditFooter() {
  const { state } = useEspolio();
  const hash = state.apuracao?.resumo.audit_hash;
  const [copying, setCopying] = useState(false);

  if (!hash) return null;

  const copiar = () => {
    void navigator.clipboard.writeText(hash).then(() => {
      setCopying(true);
      setTimeout(() => setCopying(false), 1800);
    });
  };

  return (
    <div
      className="flex items-center justify-between gap-3 px-4 py-2 mt-6 text-xs"
      style={{
        background: "var(--surface-elev)",
        border: "1px solid var(--border-solid)",
        borderRadius: "var(--r-sm)",
      }}
    >
      <div className="flex items-center gap-2 min-w-0">
        <Icon name="shield" size={12} strokeWidth={2.25} className="text-muted shrink-0" />
        <span className="text-eyebrow shrink-0">SHA-256</span>
        <code
          className="truncate"
          style={{
            fontFamily: "var(--font-mono)",
            color: "var(--muted)",
            fontSize: "0.7rem",
          }}
          title={hash}
        >
          {hash}
        </code>
      </div>
      <button
        type="button"
        onClick={copiar}
        className="shrink-0 px-2 py-1 rounded-sm transition-colors hover:bg-blue-10"
        style={{ color: "var(--muted)" }}
        title="Copiar hash"
        aria-label="Copiar hash de auditoria"
      >
        {copying ? (
          <Icon name="check" size={12} strokeWidth={2.5} />
        ) : (
          <Icon name="documents" size={12} />
        )}
      </button>
    </div>
  );
}
