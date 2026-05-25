import { useEffect, useState } from "react";
import { apurar, isencoes, otimizar } from "../api";
import { moeda } from "../lib/fmt";
import { useEspolio } from "../state";
import { Card } from "../components/ui/Card";
import { SkeletonCard } from "../components/ui/Skeleton";
import { Icon } from "../components/ui/icons";

export function ApuracaoTab() {
  const { state, setApuracao, setRecomendacoes, setIsencoes } = useEspolio();
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [hoveredSegment, setHoveredSegment] = useState<{ label: string; value: number; color: string } | null>(null);

  useEffect(() => {
    if (!state.espolio) return;
    if (state.apuracao) return;
    setCarregando(true);
    setErro(null);
    Promise.all([
      apurar(state.espolio),
      otimizar(state.espolio),
      isencoes(state.espolio),
    ])
      .then(([ap, rec, isc]) => {
        setApuracao(ap);
        setRecomendacoes(rec);
        setIsencoes(isc);
      })
      .catch((e: Error) => setErro(e.message))
      .finally(() => setCarregando(false));
  }, [state.espolio, state.apuracao, setApuracao, setRecomendacoes, setIsencoes]);

  if (erro) {
    return (
      <Card title="Erro na apuração">
        <p style={{ color: "var(--danger)" }}>{erro}</p>
      </Card>
    );
  }

  if (carregando || !state.apuracao) {
    return (
      <div className="flex flex-col gap-4">
        <SkeletonCard lines={3} />
        <SkeletonCard lines={6} />
      </div>
    );
  }

  const { resumo, bens } = state.apuracao;
  const conclusivo = resumo.conclusivo;

  const totalCusto = bens.reduce((s, b) => s + (b.custo_aquisicao_dirpf || 0), 0);
  const totalValorEstimado = bens.reduce((s, b) => s + (b.valor_venda || b.valor_partilha || 0), 0);
  const totalGanhoBruto = bens.reduce((s, b) => {
    const r = b.resultado;
    return s + (r.ganho_bruto || r.ganho_diferido || 0);
  }, 0);
  const totalBaseTributavel = bens.reduce((s, b) => s + (b.resultado.base_tributavel || 0), 0);
  const totalIr = resumo.ir_espolio_total || 0;

  const totalEconomiaReducoes = Math.max(0, totalGanhoBruto - totalBaseTributavel);
  const totalGanhoLivre = Math.max(0, totalBaseTributavel - totalIr);
  const totalCalculado = totalCusto + totalGanhoLivre + totalIr + totalEconomiaReducoes;
  const totalOutrosBens = Math.max(0, totalValorEstimado - totalCalculado);

  const pctCusto = totalValorEstimado > 0 ? (totalCusto / totalValorEstimado) * 100 : 0;
  const pctGanhoLivre = totalValorEstimado > 0 ? (totalGanhoLivre / totalValorEstimado) * 100 : 0;
  const pctIr = totalValorEstimado > 0 ? (totalIr / totalValorEstimado) * 100 : 0;
  const pctEconomia = totalValorEstimado > 0 ? (totalEconomiaReducoes / totalValorEstimado) * 100 : 0;
  const pctOutros = totalValorEstimado > 0 ? (totalOutrosBens / totalValorEstimado) * 100 : 0;

  return (
    <div className="flex flex-col gap-4">
      {/* HERO horizontal — IR + métricas inline */}
      <div className="card p-7">
        <div className="flex flex-col md:flex-row md:items-end gap-6 justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-eyebrow">IR do espólio</span>
              {conclusivo ? (
                <span className="badge-ok">
                  <Icon name="check" size={10} strokeWidth={2.5} />
                  Conclusivo
                </span>
              ) : (
                <span className="badge-warn">
                  <Icon name="alert" size={10} strokeWidth={2.5} />
                  Pendente
                </span>
              )}
            </div>
            <div
              style={{
                fontFamily: "var(--font-sans)",
                fontSize: "var(--text-display)",
                fontWeight: 800,
                letterSpacing: "-0.03em",
                lineHeight: 1,
                color: "var(--navy)",
                fontVariantNumeric: "tabular-nums",
              }}
            >
              {moeda(resumo.ir_espolio_total)}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-8 shrink-0">
            <div>
              <div className="text-eyebrow mb-1">Conclusivos</div>
              <div
                className="tabular-nums"
                style={{ fontFamily: "var(--font-sans)", fontSize: "1.75rem", fontWeight: 800, color: "var(--success)" }}
              >
                {resumo.bens_conclusivos}
              </div>
            </div>
            <div>
              <div className="text-eyebrow mb-1">Pendentes</div>
              <div
                className="tabular-nums"
                style={{
                  fontFamily: "var(--font-sans)",
                  fontSize: "1.75rem",
                  fontWeight: 800,
                  color: resumo.bens_pendentes > 0 ? "var(--warning)" : "var(--muted-2)",
                }}
              >
                {resumo.bens_pendentes}
              </div>
            </div>
          </div>
        </div>

        {!conclusivo && (
          <p
            className="mt-4 text-sm flex items-start gap-2"
            style={{ color: "var(--warning)" }}
          >
            <Icon name="alert" size={14} strokeWidth={2.5} className="mt-0.5 shrink-0" />
            <span>
              <strong>IR não é definitivo.</strong> Resolva pendências em{" "}
              <strong style={{ color: "var(--navy)" }}>Bens</strong> antes da entrega à RFB.
            </span>
          </p>
        )}
      </div>

      {/* Donut chart como destaque único */}
      {totalValorEstimado > 0 && (
        <Card
          title="Composição patrimonial"
          subtitle={`Total estimado: ${moeda(totalValorEstimado)}`}
        >
          <div className="flex flex-col md:flex-row items-center gap-8 py-2">
            <div className="relative shrink-0">
              <svg width="220" height="220" viewBox="0 0 200 200" className="donut-svg">
                <g transform="rotate(-90 100 100)">
                  {(() => {
                    let acc = 0;
                    const r = 72;
                    const circ = 2 * Math.PI * r;
                    const segs = [
                      { key: "custo",    label: "Custo DIRPF",    value: totalCusto,           pct: pctCusto,    color: "#3B82F6" },
                      { key: "ganho",    label: "Ganho líquido",  value: totalGanhoLivre,      pct: pctGanhoLivre, color: "#16A34A" },
                      { key: "ir",       label: "IR do espólio",  value: totalIr,              pct: pctIr,       color: "#DC2626" },
                      { key: "economia", label: "Economia legal", value: totalEconomiaReducoes,pct: pctEconomia, color: "#0EA5E9" },
                      { key: "outros",   label: "Isentos/outros", value: totalOutrosBens,      pct: pctOutros,   color: "#94A3B8" },
                    ].filter((s) => s.pct > 0);

                    return segs.map((s) => {
                      const dasharray = `${(s.pct / 100) * circ} ${circ}`;
                      const dashoffset = -((acc / 100) * circ);
                      acc += s.pct;
                      const isHovered = hoveredSegment?.label === s.label;
                      return (
                        <circle
                          key={s.key}
                          cx="100"
                          cy="100"
                          r={r}
                          fill="transparent"
                          stroke={s.color}
                          strokeWidth={isHovered ? "22" : "16"}
                          className="donut-segment"
                          style={{
                            strokeDasharray: dasharray,
                            strokeDashoffset: dashoffset,
                            opacity: hoveredSegment ? (isHovered ? 1 : 0.3) : 0.92,
                          }}
                          onMouseEnter={() => setHoveredSegment({ label: s.label, value: s.value, color: s.color })}
                          onMouseLeave={() => setHoveredSegment(null)}
                        />
                      );
                    });
                  })()}
                </g>
                <text x="100" y="92" textAnchor="middle" className="donut-center-lbl">
                  {hoveredSegment ? hoveredSegment.label : "Patrimônio"}
                </text>
                <text
                  x="100"
                  y="116"
                  textAnchor="middle"
                  className="donut-center-val"
                  style={{ fontSize: "16px" }}
                >
                  {moeda(hoveredSegment ? hoveredSegment.value : totalValorEstimado)}
                </text>
              </svg>
            </div>

            <div className="flex-1 w-full space-y-1">
              {[
                { label: "Custo DIRPF",    val: totalCusto,            pct: pctCusto,     color: "#3B82F6" },
                { label: "Ganho líquido",  val: totalGanhoLivre,       pct: pctGanhoLivre,color: "#16A34A" },
                { label: "IR do espólio",  val: totalIr,               pct: pctIr,        color: "#DC2626" },
                { label: "Economia legal", val: totalEconomiaReducoes, pct: pctEconomia,  color: "#0EA5E9" },
                { label: "Isentos/outros", val: totalOutrosBens,       pct: pctOutros,    color: "#94A3B8" },
              ].map((leg) => {
                const isHovered = hoveredSegment?.label === leg.label;
                return (
                  <div
                    key={leg.label}
                    className="flex items-center gap-3 py-2 px-2 transition-colors cursor-default"
                    style={{
                      background: isHovered ? "var(--blue-10)" : "transparent",
                      borderRadius: "var(--r-sm)",
                    }}
                    onMouseEnter={() => setHoveredSegment({ label: leg.label, value: leg.val, color: leg.color })}
                    onMouseLeave={() => setHoveredSegment(null)}
                  >
                    <div className="w-3 h-3 rounded-sm shrink-0" style={{ background: leg.color }} />
                    <span className="flex-1 text-sm font-medium" style={{ color: "var(--navy)" }}>
                      {leg.label}
                    </span>
                    <span className="text-xs text-muted tabular-nums" style={{ fontFamily: "var(--font-mono)" }}>
                      {leg.pct.toFixed(1)}%
                    </span>
                    <span
                      className="text-sm font-bold tabular-nums w-32 text-right"
                      style={{ color: "var(--navy)" }}
                    >
                      {moeda(leg.val)}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </Card>
      )}

      {/* Simulador local — COLAPSADO por padrão */}
      {totalValorEstimado > 0 && (
        <details
          className="card"
          style={{ padding: 0 }}
        >
          <summary
            className="cursor-pointer px-5 py-4 flex items-center gap-2 select-none"
            style={{ color: "var(--navy)", fontFamily: "var(--font-sans)", fontWeight: 600 }}
          >
            <Icon name="settings" size={14} className="text-muted" />
            Simulador de alíquotas (avançado)
            <span className="text-xs text-muted-2 font-normal ml-2">
              ITCMD · GCAP · Reforma Tributária
            </span>
          </summary>
          <div className="px-5 pb-5 pt-1 border-t" style={{ borderColor: "var(--border-solid)" }}>
            <SimuladorLocal totalValorEstimado={totalValorEstimado} totalBaseTributavel={totalBaseTributavel} totalIr={totalIr} />
          </div>
        </details>
      )}

      {/* Tabela IR por bem */}
      <Card title="IR por bem" padding={false}>
        <div className="overflow-x-auto">
          <table className="table-base">
            <thead>
              <tr>
                <th>Bem</th>
                <th>Regime</th>
                <th>Status</th>
                <th className="num">Ganho bruto</th>
                <th className="num">Base tributável</th>
                <th className="num">IR</th>
              </tr>
            </thead>
            <tbody>
              {bens.map((b, i) => {
                const r = b.resultado;
                const ganho = r.ganho_bruto ?? r.ganho_diferido;
                return (
                  <tr key={i}>
                    <td className="font-medium">{b.identificacao}</td>
                    <td className="text-muted text-xs">{b.regime}</td>
                    <td>
                      {r.status === "Conclusivo" ? (
                        <span className="badge-ok">OK</span>
                      ) : (
                        <span className="badge-warn">PEND</span>
                      )}
                    </td>
                    <td className="num">{moeda(ganho)}</td>
                    <td className="num">{moeda(r.base_tributavel)}</td>
                    <td className="num font-semibold" style={{ color: "var(--navy)" }}>
                      {moeda(r.ir_espolio)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Detalhamento e isenções colapsadas */}
      <details className="card" style={{ padding: 0 }}>
        <summary
          className="cursor-pointer px-5 py-4 flex items-center gap-2 select-none"
          style={{ color: "var(--navy)", fontFamily: "var(--font-sans)", fontWeight: 600 }}
        >
          <Icon name="documents" size={14} className="text-muted" />
          Detalhamento por bem
        </summary>
        <div className="px-5 pb-5 pt-1 border-t flex flex-col gap-3" style={{ borderColor: "var(--border-solid)" }}>
          {bens.map((b, i) => {
            const r = b.resultado;
            const ok = r.status === "Conclusivo";
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
                  <span style={{ color: ok ? "var(--success)" : "var(--warning)" }}>
                    <Icon name={ok ? "check" : "alert"} size={12} strokeWidth={2.5} />
                  </span>
                  <span className="font-semibold">{b.identificacao}</span>
                  <span className="text-xs text-muted">— {b.regime}</span>
                </summary>
                <div className="p-3 space-y-3 text-sm border-t" style={{ color: "var(--text)", borderColor: "var(--border-solid)" }}>
                  {b.pendencias.length > 0 && (
                    <div
                      className="p-3"
                      style={{
                        background: "var(--danger-10)",
                        borderLeft: "3px solid var(--danger)",
                        borderRadius: "var(--r-sm)",
                      }}
                    >
                      <p className="font-semibold mb-1" style={{ color: "var(--danger)" }}>
                        Pendências:
                      </p>
                      <ul className="list-disc pl-5 space-y-0.5">
                        {b.pendencias.map((p, j) => (
                          <li key={j}>{p}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {r.nota && (
                    <div
                      className="p-3"
                      style={{
                        background: "var(--info-10)",
                        borderLeft: "3px solid var(--info)",
                        borderRadius: "var(--r-sm)",
                        color: "var(--navy)",
                      }}
                    >
                      {r.nota}
                    </div>
                  )}
                  {r.fatores_reducao?.aplicavel && (
                    <div>
                      <p className="font-semibold mb-1">Memória dos fatores de redução</p>
                      <ul className="text-xs space-y-1 text-muted">
                        {r.fatores_reducao.memoria.map((p, j) => (
                          <li key={j}>• {p}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {r.ir_herdeiros && (
                    <div>
                      <p className="font-semibold mb-2">Rateio por herdeiro</p>
                      <table className="table-base">
                        <thead>
                          <tr>
                            <th>Herdeiro</th>
                            <th className="num">Fração</th>
                            <th className="num">Ganho</th>
                            <th className="num">Base</th>
                            <th className="num">IR</th>
                          </tr>
                        </thead>
                        <tbody>
                          {Object.entries(r.ir_herdeiros).map(([nome, d]) => (
                            <tr key={nome}>
                              <td>{nome}</td>
                              <td className="num">{d.fracao.toFixed(4)}</td>
                              <td className="num">{moeda(d.ganho)}</td>
                              <td className="num">{moeda(d.base_tributavel)}</td>
                              <td className="num font-semibold">{moeda(d.ir)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </details>
            );
          })}
        </div>
      </details>

      {state.recomendacoes && state.recomendacoes.length > 0 && (
        <details className="card" style={{ padding: 0 }}>
          <summary
            className="cursor-pointer px-5 py-4 flex items-center gap-2 select-none"
            style={{ color: "var(--navy)", fontFamily: "var(--font-sans)", fontWeight: 600 }}
          >
            <Icon name="chartBar" size={14} className="text-muted" />
            Comparativo de cenários legais
          </summary>
          <div className="border-t overflow-x-auto" style={{ borderColor: "var(--border-solid)" }}>
            <table className="table-base">
              <thead>
                <tr>
                  <th>Bem</th>
                  <th className="num">Pior cenário</th>
                  <th className="num">Recomendado</th>
                  <th>Recomendação</th>
                </tr>
              </thead>
              <tbody>
                {state.recomendacoes.map((rec) => {
                  const recomCusto =
                    rec.recomendado.ir_espolio + rec.recomendado.ir_herdeiros_futuro_estimado;
                  return (
                    <tr key={rec.bem}>
                      <td className="font-medium">{rec.bem}</td>
                      <td className="num">{moeda(recomCusto + rec.economia_vs_pior)}</td>
                      <td className="num font-semibold" style={{ color: "var(--success)" }}>
                        {moeda(recomCusto)}
                      </td>
                      <td className="text-xs text-muted">{rec.recomendado.descricao}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </details>
      )}

      {state.isencoes && state.isencoes.length > 0 && (
        <details className="card" style={{ padding: 0 }}>
          <summary
            className="cursor-pointer px-5 py-4 flex items-center gap-2 select-none"
            style={{ color: "var(--navy)", fontFamily: "var(--font-sans)", fontWeight: 600 }}
          >
            <Icon name="info" size={14} className="text-muted" />
            Isenções a verificar
            <span className="text-xs text-muted-2 font-normal ml-2">
              {state.isencoes.length} item(ns)
            </span>
          </summary>
          <div className="px-5 pb-5 pt-1 border-t space-y-2" style={{ borderColor: "var(--border-solid)" }}>
            {state.isencoes.map((v, i) => (
              <details
                key={i}
                className="overflow-hidden"
                style={{ border: "1px solid var(--border-solid)", borderRadius: "var(--r-sm)" }}
              >
                <summary
                  className="cursor-pointer px-3 py-2 text-sm flex items-center gap-2"
                  style={{ color: "var(--navy)" }}
                >
                  <span className="font-semibold">{v.bem}</span> — {v.isencao}
                  {v.elegivel_em_tese ? (
                    <span className="badge-info">elegível em tese</span>
                  ) : (
                    <span className="badge-warn">não elegível</span>
                  )}
                </summary>
                <div className="p-3 text-sm space-y-2 border-t" style={{ color: "var(--text)", borderColor: "var(--border-solid)" }}>
                  <p className="text-xs text-muted">{v.base_legal}</p>
                  {v.observacao && <p>{v.observacao}</p>}
                  {v.requisitos_a_confirmar.length > 0 && (
                    <ul className="list-none space-y-0.5">
                      {v.requisitos_a_confirmar.map((r, j) => (
                        <li key={j} className="flex items-start gap-2">
                          <span className="mt-0.5 text-muted-2">
                            <Icon name="minus" size={10} />
                          </span>
                          {r}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </details>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}

function SimuladorLocal({
  totalValorEstimado,
  totalBaseTributavel,
  totalIr,
}: {
  totalValorEstimado: number;
  totalBaseTributavel: number;
  totalIr: number;
}) {
  const [itcmd, setItcmd] = useState(4.0);
  const [gcap, setGcap] = useState(15.0);

  const baseTotal = totalValorEstimado * 0.04 + totalIr;
  const simTotal = totalValorEstimado * (itcmd / 100) + totalBaseTributavel * (gcap / 100);
  const diff = simTotal - baseTotal;

  return (
    <div className="space-y-5 mt-4 slider-container">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <div className="flex justify-between items-center mb-2">
            <label className="text-eyebrow" htmlFor="slider-itcmd">
              Alíquota ITCMD
            </label>
            <span className="text-xs font-bold tabular-nums" style={{ color: "var(--info)", fontFamily: "var(--font-mono)" }}>
              {itcmd.toFixed(1)}%
            </span>
          </div>
          <input
            id="slider-itcmd"
            type="range"
            min="2.0"
            max="8.0"
            step="0.5"
            value={itcmd}
            onChange={(e) => setItcmd(parseFloat(e.target.value))}
            className="w-full"
          />
          <div className="flex justify-between text-[10px] mt-1 tabular-nums" style={{ fontFamily: "var(--font-mono)", color: "var(--muted-2)" }}>
            <span>2,0%</span>
            <span>4,0% (padrão)</span>
            <span>8,0%</span>
          </div>
        </div>

        <div>
          <div className="flex justify-between items-center mb-2">
            <label className="text-eyebrow" htmlFor="slider-gcap">
              Alíquota GCAP
            </label>
            <span className="text-xs font-bold tabular-nums" style={{ color: "var(--sky)", fontFamily: "var(--font-mono)" }}>
              {gcap.toFixed(1)}%
            </span>
          </div>
          <input
            id="slider-gcap"
            type="range"
            min="15.0"
            max="22.5"
            step="0.5"
            value={gcap}
            onChange={(e) => setGcap(parseFloat(e.target.value))}
            className="w-full"
          />
          <div className="flex justify-between text-[10px] mt-1 tabular-nums" style={{ fontFamily: "var(--font-mono)", color: "var(--muted-2)" }}>
            <span>15,0%</span>
            <span>22,5%</span>
          </div>
        </div>
      </div>

      <div className="overflow-hidden text-xs" style={{ border: "1px solid var(--border-solid)", borderRadius: "var(--r-sm)" }}>
        <table className="table-base">
          <thead>
            <tr>
              <th>Imposto</th>
              <th className="num">Apurado</th>
              <th className="num">Simulado</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="font-semibold text-muted">ITCMD (est.)</td>
              <td className="num text-muted-2 italic">simul.</td>
              <td className="num font-bold tabular-nums" style={{ color: "var(--blue)" }}>
                {moeda(totalValorEstimado * (itcmd / 100))}
              </td>
            </tr>
            <tr>
              <td className="font-semibold text-muted">GCAP (IR)</td>
              <td className="num tabular-nums">{moeda(totalIr)}</td>
              <td className="num font-bold tabular-nums" style={{ color: "var(--sky)" }}>
                {moeda(totalBaseTributavel * (gcap / 100))}
              </td>
            </tr>
            <tr style={{ background: "var(--blue-10)" }}>
              <td className="font-bold" style={{ color: "var(--navy)" }}>Total geral</td>
              <td className="num font-bold tabular-nums">{moeda(baseTotal)}</td>
              <td className="num font-bold tabular-nums" style={{ color: "var(--blue)" }}>{moeda(simTotal)}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="flex justify-center">
        {diff > 0 ? (
          <span className="badge-warn">Divergência: +{moeda(diff)} (alíquotas mais severas)</span>
        ) : diff < 0 ? (
          <span className="badge-ok">Diferença: -{moeda(Math.abs(diff))} (otimizado)</span>
        ) : (
          <span className="badge-info">Custo fiscal idêntico ao cenário base</span>
        )}
      </div>

      <p className="text-xs text-muted">
        <strong style={{ color: "var(--warning)" }}>ITCMD ilustrativo.</strong> Imposto estadual (2% a 8%) varia
        por Estado. Este simulador usa valor estimado como proxy — não substitui o cálculo oficial junto à
        SEFAZ.
      </p>
    </div>
  );
}
