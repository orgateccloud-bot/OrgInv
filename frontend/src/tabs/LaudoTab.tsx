import { useState, useEffect } from "react";
import { laudoPdf, laudoXlsx, apurar, otimizar, isencoes, laudoReactive } from "../api";
import { useEspolio } from "../state";
import { Card } from "../components/ui/Card";
import { Icon, type IconName } from "../components/ui/icons";
import { moeda } from "../lib/fmt";

export function LaudoTab() {
  const { state, setApuracao, setRecomendacoes, setIsencoes } = useEspolio();

  const [errX, setErrX] = useState<string | null>(null);
  const [errP, setErrP] = useState<string | null>(null);
  const [errM, setErrM] = useState<string | null>(null);
  const [loadX, setLoadX] = useState(false);
  const [loadP, setLoadP] = useState(false);
  const [loadM, setLoadM] = useState(false);

  const [carregandoDados, setCarregandoDados] = useState(false);
  const [erroDados, setErroDados] = useState<string | null>(null);

  useEffect(() => {
    if (!state.espolio) return;
    if (state.apuracao) return;
    setCarregandoDados(true);
    setErroDados(null);
    Promise.all([apurar(state.espolio), otimizar(state.espolio), isencoes(state.espolio)])
      .then(([ap, rec, isc]) => {
        setApuracao(ap);
        setRecomendacoes(rec);
        setIsencoes(isc);
      })
      .catch((e: Error) => setErroDados(e.message))
      .finally(() => setCarregandoDados(false));
  }, [state.espolio, state.apuracao, setApuracao, setRecomendacoes, setIsencoes]);

  const espolio = state.espolio;
  if (!espolio) return null;

  if (erroDados) {
    return (
      <Card title="Erro ao processar dados">
        <p style={{ color: "var(--danger)" }}>{erroDados}</p>
      </Card>
    );
  }

  if (carregandoDados || !state.apuracao) {
    return (
      <div className="flex flex-col gap-4">
        <div className="h-64 w-full skeleton" style={{ borderRadius: "var(--r-lg)" }} />
        <div className="h-40 skeleton" style={{ borderRadius: "var(--r-lg)" }} />
      </div>
    );
  }

  const { resumo } = state.apuracao;
  const nomeArq = espolio.nome.replace(/\s+/g, "_");

  // Risk score
  const somaFracoes = espolio.herdeiros.reduce((s, h) => s + (h.fracao_monte || 0), 0);
  const somaInvalida = Math.abs(somaFracoes - 1) > 0.001;
  const bensIndet = espolio.bens.filter((b) => b.regime === "Indeterminado — requer classificação").length;
  const bensSemCusto = espolio.bens.filter(
    (b) =>
      b.regime !== "Fora do monte partilhável" &&
      (b.custo_aquisicao_dirpf === null || b.custo_aquisicao_dirpf === undefined),
  ).length;
  const herdeirosSemCpf = espolio.herdeiros.filter((h) => !h.cpf || h.cpf.trim() === "").length;
  const obitoIgualPartilha = espolio.data_obito === espolio.data_partilha;
  const vendas = espolio.bens.filter(
    (b) => b.regime === "Venda pelo espólio a terceiro" || b.regime === "Cessão de direitos hereditários",
  );
  const smurfingSuspeito = vendas.length >= 3;

  const anomalias: Array<{ categoria: "grave" | "alerta" | "info"; titulo: string; descricao: string }> = [];
  let riscoScore = 10;

  if (somaInvalida) {
    riscoScore += 35;
    anomalias.push({
      categoria: "grave",
      titulo: "Divisão do monte desequilibrada",
      descricao: `Soma das frações: ${somaFracoes.toFixed(4)} (deve ser 1.0000).`,
    });
  }
  if (bensIndet > 0) {
    riscoScore += 20;
    anomalias.push({
      categoria: "alerta",
      titulo: "Regimes indeterminados",
      descricao: `${bensIndet} bem(ns) sem classificação.`,
    });
  }
  if (bensSemCusto > 0) {
    riscoScore += Math.min(45, bensSemCusto * 15);
    anomalias.push({
      categoria: "alerta",
      titulo: "Ausência de custo DIRPF",
      descricao: `${bensSemCusto} bem(ns) sem custo histórico — tributação integral.`,
    });
  }
  if (herdeirosSemCpf > 0) {
    riscoScore += 10;
    anomalias.push({
      categoria: "info",
      titulo: "Documentação pendente",
      descricao: `${herdeirosSemCpf} herdeiro(s) sem CPF.`,
    });
  }
  if (obitoIgualPartilha) {
    riscoScore += 5;
    anomalias.push({
      categoria: "info",
      titulo: "Simultaneidade óbito/partilha",
      descricao: "Datas idênticas — revise certidões.",
    });
  }
  if (smurfingSuspeito) {
    riscoScore += 15;
    anomalias.push({
      categoria: "alerta",
      titulo: "Fracionamento suspeito",
      descricao: "3+ vendas/cessões. Risco de autuação por triangulação patrimonial.",
    });
  }
  riscoScore = Math.min(99, riscoScore);

  const radius = 100;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (circumference * riscoScore) / 100;
  const riskColor = riscoScore <= 30 ? "var(--success)" : riscoScore <= 60 ? "var(--warning)" : "var(--danger)";
  const riskLabel = riscoScore <= 30 ? "Risco baixo" : riscoScore <= 60 ? "Risco médio" : "Risco crítico";

  // Tax reform
  const totalGanhos = espolio.bens.reduce(
    (s, b) => s + Math.max(0, (b.valor_venda || b.valor_partilha || 0) - (b.custo_aquisicao_dirpf || 0)),
    0,
  );
  const irAtual = resumo.ir_espolio_total || 0;
  const irReforma = totalGanhos * 0.265;
  const aumentoReforma = Math.max(0, irReforma - irAtual);
  const economiaAtual = Math.max(0, irAtual - irReforma);
  const maxIR = Math.max(irAtual, irReforma, 1000);
  const pctAtual = (irAtual / maxIR) * 100;
  const pctReforma = (irReforma / maxIR) * 100;

  const getComentario = () => {
    if (riscoScore >= 60) {
      return "Risco ALTO de autuação. Há inconsistências graves na partilha ou nos valores. Corrija herdeiros e bens antes da assinatura.";
    }
    if (riscoScore >= 30) {
      return "Risco MÉDIO. O espólio apresenta alertas de compliance (documentação ou custo DIRPF). A apuração procede, mas pendências podem gerar custos.";
    }
    return "Compliance EXCELENTE. Dados consistentes, frações perfeitas, documentação completa. Risco fiscal mínimo.";
  };

  const baixar = async (
    fn: () => Promise<Blob>,
    ext: string,
    setLoad: (v: boolean) => void,
    setErr: (v: string | null) => void,
  ) => {
    setErr(null);
    setLoad(true);
    try {
      const blob = await fn();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `laudo_${nomeArq}.${ext}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setLoad(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Risk Gauge — HERO grande */}
      <Card>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
          {/* Gauge */}
          <div className="flex flex-col items-center justify-center text-center">
            <div className="relative w-64 h-64 flex items-center justify-center">
              <svg className="w-64 h-64 transform -rotate-90" viewBox="0 0 240 240">
                <circle cx="120" cy="120" r={radius} stroke="var(--blue-10)" strokeWidth="14" fill="transparent" />
                <circle
                  cx="120"
                  cy="120"
                  r={radius}
                  stroke={riskColor}
                  strokeWidth="14"
                  fill="transparent"
                  strokeDasharray={circumference}
                  strokeDashoffset={strokeDashoffset}
                  strokeLinecap="round"
                  style={{ transition: "stroke-dashoffset 0.8s var(--easing)" }}
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span
                  className="tabular-nums"
                  style={{
                    fontFamily: "var(--font-sans)",
                    fontSize: "4.5rem",
                    fontWeight: 800,
                    letterSpacing: "-0.04em",
                    color: "var(--navy)",
                    lineHeight: 1,
                  }}
                >
                  {riscoScore}
                </span>
                <span className="text-eyebrow mt-2" style={{ color: "var(--muted)" }}>
                  Score
                </span>
              </div>
            </div>
            <span
              className={
                riscoScore <= 30 ? "badge-ok mt-3" : riscoScore <= 60 ? "badge-warn mt-3" : "badge-err mt-3"
              }
            >
              {riskLabel}
            </span>
          </div>

          {/* Comentário lateral */}
          <div>
            <span className="text-eyebrow">Probabilidade de autuação</span>
            <h3
              className="mt-1 leading-tight"
              style={{
                fontFamily: "var(--font-sans)",
                fontWeight: 700,
                fontSize: "1.35rem",
                color: "var(--navy)",
                letterSpacing: "-0.02em",
              }}
            >
              Conclusão de auditoria fiscal
            </h3>
            <p
              className="mt-3 leading-relaxed"
              style={{ color: "var(--text-2)", fontFamily: "var(--font-serif)", fontStyle: "italic", fontSize: "1.05rem" }}
            >
              {getComentario()}
            </p>
          </div>
        </div>
      </Card>

      {/* Anomalias */}
      <Card title="Checkpoints forenses" subtitle={`${anomalias.length} item(ns) detectado(s)`}>
        {anomalias.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center gap-2">
            <div
              className="w-12 h-12 rounded-full flex items-center justify-center"
              style={{ background: "var(--success-10)", color: "var(--success)" }}
            >
              <Icon name="shield" size={22} strokeWidth={2.5} />
            </div>
            <p className="text-sm font-bold" style={{ color: "var(--success)" }}>
              Nenhuma inconformidade detectada
            </p>
            <p className="text-xs text-muted">O dossiê está íntegro.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {anomalias.map((anom, idx) => {
              const config = {
                grave:  { color: "var(--danger)",  bg: "var(--danger-10)",  icon: "x" as IconName },
                alerta: { color: "var(--warning)", bg: "var(--warning-10)", icon: "alert" as IconName },
                info:   { color: "var(--info)",    bg: "var(--info-10)",    icon: "info" as IconName },
              }[anom.categoria];
              return (
                <div
                  key={idx}
                  className="flex items-start gap-3 p-3 text-sm"
                  style={{
                    background: config.bg,
                    borderLeft: `3px solid ${config.color}`,
                    borderRadius: "var(--r-sm)",
                  }}
                >
                  <span style={{ color: config.color }} className="shrink-0 mt-0.5">
                    <Icon name={config.icon} size={14} strokeWidth={2.5} />
                  </span>
                  <div className="flex-1 min-w-0">
                    <h5 className="font-bold" style={{ color: "var(--navy)" }}>
                      {anom.titulo}
                    </h5>
                    <p className="text-muted mt-0.5 leading-snug">{anom.descricao}</p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Card>

      {/* Reforma simulator — colapsável */}
      <details className="card" style={{ padding: 0 }}>
        <summary
          className="cursor-pointer px-5 py-4 flex items-center gap-2 select-none"
          style={{ color: "var(--navy)", fontFamily: "var(--font-sans)", fontWeight: 600 }}
        >
          <Icon name="chartBar" size={14} className="text-muted" />
          Simulação Reforma Tributária (IBS/CBS)
          <span className="text-xs text-muted-2 font-normal ml-2">
            {aumentoReforma > 0 ? `+${moeda(aumentoReforma)}` : `-${moeda(economiaAtual)}`}
          </span>
        </summary>
        <div className="px-5 pb-5 pt-1 border-t" style={{ borderColor: "var(--border-solid)" }}>
          <p className="text-xs text-muted mb-4 mt-3">Alíquota simulada: <strong style={{ color: "var(--navy)" }}>26,5%</strong></p>
          <div className="space-y-4">
            <div className="space-y-1.5">
              <div className="flex justify-between text-sm">
                <span className="text-muted">Regime atual (IR + FR1/FR2)</span>
                <span className="font-bold tabular-nums" style={{ color: "var(--navy)" }}>
                  {moeda(irAtual)}
                </span>
              </div>
              <div className="progress-bar h-2">
                <div className="progress-fill" style={{ width: `${pctAtual}%`, background: "var(--blue)" }} />
              </div>
            </div>
            <div className="space-y-1.5">
              <div className="flex justify-between text-sm">
                <span className="text-muted">Pós-reforma (flat 26,5%)</span>
                <span className="font-bold tabular-nums" style={{ color: "var(--navy)" }}>
                  {moeda(irReforma)}
                </span>
              </div>
              <div className="progress-bar h-2">
                <div className="progress-fill" style={{ width: `${pctReforma}%`, background: "var(--danger)" }} />
              </div>
            </div>
          </div>
          <p className="mt-4 text-sm flex items-center gap-2">
            {aumentoReforma > 0 ? (
              <span style={{ color: "var(--danger)" }} className="font-bold flex items-center gap-2">
                <Icon name="alert" size={14} strokeWidth={2.5} />
                Aumento estimado: {moeda(aumentoReforma)}
              </span>
            ) : (
              <span style={{ color: "var(--success)" }} className="font-bold flex items-center gap-2">
                <Icon name="check" size={14} strokeWidth={2.5} />
                Redução estimada: {moeda(economiaAtual)}
              </span>
            )}
          </p>
        </div>
      </details>

      {/* Downloads — uma única linha */}
      <Card title="Downloads do laudo" subtitle="Versões disponíveis para entrega ao cliente">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <DownloadButton
            label="Planilha"
            ext="xlsx"
            description="4 abas com fórmulas vivas"
            loading={loadX}
            error={errX}
            onClick={() => void baixar(() => laudoXlsx(espolio), "xlsx", setLoadX, setErrX)}
          />
          <DownloadButton
            label="PDF consolidado"
            ext="pdf"
            description={state.analise ? "Inclui análise IA" : "Sem análise IA"}
            loading={loadP}
            error={errP}
            primary
            onClick={() => void baixar(() => laudoPdf(espolio, state.analise), "pdf", setLoadP, setErrP)}
          />
          <DownloadButton
            label="Markdown interativo"
            ext="md"
            description="Reactive MD no VS Code"
            loading={loadM}
            error={errM}
            onClick={() => void baixar(() => laudoReactive(espolio), "md", setLoadM, setErrM)}
          />
        </div>
      </Card>
    </div>
  );
}

function DownloadButton({
  label,
  ext,
  description,
  loading,
  error,
  primary,
  onClick,
}: {
  label: string;
  ext: string;
  description: string;
  loading: boolean;
  error: string | null;
  primary?: boolean;
  onClick: () => void;
}) {
  return (
    <div className="flex flex-col">
      <button
        type="button"
        className={primary ? "btn-primary w-full" : "btn-ghost w-full"}
        onClick={onClick}
        disabled={loading}
        style={{ flexDirection: "column", alignItems: "stretch", padding: "14px 16px", height: "auto", gap: 4 }}
      >
        <div className="flex items-center justify-between w-full">
          <span style={{ fontFamily: "var(--font-sans)", fontWeight: 600 }}>{label}</span>
          {loading ? (
            <Icon name="loader" size={14} />
          ) : (
            <Icon name="download" size={14} />
          )}
        </div>
        <div
          className="text-xs text-left"
          style={{
            color: primary ? "rgba(255,255,255,0.75)" : "var(--muted)",
            fontWeight: 400,
          }}
        >
          {description}
        </div>
        <div
          className="text-[10px] text-left tabular-nums"
          style={{
            fontFamily: "var(--font-mono)",
            color: primary ? "rgba(255,255,255,0.6)" : "var(--muted-2)",
          }}
        >
          .{ext}
        </div>
      </button>
      {error && (
        <p className="text-xs mt-2" style={{ color: "var(--danger)" }}>
          {error}
        </p>
      )}
    </div>
  );
}
