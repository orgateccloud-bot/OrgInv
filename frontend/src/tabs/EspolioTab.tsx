import { useEspolio } from "../state";
import type { Herdeiro } from "../types";
import { Card } from "../components/ui/Card";
import { Field } from "../components/ui/Field";
import { Icon } from "../components/ui/icons";

export function EspolioTab() {
  const { state, patchEspolio, setApiKey } = useEspolio();
  const e = state.espolio;

  if (!e) {
    return (
      <Card title="Aguardando backend">
        <p className="text-sm text-muted">Conectando à API…</p>
      </Card>
    );
  }

  const setHerdeiro = (i: number, patch: Partial<Herdeiro>) => {
    const novos = e.herdeiros.map((h, idx) => (idx === i ? { ...h, ...patch } : h));
    patchEspolio({ herdeiros: novos });
  };
  const addHerdeiro = () =>
    patchEspolio({
      herdeiros: [...e.herdeiros, { nome: "", cpf: "", fracao_monte: 0, eh_meeiro: false }],
    });
  const delHerdeiro = (i: number) =>
    patchEspolio({ herdeiros: e.herdeiros.filter((_, idx) => idx !== i) });

  const somaFracoes = Math.round(e.herdeiros.reduce((s, h) => s + (h.fracao_monte || 0), 0) * 10000) / 10000;
  const somaOk = Math.abs(somaFracoes - 1) < 0.001;
  const pctFracoes = Math.min(100, Math.round(somaFracoes * 100));

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      {/* Coluna esquerda — Identificação */}
      <Card title="Identificação do espólio" className="lg:col-span-2">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Field
            label="Nome do falecido / espólio"
            className="md:col-span-2"
            hint={
              <span className="flex items-center gap-1" style={{ color: "var(--success)" }}>
                <Icon name="shield" size={10} strokeWidth={2.5} />
                Anonimizado antes do envio à IA
              </span>
            }
          >
            <input
              className="input-base"
              value={e.nome}
              onChange={(ev) => patchEspolio({ nome: ev.target.value })}
              placeholder="Nome do espólio"
            />
          </Field>

          <Field label="CPF do falecido">
            <input
              className="input-base"
              value={e.cpf_falecido}
              onChange={(ev) => patchEspolio({ cpf_falecido: ev.target.value })}
              placeholder="000.000.000-00"
            />
          </Field>

          <div />

          <Field label="Data do óbito">
            <input
              type="date"
              className="input-base"
              value={e.data_obito}
              onChange={(ev) => patchEspolio({ data_obito: ev.target.value })}
            />
          </Field>

          <Field label="Data da partilha">
            <input
              type="date"
              className="input-base"
              value={e.data_partilha}
              onChange={(ev) => patchEspolio({ data_partilha: ev.target.value })}
            />
          </Field>
        </div>
      </Card>

      {/* Coluna direita — API key */}
      <Card title="Claude Sonnet">
        <Field
          label="Anthropic API Key"
          hint="Necessária para Extração e Análise IA."
        >
          <input
            type="password"
            className="input-base"
            autoComplete="off"
            value={state.apiKey ?? ""}
            onChange={(ev) => setApiKey(ev.target.value.trim() || null)}
            placeholder="sk-ant-…"
          />
        </Field>
        <div className="mt-3">
          {state.apiKey ? (
            <span className="badge-ok">
              <Icon name="check" size={10} strokeWidth={2.5} />
              Chave configurada
            </span>
          ) : (
            <span className="badge-warn">
              <Icon name="alert" size={10} strokeWidth={2.5} />
              Sem chave — IA desativada
            </span>
          )}
        </div>
      </Card>

      {/* Herdeiros — full width */}
      <Card
        title="Herdeiros"
        subtitle={`${e.herdeiros.length} cadastrado(s)`}
        className="lg:col-span-3"
        actions={
          <button onClick={addHerdeiro} className="btn-ghost text-xs">
            <Icon name="plus" size={12} />
            Adicionar
          </button>
        }
      >
        {e.herdeiros.length === 0 ? (
          <div
            className="p-8 text-center text-sm text-muted"
            style={{
              border: "1px dashed var(--border-solid)",
              borderRadius: "var(--r-sm)",
            }}
          >
            Nenhum herdeiro cadastrado. Clique em <strong style={{ color: "var(--navy)" }}>Adicionar</strong>.
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="table-base">
                <thead>
                  <tr>
                    <th>Nome</th>
                    <th>CPF</th>
                    <th className="num">Fração</th>
                    <th>Meeiro</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {e.herdeiros.map((h, i) => (
                    <tr key={i}>
                      <td>
                        <input
                          className="input-base text-sm"
                          placeholder="Nome"
                          value={h.nome}
                          onChange={(ev) => setHerdeiro(i, { nome: ev.target.value })}
                          aria-label={`Nome herdeiro ${i + 1}`}
                        />
                      </td>
                      <td>
                        <input
                          className="input-base text-sm"
                          placeholder="000.000.000-00"
                          value={h.cpf}
                          onChange={(ev) => setHerdeiro(i, { cpf: ev.target.value })}
                          aria-label={`CPF herdeiro ${i + 1}`}
                        />
                      </td>
                      <td className="num" style={{ width: 120 }}>
                        <input
                          type="number"
                          step="0.0001"
                          min={0}
                          max={1}
                          className="input-base text-sm num"
                          value={h.fracao_monte}
                          onChange={(ev) =>
                            setHerdeiro(i, { fracao_monte: parseFloat(ev.target.value) || 0 })
                          }
                          aria-label={`Fração herdeiro ${i + 1}`}
                        />
                      </td>
                      <td style={{ width: 60 }}>
                        <input
                          type="checkbox"
                          checked={h.eh_meeiro}
                          onChange={(ev) => setHerdeiro(i, { eh_meeiro: ev.target.checked })}
                          style={{ accentColor: "var(--blue)" }}
                          aria-label={`Meeiro herdeiro ${i + 1}`}
                        />
                      </td>
                      <td style={{ width: 40 }}>
                        <button
                          onClick={() => delHerdeiro(i)}
                          className="btn-danger"
                          aria-label={`Remover herdeiro ${i + 1}`}
                        >
                          <Icon name="trash" size={11} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Progress bar — soma frações */}
            <div className="mt-4 max-w-md">
              <div className="flex items-center justify-between text-xs mb-1.5">
                <span className="text-eyebrow">Soma das frações</span>
                <span
                  className="font-bold tabular-nums flex items-center gap-1"
                  style={{ color: somaOk ? "var(--success)" : "var(--warning)" }}
                >
                  {(somaFracoes * 100).toFixed(2)}%
                  {somaOk ? (
                    <Icon name="check" size={12} strokeWidth={2.5} />
                  ) : (
                    <Icon name="alert" size={12} strokeWidth={2.5} />
                  )}
                </span>
              </div>
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{
                    width: `${pctFracoes}%`,
                    background: somaOk ? "var(--success)" : "var(--warning)",
                  }}
                />
              </div>
              {!somaOk && (
                <p className="text-xs text-muted mt-2">
                  A soma deve ser exatamente <strong style={{ color: "var(--navy)" }}>100,00%</strong>.
                </p>
              )}
            </div>
          </>
        )}
      </Card>
    </div>
  );
}
