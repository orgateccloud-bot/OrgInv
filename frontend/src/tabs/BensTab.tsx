import { useState } from "react";
import { useEspolio } from "../state";
import { OPCOES_ART23, REGIMES, type Bem } from "../types";
import { moeda } from "../lib/fmt";
import { Field } from "../components/ui/Field";
import { Icon } from "../components/ui/icons";

const REGIME_SHORT: Record<string, string> = {
  "Transmissão a herdeiro (partilha)":      "Partilha",
  "Venda pelo espólio a terceiro":           "Venda pelo espólio",
  "Cessão de direitos hereditários":         "Cessão",
  "Fora do monte partilhável":               "Fora do monte",
  "Indeterminado — requer classificação":    "Indeterminado",
};

export function BensTab() {
  const { state, patchEspolio } = useEspolio();
  const e = state.espolio;
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
  if (!e) return null;

  const setBem = (i: number, patch: Partial<Bem>) => {
    const novos = e.bens.map((b, idx) => (idx === i ? { ...b, ...patch } : b));
    patchEspolio({ bens: novos });
  };
  const addBem = () => {
    patchEspolio({
      bens: [
        ...e.bens,
        {
          identificacao: "Novo bem",
          matricula: "",
          regime: "Indeterminado — requer classificação",
          opcao: "Não aplicável a este regime",
          eh_imovel: true,
          custo_aquisicao_dirpf: null,
          data_aquisicao: null,
          valor_partilha: null,
          valor_venda: null,
          data_operacao: null,
        },
      ],
    });
    setExpandedIdx(e.bens.length);
  };
  const delBem = (i: number) => patchEspolio({ bens: e.bens.filter((_, idx) => idx !== i) });

  const indeterminadosCount = e.bens.filter(
    (b) => b.regime === "Indeterminado — requer classificação",
  ).length;

  const totalFracoes = e.herdeiros.reduce((s, h) => s + (h.fracao_monte || 0), 0);
  const fracaoDesbalanceada = e.herdeiros.length > 0 && Math.abs(totalFracoes - 1.0) > 0.0001;

  const bensSemValor = e.bens.filter((b) => {
    if (b.regime === "Transmissão a herdeiro (partilha)") {
      return b.valor_partilha === null || b.valor_partilha === undefined;
    }
    if (b.regime === "Venda pelo espólio a terceiro" || b.regime === "Cessão de direitos hereditários") {
      return b.valor_venda === null || b.valor_venda === undefined;
    }
    return false;
  });

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <span className="text-eyebrow">Catálogo de Bens</span>
          <div className="flex items-center gap-2 mt-1">
            <h2
              className="leading-tight"
              style={{
                fontFamily: "var(--font-sans)",
                fontWeight: 800,
                fontSize: "1.75rem",
                letterSpacing: "-0.02em",
                color: "var(--navy)",
              }}
            >
              Bens do espólio
            </h2>
            <span className="badge-info">{e.bens.length}</span>
            {indeterminadosCount > 0 && (
              <span className="badge-warn" title="Bens com regime ainda não classificado">
                {indeterminadosCount} indet.
              </span>
            )}
          </div>
          <p className="text-sm mt-2 text-muted leading-snug max-w-2xl">
            Cada bem é classificado por regime. Use <strong style={{ color: "var(--navy)" }}>Indeterminado</strong>{" "}
            quando faltar fato — o motor bloqueia a apuração.
          </p>
        </div>
        <button className="btn-primary shrink-0" onClick={addBem}>
          <Icon name="plus" size={14} />
          Adicionar bem
        </button>
      </div>

      {/* Validation banners — Aurora aviso style */}
      {(fracaoDesbalanceada || bensSemValor.length > 0) && (
        <div
          className="flex flex-col gap-2.5 p-4"
          style={{
            background: "var(--warning-10)",
            borderLeft: "3px solid var(--warning)",
            border: "1px solid var(--warning-20)",
            borderRadius: "var(--r-md)",
          }}
        >
          <h3
            className="text-eyebrow flex items-center gap-2 m-0"
            style={{ color: "var(--warning)" }}
          >
            <Icon name="alert" size={12} strokeWidth={2.5} />
            Alertas de inconsistência (validação em tempo real)
          </h3>
          <ul className="text-xs space-y-1.5 list-disc pl-5 m-0" style={{ color: "var(--navy)" }}>
            {fracaoDesbalanceada && (
              <li>
                <strong>Partilha desbalanceada:</strong> A soma das frações dos herdeiros é{" "}
                <span className="tabular-nums font-bold" style={{ color: "var(--warning)" }}>
                  {(totalFracoes * 100).toFixed(2)}%
                </span>
                . A soma exata deve ser 100,00%. Ajuste na aba lateral.
              </li>
            )}
            {bensSemValor.length > 0 && (
              <li>
                <strong>Valores ausentes:</strong> Existem {bensSemValor.length} bem(ns) pendente(s) de valor
                necessário para o regime:
                <ul className="list-inside list-disc pl-4 mt-1 font-normal text-muted">
                  {bensSemValor.map((b, idx) => (
                    <li key={idx}>
                      {b.identificacao || `Sem nome #${idx + 1}`} (Regime:{" "}
                      {REGIME_SHORT[b.regime] || b.regime})
                    </li>
                  ))}
                </ul>
              </li>
            )}
          </ul>
        </div>
      )}

      {/* Empty state */}
      {e.bens.length === 0 && (
        <div className="card p-10 text-center">
          <div
            className="w-14 h-14 mx-auto mb-3 flex items-center justify-center"
            style={{
              background: "var(--blue-10)",
              border: "1px solid var(--blue-20)",
              borderRadius: "var(--r-md)",
              color: "var(--blue)",
            }}
          >
            <Icon name="clipboard" size={24} />
          </div>
          <h3 className="font-semibold mb-1" style={{ color: "var(--navy)" }}>
            Nenhum bem cadastrado
          </h3>
          <p className="text-sm text-muted max-w-md mx-auto mb-4">
            Adicione manualmente ou importe via <strong style={{ color: "var(--navy)" }}>Documentos</strong> com
            Claude Sonnet.
          </p>
          <button className="btn-primary" onClick={addBem}>
            <Icon name="plus" size={14} />
            Adicionar primeiro bem
          </button>
        </div>
      )}

      {/* Lista de bens */}
      {e.bens.length > 0 && (
        <div className="flex flex-col gap-2.5">
          {e.bens.map((b, i) => (
            <BemRow
              key={i}
              bem={b}
              index={i}
              expanded={expandedIdx === i}
              onToggle={() => setExpandedIdx(expandedIdx === i ? null : i)}
              onChange={(patch) => setBem(i, patch)}
              onDelete={() => delBem(i)}
            />
          ))}
        </div>
      )}

      {/* Regime help */}
      <details
        className="p-4"
        style={{
          background: "var(--info-10)",
          border: "1px solid var(--blue-20)",
          borderRadius: "var(--r-md)",
        }}
      >
        <summary
          className="cursor-pointer text-sm font-semibold flex items-center gap-2"
          style={{ color: "var(--blue)" }}
        >
          <Icon name="info" size={14} />
          Como classificar o regime
        </summary>
        <div className="mt-3 text-sm space-y-2" style={{ color: "var(--text)" }}>
          <p>
            <strong>Transmissão a herdeiro</strong> — bem partilhado (não vendido); herdeiro herda o direito a FR1/FR2.
          </p>
          <p>
            <strong>Venda pelo espólio</strong> — espólio aliena a terceiro antes da partilha; sem diferimento; FR1/FR2 se imóvel.
          </p>
          <p>
            <strong>Cessão de direitos hereditários</strong> — herdeiros vendem antes da partilha; IR proporcional ao quinhão.
          </p>
          <p>
            <strong>Fora do monte</strong> — bem não pertencia ao de cujus na data do óbito.
          </p>
          <p>
            <strong>Indeterminado</strong> — faltam fatos; bloqueia apuração até classificação.
          </p>
        </div>
      </details>
    </div>
  );
}

function BemRow({
  bem: b,
  index: i,
  expanded,
  onToggle,
  onChange,
  onDelete,
}: {
  bem: Bem;
  index: number;
  expanded: boolean;
  onToggle: () => void;
  onChange: (patch: Partial<Bem>) => void;
  onDelete: () => void;
}) {
  const indet = b.regime === "Indeterminado — requer classificação";
  const valorPrincipal = b.valor_venda ?? b.valor_partilha;

  return (
    <div className="bem-row flex-col items-stretch !grid-cols-1 sm:!grid sm:!grid-cols-[auto_1fr_auto] sm:items-center">
      <div className="hidden sm:flex">
        <div
          className="w-9 h-9 flex items-center justify-center text-xs font-bold shrink-0"
          style={{
            background: indet ? "var(--warning-10)" : "var(--blue-10)",
            color: indet ? "var(--warning)" : "var(--blue)",
            borderRadius: "var(--r-sm)",
            fontFamily: "var(--font-mono)",
          }}
        >
          {String(i + 1).padStart(2, "0")}
        </div>
      </div>

      <button
        type="button"
        onClick={onToggle}
        className="flex-1 min-w-0 text-left flex items-center gap-3"
        aria-expanded={expanded}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold truncate" style={{ color: "var(--navy)" }}>
              {b.identificacao || "(sem nome)"}
            </span>
            {b.matricula && (
              <span className="text-mono-sm text-muted">m. {b.matricula}</span>
            )}
            <span className="text-xs text-muted-2 flex items-center gap-1">
              {b.eh_imovel ? "imóvel" : "móvel"}
            </span>
          </div>
          <div className="flex items-center gap-2 mt-1">
            {indet ? (
              <span className="badge-warn">{REGIME_SHORT[b.regime] ?? b.regime}</span>
            ) : (
              <span className="badge-ok">{REGIME_SHORT[b.regime] ?? b.regime}</span>
            )}
            {valorPrincipal !== null && (
              <span className="text-xs text-muted tabular-nums">
                {moeda(valorPrincipal)}
              </span>
            )}
          </div>
        </div>
        <span
          className="text-muted shrink-0"
          aria-hidden
          style={{
            transform: expanded ? "rotate(180deg)" : "none",
            transition: "transform 0.2s var(--easing)",
          }}
        >
          <Icon name="chevronDown" size={14} />
        </span>
      </button>

      <button
        type="button"
        onClick={onDelete}
        className="btn-danger shrink-0 hidden sm:flex"
        aria-label={`Remover bem ${b.identificacao || i + 1}`}
      >
        <Icon name="trash" size={12} />
      </button>

      {expanded && (
        <div
          className="col-span-full mt-3 pt-3 fade-in"
          style={{ borderTop: "1px solid var(--border-solid)" }}
        >
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <Field label="Identificação" className="md:col-span-2">
              <input
                className="input-base text-sm"
                value={b.identificacao}
                onChange={(ev) => onChange({ identificacao: ev.target.value })}
              />
            </Field>
            <Field label="Matrícula">
              <input
                className="input-base text-sm"
                value={b.matricula}
                onChange={(ev) => onChange({ matricula: ev.target.value })}
              />
            </Field>
            <Field label="Regime" className="md:col-span-2">
              <select
                className="input-base text-sm"
                value={b.regime}
                onChange={(ev) => onChange({ regime: ev.target.value as Bem["regime"] })}
              >
                {REGIMES.map((r) => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </Field>
            <Field label="Opção art. 23">
              <select
                className="input-base text-sm"
                value={b.opcao}
                onChange={(ev) => onChange({ opcao: ev.target.value as Bem["opcao"] })}
              >
                {OPCOES_ART23.map((o) => (
                  <option key={o} value={o}>{o}</option>
                ))}
              </select>
            </Field>

            <Field label="Custo DIRPF">
              <input
                type="number"
                step="0.01"
                className="input-base text-sm num"
                value={b.custo_aquisicao_dirpf ?? ""}
                onChange={(ev) =>
                  onChange({
                    custo_aquisicao_dirpf:
                      ev.target.value === "" ? null : parseFloat(ev.target.value),
                  })
                }
              />
            </Field>
            <Field label="Aquisição">
              <input
                type="date"
                className="input-base text-sm"
                value={b.data_aquisicao ?? ""}
                onChange={(ev) => onChange({ data_aquisicao: ev.target.value || null })}
              />
            </Field>
            <Field label="Valor partilha">
              <input
                type="number"
                step="0.01"
                className="input-base text-sm num"
                value={b.valor_partilha ?? ""}
                onChange={(ev) =>
                  onChange({
                    valor_partilha: ev.target.value === "" ? null : parseFloat(ev.target.value),
                  })
                }
              />
            </Field>

            <Field label="Valor venda">
              <input
                type="number"
                step="0.01"
                className="input-base text-sm num"
                value={b.valor_venda ?? ""}
                onChange={(ev) =>
                  onChange({
                    valor_venda: ev.target.value === "" ? null : parseFloat(ev.target.value),
                  })
                }
              />
            </Field>
            <Field label="Data operação">
              <input
                type="date"
                className="input-base text-sm"
                value={b.data_operacao ?? ""}
                onChange={(ev) => onChange({ data_operacao: ev.target.value || null })}
              />
            </Field>
            <Field label="Tipo">
              <label className="input-base text-sm flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={b.eh_imovel}
                  onChange={(ev) => onChange({ eh_imovel: ev.target.checked })}
                  style={{ accentColor: "var(--blue)" }}
                />
                <span style={{ color: "var(--text)" }}>
                  {b.eh_imovel ? "Imóvel" : "Móvel"}
                </span>
              </label>
            </Field>

            <button
              type="button"
              onClick={onDelete}
              className="btn-danger sm:hidden mt-1 col-span-full"
            >
              <Icon name="trash" size={12} />
              Remover bem
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
