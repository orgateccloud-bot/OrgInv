import { useState } from "react";
import { getSupabase } from "../lib/supabase";
import { useEspolio } from "../state";
import { useToast } from "./ui/Toast";
import { Icon } from "./ui/icons";

export function AuthModal() {
  const { state, setAuthModalOpen } = useEspolio();
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  if (!state.authModalOpen) return null;

  const handleSubmit = async (ev: React.FormEvent) => {
    ev.preventDefault();
    setError(null);
    setLoading(true);

    const sb = getSupabase();
    if (!sb) {
      setError("Supabase não está habilitado.");
      setLoading(false);
      return;
    }

    try {
      if (isSignUp) {
        const { error: signUpError } = await sb.auth.signUp({ email, password });
        if (signUpError) throw signUpError;
        toast.push({
          tone: "ok",
          title: "Cadastro realizado",
          description: "Verifique seu e-mail para confirmação se necessário.",
        });
      } else {
        const { error: signInError } = await sb.auth.signInWithPassword({ email, password });
        if (signInError) throw signInError;
        toast.push({
          tone: "ok",
          title: "Conectado à Nuvem",
          description: "Sessão iniciada com sucesso.",
        });
      }
      setAuthModalOpen(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      toast.push({
        tone: "err",
        title: isSignUp ? "Falha no cadastro" : "Falha na conexão",
        description: e instanceof Error ? e.message : String(e),
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center fade-in p-4"
      style={{
        background: "rgba(15, 23, 42, 0.45)",
        backdropFilter: "blur(6px)",
        WebkitBackdropFilter: "blur(6px)",
      }}
    >
      <div className="card p-7 w-full max-w-sm flex flex-col gap-5 relative fade-up">
        <button
          type="button"
          onClick={() => setAuthModalOpen(false)}
          className="absolute top-3 right-3 transition-colors p-1.5 rounded-md hover:bg-blue-10"
          style={{ color: "var(--muted)" }}
          aria-label="Fechar"
        >
          <Icon name="x" size={16} />
        </button>

        <div>
          <span className="text-eyebrow">Nuvem ORGATEC</span>
          <h3
            className="leading-tight mt-1 flex items-baseline gap-2"
            style={{ color: "var(--navy)", fontFamily: "var(--font-sans)", fontWeight: 700, fontSize: "1.35rem" }}
          >
            {isSignUp ? "Criar conta." : "Entrar."}
            <span
              style={{
                fontFamily: "var(--font-serif)",
                fontStyle: "italic",
                fontSize: "1.15rem",
                color: "var(--sky)",
              }}
            >
              O ledger aguarda.
            </span>
          </h3>
          <p className="text-xs text-muted leading-snug mt-2">
            Sincronize seus espólios e acesse-os de qualquer lugar.
          </p>
        </div>

        <div className="segmented w-full">
          <button
            type="button"
            className="flex-1 text-center"
            aria-selected={!isSignUp}
            onClick={() => {
              setIsSignUp(false);
              setError(null);
            }}
          >
            Entrar
          </button>
          <button
            type="button"
            className="flex-1 text-center"
            aria-selected={isSignUp}
            onClick={() => {
              setIsSignUp(true);
              setError(null);
            }}
          >
            Criar conta
          </button>
        </div>

        <form onSubmit={(ev) => void handleSubmit(ev)} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="field-label" htmlFor="email-input">
              E-mail corporativo
            </label>
            <input
              id="email-input"
              type="email"
              required
              className="input-base text-sm"
              placeholder="seu@email.com"
              value={email}
              onChange={(ev) => setEmail(ev.target.value)}
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="field-label" htmlFor="pass-input">
              Senha
            </label>
            <div className="relative">
              <input
                id="pass-input"
                type={showPw ? "text" : "password"}
                required
                className="input-base text-sm pr-10"
                placeholder="••••••••"
                value={password}
                onChange={(ev) => setPassword(ev.target.value)}
              />
              <button
                type="button"
                onClick={() => setShowPw((v) => !v)}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-md transition-colors hover:bg-blue-10"
                style={{ color: "var(--muted)" }}
                aria-label={showPw ? "Ocultar senha" : "Mostrar senha"}
              >
                <Icon name={showPw ? "eyeOff" : "eye"} size={14} />
              </button>
            </div>
          </div>

          {error && (
            <div
              className="rounded-sm p-2.5 text-xs flex items-start gap-2"
              style={{
                background: "var(--danger-10)",
                border: "1px solid var(--danger-20)",
                color: "var(--danger)",
              }}
            >
              <Icon name="alert" size={14} strokeWidth={2.5} />
              <span className="flex-1">{error}</span>
            </div>
          )}

          <button type="submit" className="btn-primary w-full mt-1" disabled={loading}>
            {loading ? (
              <>
                <Icon name="loader" size={14} />
                Conectando…
              </>
            ) : (
              <>
                {isSignUp ? "Cadastrar" : "Acessar plataforma"}
                <Icon name="arrowRight" size={14} />
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
