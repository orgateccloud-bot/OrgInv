import { useRef, useState } from "react";
import { extrairPdfs } from "../api";
import { moeda } from "../lib/fmt";
import { cx } from "../lib/fmt";
import { useEspolio } from "../state";
import { Card } from "../components/ui/Card";
import { Field } from "../components/ui/Field";
import { useToast } from "../components/ui/Toast";
import { Icon } from "../components/ui/icons";
import type { Bem, Espolio, Herdeiro, OpcaoArt23, Regime } from "../types";
import { isSupabaseEnabled, getSupabase } from "../lib/supabase";
import { salvarExtracaoIa } from "../lib/espolioRepo";

const REGIME_MAP: Record<string, Regime> = {
  TRANSMISSAO_HERDEIRO:          "Transmissão a herdeiro (partilha)",
  VENDA_PELO_ESPOLIO:            "Venda pelo espólio a terceiro",
  CESSAO_DIREITOS_HEREDITARIOS:  "Cessão de direitos hereditários",
  FORA_DO_ESPOLIO:               "Fora do monte partilhável",
  INDETERMINADO:                 "Indeterminado — requer classificação",
};
const OPCAO_MAP: Record<string, OpcaoArt23> = {
  VALOR_HISTORICO: "Valor histórico (§2º — sem IR; ganho diferido)",
  VALOR_MERCADO:   "Valor de mercado (§1º — IR no espólio agora)",
  NAO_APLICAVEL:   "Não aplicável a este regime",
};

async function computeSha256(text: string): Promise<string> {
  const msgBuffer = new TextEncoder().encode(text);
  const hashBuffer = await crypto.subtle.digest("SHA-256", msgBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}

function corConfianca(c: string): { color: string; label: string } {
  const k = (c || "").toLowerCase();
  if (k === "alta") return { color: "var(--success)", label: "alta" };
  if (k === "media" || k === "média") return { color: "var(--warning)", label: "média" };
  if (k === "baixa") return { color: "var(--danger)", label: "baixa" };
  return { color: "var(--muted-2)", label: "—" };
}

export function DocumentosTab() {
  const { state, setExtracao, setEspolio } = useEspolio();
  const [files, setFiles] = useState<File[]>([]);
  const [instr, setInstr] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const toast = useToast();

  const apiKey = state.apiKey;
  const podeExtrair = files.length > 0 && !!apiKey && !carregando;
  const tamanhoTotalKB = files.reduce((s, f) => s + f.size, 0) / 1024;

  const onExtrair = async () => {
    setErro(null);
    setCarregando(true);
    try {
      const r = await extrairPdfs(files, instr, apiKey);
      setExtracao(r.espolio);
      toast.push({
        tone: "ok",
        title: "Extração concluída",
        description: `${r.espolio.bens.length} bem(ns), ${r.espolio.herdeiros.length} herdeiro(s).`,
      });

      if (isSupabaseEnabled()) {
        const sb = getSupabase();
        const { data: { session } } = sb ? await sb.auth.getSession() : { data: { session: null } };
        if (session?.user) {
          try {
            const hash = await computeSha256(JSON.stringify(r.espolio));
            await salvarExtracaoIa({
              espolioId: state.activeEspolioId,
              documentos: files.map((f) => f.name),
              resultadoJson: r.espolio,
              tokensInput: r.uso?.input_tokens,
              tokensOutput: r.uso?.output_tokens,
              auditHash: hash,
            });
          } catch (dbErr) {
            console.error("Falha ao salvar log de auditoria:", dbErr);
          }
        }
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setErro(msg);
      toast.push({ tone: "err", title: "Falha na extração", description: msg });
    } finally {
      setCarregando(false);
    }
  };

  const aplicarAoFormulario = () => {
    if (!state.extracao || !state.espolio) return;
    const x = state.extracao;
    const herdeiros: Herdeiro[] = x.herdeiros.length
      ? x.herdeiros.map((h) => ({
          nome: h.nome ?? "",
          cpf: h.cpf ?? "",
          fracao_monte: h.fracao_monte ?? 0,
          eh_meeiro: !!h.eh_meeiro,
        }))
      : state.espolio.herdeiros;

    const bens: Bem[] = x.bens.map((b) => ({
      identificacao: b.identificacao,
      matricula: b.matricula ?? "",
      regime: REGIME_MAP[b.regime_sugerido ?? "INDETERMINADO"] ?? "Indeterminado — requer classificação",
      opcao:  OPCAO_MAP[b.opcao_art23_sugerida ?? "NAO_APLICAVEL"] ?? "Não aplicável a este regime",
      eh_imovel: b.eh_imovel ?? true,
      custo_aquisicao_dirpf: b.custo_aquisicao_dirpf,
      data_aquisicao: b.data_aquisicao_iso,
      valor_partilha: b.valor_partilha,
      valor_venda: b.valor_venda,
      data_operacao: b.data_operacao_iso,
    }));

    const novo: Espolio = {
      ...state.espolio,
      nome:          x.nome_espolio    ?? state.espolio.nome,
      cpf_falecido:  x.cpf_falecido    ?? state.espolio.cpf_falecido,
      data_obito:    x.data_obito_iso  ?? state.espolio.data_obito,
      data_partilha: x.data_partilha_iso ?? state.espolio.data_partilha,
      herdeiros,
      bens,
    };
    setEspolio(novo);
    toast.push({ tone: "info", title: "Aplicado ao formulário", description: "Revise tudo na aba Bens." });
  };

  const onDrop = (ev: React.DragEvent) => {
    ev.preventDefault();
    setDragging(false);
    const dropped = Array.from(ev.dataTransfer.files).filter(
      (f) => f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf"),
    );
    if (dropped.length > 0) setFiles((prev) => [...prev, ...dropped]);
  };

  const removeFile = (idx: number) => setFiles((prev) => prev.filter((_, i) => i !== idx));

  return (
    <div className="flex flex-col gap-4">
      <Card
        title="Extrair com Claude Sonnet"
        subtitle="Arraste PDFs — a IA propõe a estrutura, você confirma."
      >
        <div
          className={cx("dropzone", dragging && "is-dragging")}
          onDragOver={(ev) => {
            ev.preventDefault();
            if (!dragging) setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          onClick={() => inputRef.current?.click()}
          role="button"
          tabIndex={0}
        >
          <input
            ref={inputRef}
            type="file"
            accept="application/pdf"
            multiple
            onChange={(ev) => setFiles(Array.from(ev.target.files ?? []))}
            className="hidden"
          />
          <Icon name="upload" size={28} className="mx-auto mb-2 text-blue" />
          <p className="text-sm font-semibold" style={{ color: "var(--navy)" }}>
            {dragging ? "Solte aqui" : "Arraste PDFs ou clique para selecionar"}
          </p>
          <p className="text-xs text-muted mt-1">
            Escrituras, inventário, DIRPF, ITCD, contratos…
          </p>
        </div>

        {files.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {files.map((f, i) => (
              <div
                key={i}
                className="inline-flex items-center gap-2 px-2.5 py-1 text-xs"
                style={{
                  background: "var(--blue-10)",
                  border: "1px solid var(--blue-20)",
                  borderRadius: "var(--r-sm)",
                  color: "var(--navy)",
                }}
              >
                <Icon name="document" size={11} className="text-muted" />
                <span className="font-medium max-w-[200px] truncate">{f.name}</span>
                <span className="text-muted text-mono-sm">{(f.size / 1024).toFixed(0)} KB</span>
                <button
                  type="button"
                  onClick={(ev) => {
                    ev.stopPropagation();
                    removeFile(i);
                  }}
                  className="text-muted hover:text-danger transition-colors"
                  aria-label={`Remover ${f.name}`}
                >
                  <Icon name="x" size={11} />
                </button>
              </div>
            ))}
          </div>
        )}

        <Field
          label="Instruções adicionais (opcional)"
          className="mt-4"
          hint="Ex.: «Lote A já vendido em jul/2024» · «Cônjuge é meeira»"
        >
          <textarea
            className="input-base min-h-[64px]"
            value={instr}
            onChange={(ev) => setInstr(ev.target.value)}
          />
        </Field>

        <div className="flex items-center gap-3 mt-4 flex-wrap">
          <button className="btn-primary" disabled={!podeExtrair} onClick={() => void onExtrair()}>
            {carregando ? (
              <>
                <Icon name="loader" size={14} />
                Lendo PDFs…
              </>
            ) : (
              <>
                <Icon name="sparkles" size={14} />
                Extrair
              </>
            )}
          </button>

          {!apiKey && (
            <span className="text-xs text-muted">
              Configure a chave na aba <strong style={{ color: "var(--navy)" }}>Espólio</strong>.
            </span>
          )}
          {files.length > 0 && apiKey && (
            <span className="text-xs text-muted tabular-nums">
              {files.length} arquivo(s) · {tamanhoTotalKB.toFixed(1)} KB
            </span>
          )}
        </div>

        {erro && (
          <div
            className="mt-3 p-3 text-sm flex items-start gap-2"
            style={{
              background: "var(--danger-10)",
              border: "1px solid var(--danger-20)",
              borderLeft: "3px solid var(--danger)",
              borderRadius: "var(--r-sm)",
              color: "var(--danger)",
            }}
          >
            <Icon name="alert" size={14} strokeWidth={2.5} />
            <div>
              <strong>Erro:</strong> {erro}
            </div>
          </div>
        )}
      </Card>

      {state.extracao && (
        <Card
          title="Resultado da extração"
          subtitle={`${state.extracao.documentos_analisados.length} documento(s) analisado(s) · ${state.extracao.bens.length} bem(ns), ${state.extracao.herdeiros.length} herdeiro(s)`}
          actions={
            <button onClick={aplicarAoFormulario} className="btn-primary text-xs">
              <Icon name="arrowDown" size={12} />
              Aplicar
            </button>
          }
        >
          {state.extracao.observacoes_globais.length > 0 && (
            <div
              className="p-3 mb-4"
              style={{
                background: "var(--warning-10)",
                borderLeft: "3px solid var(--warning)",
                border: "1px solid var(--warning-20)",
                borderRadius: "var(--r-sm)",
              }}
            >
              <p className="font-semibold text-xs mb-1.5 flex items-center gap-1.5" style={{ color: "var(--warning)" }}>
                <Icon name="alert" size={11} strokeWidth={2.5} />
                Observações da IA — exigem revisão humana
              </p>
              <ul className="text-sm list-disc pl-5 space-y-0.5" style={{ color: "var(--navy)" }}>
                {state.extracao.observacoes_globais.map((o, i) => (
                  <li key={i}>{o}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="space-y-2">
            {state.extracao.bens.map((b, i) => {
              const c = corConfianca(b.confianca);
              return (
                <details
                  key={i}
                  className="overflow-hidden"
                  style={{ border: "1px solid var(--border-solid)", borderRadius: "var(--r-sm)" }}
                >
                  <summary
                    className="cursor-pointer px-3 py-2 flex items-center gap-2 text-sm"
                    style={{ color: "var(--navy)" }}
                  >
                    <span
                      className="w-2 h-2 rounded-full inline-block shrink-0"
                      style={{ background: c.color }}
                    />
                    <span className="font-semibold">{b.identificacao}</span>
                    <span className="text-xs text-muted ml-auto">
                      {b.regime_sugerido ?? "INDETERMINADO"} · {c.label}
                    </span>
                  </summary>
                  <div className="p-3 text-sm space-y-2" style={{ color: "var(--text)", borderTop: "1px solid var(--border-solid)" }}>
                    <p><strong>Rationale:</strong> {b.rationale}</p>
                    <p className="text-xs text-muted">Fonte: {b.fonte}</p>
                    <div className="grid grid-cols-3 gap-2 text-xs">
                      <div>Custo: <span className="tabular-nums">{moeda(b.custo_aquisicao_dirpf)}</span></div>
                      <div>Partilha: <span className="tabular-nums">{moeda(b.valor_partilha)}</span></div>
                      <div>Venda: <span className="tabular-nums">{moeda(b.valor_venda)}</span></div>
                      <div>Aquisição: {b.data_aquisicao_iso ?? "—"}</div>
                      <div>Operação: {b.data_operacao_iso ?? "—"}</div>
                      <div>Imóvel? {b.eh_imovel ? "sim" : "não"}</div>
                    </div>
                  </div>
                </details>
              );
            })}
          </div>
        </Card>
      )}
    </div>
  );
}
