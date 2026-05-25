import { Logo } from "./Logo";
import { SupabaseBadge } from "./SupabaseBadge";
import { useEspolio } from "../state";
import { Icon } from "./ui/icons";
import { useState } from "react";
import { useToast } from "./ui/Toast";
import { isSupabaseEnabled, getSupabase } from "../lib/supabase";
import { salvarEspolio } from "../lib/espolioRepo";

export function Header() {
  const {
    state,
    novo,
    reset,
    setAuthModalOpen,
    setAbrirModalOpen,
    setEspolio,
  } = useEspolio();
  const [saving, setSaving] = useState(false);
  const toast = useToast();

  const e = state.espolio;

  const checkAuth = async (): Promise<boolean> => {
    if (!isSupabaseEnabled()) {
      toast.push({
        tone: "info",
        title: "Modo local",
        description: "Supabase não está configurado.",
      });
      return false;
    }
    const sb = getSupabase();
    if (!sb) return false;
    const { data: { session } } = await sb.auth.getSession();
    if (!session?.user) {
      toast.push({ tone: "warn", title: "Login necessário" });
      setAuthModalOpen(true);
      return false;
    }
    return true;
  };

  const onSalvar = async () => {
    if (!e) return;
    if (!(await checkAuth())) return;
    if (!e.nome) {
      toast.push({ tone: "warn", title: "Nome obrigatório", description: "Preencha o nome do espólio antes de salvar." });
      return;
    }
    setSaving(true);
    try {
      const id = await salvarEspolio(e, state.activeEspolioId || undefined);
      setEspolio(e, id);
      toast.push({ tone: "ok", title: "Salvo na nuvem", description: e.nome });
    } catch (err) {
      toast.push({ tone: "err", title: "Falha ao salvar", description: err instanceof Error ? err.message : String(err) });
    } finally {
      setSaving(false);
    }
  };

  const onAbrir = async () => {
    if (await checkAuth()) setAbrirModalOpen(true);
  };

  return (
    <header
      className="shrink-0 relative"
      style={{
        background: "var(--surface-elev)",
        borderBottom: "1px solid var(--border-solid)",
        height: 52,
      }}
    >
      <div className="h-full px-5 flex items-center gap-4">
        {/* Brand */}
        <div className="flex items-center gap-2.5 shrink-0">
          <Logo size={26} />
          <h1
            className="leading-none flex items-baseline gap-1.5"
            style={{ color: "var(--navy)" }}
          >
            <span style={{ fontFamily: "var(--font-sans)", fontWeight: 800, fontSize: "1rem", letterSpacing: "-0.02em" }}>
              OrgAudi
            </span>
            <span style={{ fontFamily: "var(--font-serif)", fontStyle: "italic", fontSize: "0.95rem", color: "var(--sky)" }}>
              Espólio.
            </span>
          </h1>
        </div>

        {/* Espólio breadcrumb */}
        {e?.nome && (
          <>
            <span className="text-muted-2" aria-hidden>
              <Icon name="chevronDown" size={12} className="-rotate-90" />
            </span>
            <span
              className="text-sm truncate max-w-[260px]"
              style={{ color: "var(--text-2)", fontFamily: "var(--font-sans)", fontWeight: 500 }}
              title={e.nome}
            >
              {e.nome}
            </span>
          </>
        )}

        <div className="flex-1" />

        {/* Actions */}
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={novo}
            className="text-xs px-2.5 py-1.5 rounded-sm transition-colors flex items-center gap-1.5"
            style={{ color: "var(--muted)" }}
            title="Novo espólio em branco"
          >
            <Icon name="plus" size={12} />
            <span className="hidden md:inline">Novo</span>
          </button>
          <button
            type="button"
            onClick={() => void reset()}
            className="text-xs px-2.5 py-1.5 rounded-sm transition-colors flex items-center gap-1.5"
            style={{ color: "var(--muted)" }}
            title="Carregar espólio de exemplo"
          >
            <Icon name="refresh" size={12} />
            <span className="hidden md:inline">Exemplo</span>
          </button>
          <button
            type="button"
            onClick={() => void onAbrir()}
            className="text-xs px-2.5 py-1.5 rounded-sm transition-colors flex items-center gap-1.5"
            style={{ color: "var(--muted)" }}
            title="Abrir espólio salvo"
          >
            <Icon name="cloudDown" size={12} />
            <span className="hidden md:inline">Abrir</span>
          </button>
          <button
            type="button"
            onClick={() => void onSalvar()}
            className="btn-primary text-xs"
            style={{ padding: "6px 14px" }}
            disabled={saving}
          >
            {saving ? <Icon name="loader" size={12} /> : <Icon name="cloudUp" size={12} />}
            {saving ? "Salvando…" : "Salvar"}
          </button>

          <div className="w-px h-5 mx-1.5" style={{ background: "var(--border-solid)" }} />

          <SupabaseBadge />
        </div>
      </div>
    </header>
  );
}
