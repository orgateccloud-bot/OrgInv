import { useEffect, useState } from "react";
import { getSupabase, isSupabaseEnabled } from "../lib/supabase";
import { useEspolio } from "../state";
import { useToast } from "./ui/Toast";
import { Icon } from "./ui/icons";

type Status = "off" | "anon" | "logged";

export function SupabaseBadge() {
  const { setAuthModalOpen } = useEspolio();
  const toast = useToast();
  const [status, setStatus] = useState<Status>(isSupabaseEnabled() ? "anon" : "off");
  const [email, setEmail] = useState<string | null>(null);

  useEffect(() => {
    if (!isSupabaseEnabled()) return;
    const sb = getSupabase();
    if (!sb) return;

    void sb.auth.getUser().then(({ data }) => {
      if (data.user) {
        setStatus("logged");
        setEmail(data.user.email ?? null);
      }
    });
    const { data: sub } = sb.auth.onAuthStateChange((_evt, session) => {
      if (session?.user) {
        setStatus("logged");
        setEmail(session.user.email ?? null);
      } else {
        setStatus("anon");
        setEmail(null);
      }
    });
    return () => sub.subscription.unsubscribe();
  }, []);

  const handleClick = async () => {
    if (status === "off") {
      toast.push({
        tone: "info",
        title: "Modo Local Ativo",
        description: "Supabase não está configurado. O aplicativo está rodando em modo totalmente local.",
      });
      return;
    }
    if (status === "anon") {
      setAuthModalOpen(true);
      return;
    }
    if (status === "logged") {
      if (confirm(`Deseja realmente sair da conta ${email}?`)) {
        const sb = getSupabase();
        if (sb) {
          await sb.auth.signOut();
          toast.push({
            tone: "ok",
            title: "Sessão encerrada",
            description: "Você saiu da sua conta Supabase com sucesso.",
          });
        }
      }
    }
  };

  const cfg: Record<
    Status,
    { bg: string; color: string; border: string; label: string; iconName: "user" | "logIn" | "settings" }
  > = {
    off: {
      bg: "var(--surface-elev)",
      color: "var(--muted)",
      border: "var(--border-solid)",
      label: "local-only",
      iconName: "settings",
    },
    anon: {
      bg: "var(--info-10)",
      color: "var(--info)",
      border: "var(--blue-20)",
      label: "conectar",
      iconName: "logIn",
    },
    logged: {
      bg: "var(--success-10)",
      color: "var(--success)",
      border: "var(--success-20)",
      label: email ? truncEmail(email) : "supabase",
      iconName: "user",
    },
  };
  const c = cfg[status];

  return (
    <button
      type="button"
      onClick={() => void handleClick()}
      className="hidden md:inline-flex items-center gap-1.5 transition-all active:scale-95 cursor-pointer rounded-pill"
      style={{
        background: c.bg,
        color: c.color,
        border: `1px solid ${c.border}`,
        padding: "4px 12px",
        fontFamily: "var(--font-mono)",
        fontSize: "0.62rem",
        textTransform: "uppercase",
        letterSpacing: "0.08em",
        fontWeight: 500,
      }}
      title={
        status === "logged"
          ? `Conectado como ${email}. Clique para sair.`
          : status === "anon"
          ? "Clique para conectar à Nuvem Supabase."
          : "Modo Local. Configurações do Supabase ausentes no .env."
      }
    >
      <Icon name={c.iconName} size={11} strokeWidth={2.5} />
      {c.label}
    </button>
  );
}

function truncEmail(s: string): string {
  if (s.length <= 18) return s;
  const [user, dom] = s.split("@");
  if (!dom) return s.slice(0, 16) + "…";
  return `${user.slice(0, 6)}…@${dom}`;
}
