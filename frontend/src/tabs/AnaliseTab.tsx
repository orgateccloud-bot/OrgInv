import { useState } from "react";
import { analisarStream } from "../api";
import { useEspolio } from "../state";
import { Card } from "../components/ui/Card";
import { Icon } from "../components/ui/icons";
import { isSupabaseEnabled, getSupabase } from "../lib/supabase";
import { salvarExtracaoIa } from "../lib/espolioRepo";

async function computeSha256(text: string): Promise<string> {
  const msgBuffer = new TextEncoder().encode(text);
  const hashBuffer = await crypto.subtle.digest("SHA-256", msgBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}

function MdView({ texto }: { texto: string }) {
  const blocos = texto.split(/\n\n+/);
  return (
    <div className="space-y-3 leading-relaxed" style={{ color: "var(--text)" }}>
      {blocos.map((bloco, i) => {
        const linhas = bloco.split("\n");
        if (linhas.every((l) => /^\s*[-•*]\s+/.test(l))) {
          return (
            <ul key={i} className="list-disc pl-5 space-y-1.5">
              {linhas.map((l, j) => (
                <li
                  key={j}
                  dangerouslySetInnerHTML={{
                    __html: aplicaInline(l.replace(/^\s*[-•*]\s+/, "")),
                  }}
                />
              ))}
            </ul>
          );
        }
        const join = linhas.join(" ").trim();
        if (/^\*\*.+\*\*$/.test(join)) {
          return (
            <h4
              key={i}
              className="text-base font-bold mt-4"
              style={{ color: "var(--navy)", fontFamily: "var(--font-sans)" }}
            >
              {join.replace(/^\*\*|\*\*$/g, "")}
            </h4>
          );
        }
        return <p key={i} dangerouslySetInnerHTML={{ __html: aplicaInline(join) }} />;
      })}
    </div>
  );
}

function aplicaInline(s: string): string {
  const esc = s
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
  return esc.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
}

export function AnaliseTab() {
  const { state, setAnalise, appendAnalise } = useEspolio();
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const apiKey = state.apiKey;
  const podeAnalisar = !!state.espolio && !!apiKey && !carregando;

  const onAnalisar = async () => {
    if (!state.espolio) return;
    setErro(null);
    setAnalise("");
    setCarregando(true);
    let fullText = "";
    try {
      await analisarStream(state.espolio, apiKey, (chunk) => {
        fullText += chunk;
        appendAnalise(chunk);
      });

      if (isSupabaseEnabled()) {
        const sb = getSupabase();
        const { data: { session } } = sb ? await sb.auth.getSession() : { data: { session: null } };
        if (session?.user) {
          try {
            const hash = await computeSha256(fullText);
            await salvarExtracaoIa({
              espolioId: state.activeEspolioId,
              documentos: ["Relatório de Análise Narrativa da IA"],
              resultadoJson: { relatorio_ia: fullText },
              auditHash: hash,
            });
          } catch (dbErr) {
            console.error("Falha ao salvar log de auditoria:", dbErr);
          }
        }
      }
    } catch (e) {
      setErro(e instanceof Error ? e.message : String(e));
    } finally {
      setCarregando(false);
    }
  };

  const baixar = () => {
    if (!state.analise || !state.espolio) return;
    const blob = new Blob([state.analise], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `analise_${state.espolio.nome.replace(/\s+/g, "_")}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Card
      title="Análise narrativa"
      subtitle="Redigida pelo Claude Sonnet em PT-BR. Não recalcula — só comenta."
      actions={
        <div className="flex gap-2">
          <button
            className="btn-primary text-xs"
            disabled={!podeAnalisar}
            onClick={() => void onAnalisar()}
          >
            {carregando ? (
              <>
                <Icon name="loader" size={12} />
                Redigindo…
              </>
            ) : (
              <>
                <Icon name="sparkles" size={12} />
                Gerar análise
              </>
            )}
          </button>
          {state.analise && !carregando && (
            <button onClick={baixar} className="btn-ghost text-xs">
              <Icon name="download" size={12} />
              .md
            </button>
          )}
        </div>
      }
    >
      {carregando && <div className="h-1 w-full mb-4 skeleton" />}
      {!apiKey && (
        <p className="text-sm mb-3 flex items-center gap-2" style={{ color: "var(--warning)" }}>
          <Icon name="alert" size={14} strokeWidth={2.5} />
          Configure a <code>ANTHROPIC_API_KEY</code> na aba Espólio.
        </p>
      )}
      {erro && (
        <p className="text-sm mb-3 flex items-center gap-2" style={{ color: "var(--danger)" }}>
          <Icon name="alert" size={14} strokeWidth={2.5} />
          Erro: {erro}
        </p>
      )}
      {state.analise ? (
        <MdView texto={state.analise} />
      ) : !carregando ? (
        <div className="text-sm text-muted">
          Clique em <strong style={{ color: "var(--navy)" }}>Gerar análise</strong>. A IA explica o motor — não
          recalcula nem altera valores. Toda a aritmética já foi feita em código verificável.
        </div>
      ) : null}
    </Card>
  );
}
