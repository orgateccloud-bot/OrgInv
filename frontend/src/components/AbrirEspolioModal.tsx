import { useEffect, useState } from "react";
import { useEspolio } from "../state";
import { listarEspolios, carregarEspolio, apagarEspolio } from "../lib/espolioRepo";
import { useToast } from "./ui/Toast";
import { Icon } from "./ui/icons";
import type { DbEspolio } from "../lib/supabase";

export function AbrirEspolioModal() {
  const { state, setAbrirModalOpen, setEspolio } = useEspolio();
  const [espolios, setEspolios] = useState<DbEspolio[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  useEffect(() => {
    if (state.abrirModalOpen) {
      void fetchList();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.abrirModalOpen]);

  const fetchList = async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await listarEspolios();
      setEspolios(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  const handleCarregar = async (id: string) => {
    setLoading(true);
    try {
      const esp = await carregarEspolio(id);
      if (!esp) throw new Error("Espólio não encontrado.");
      setEspolio(esp, id);
      toast.push({
        tone: "ok",
        title: "Espólio carregado",
        description: `O espólio "${esp.nome}" foi carregado da nuvem.`,
      });
      setAbrirModalOpen(false);
    } catch (e) {
      toast.push({
        tone: "err",
        title: "Falha ao carregar",
        description: e instanceof Error ? e.message : String(e),
      });
    } finally {
      setLoading(false);
    }
  };

  const handleExcluir = async (id: string, nome: string) => {
    if (!confirm(`Deseja realmente excluir o espólio "${nome}"? Esta ação não pode ser desfeita.`)) {
      return;
    }
    setLoading(true);
    try {
      await apagarEspolio(id);
      toast.push({
        tone: "ok",
        title: "Espólio excluído",
        description: `O espólio "${nome}" foi excluído da nuvem.`,
      });
      if (state.activeEspolioId === id) {
        setEspolio(
          {
            nome: "",
            cpf_falecido: "",
            data_obito: new Date().toISOString().slice(0, 10),
            data_partilha: new Date().toISOString().slice(0, 10),
            herdeiros: [],
            bens: [],
          },
          null,
        );
      }
      await fetchList();
    } catch (e) {
      toast.push({
        tone: "err",
        title: "Falha ao excluir",
        description: e instanceof Error ? e.message : String(e),
      });
    } finally {
      setLoading(false);
    }
  };

  if (!state.abrirModalOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center fade-in p-4"
      style={{
        background: "rgba(15, 23, 42, 0.45)",
        backdropFilter: "blur(6px)",
        WebkitBackdropFilter: "blur(6px)",
      }}
    >
      <div
        className="card p-6 w-full max-w-lg flex flex-col gap-4 relative fade-up"
        style={{ maxHeight: "90vh" }}
      >
        <button
          type="button"
          onClick={() => setAbrirModalOpen(false)}
          className="absolute top-3 right-3 transition-colors p-1.5 rounded-md hover:bg-blue-10"
          style={{ color: "var(--muted)" }}
          aria-label="Fechar"
        >
          <Icon name="x" size={16} />
        </button>

        <div>
          <span className="text-eyebrow">Nuvem ORGATEC</span>
          <h3
            className="leading-tight mt-1"
            style={{ color: "var(--navy)", fontFamily: "var(--font-sans)", fontWeight: 700, fontSize: "1.25rem" }}
          >
            Abrir Espólio
          </h3>
          <p className="text-xs text-muted leading-snug mt-1">
            Selecione um espólio salvo na sua conta Supabase.
          </p>
        </div>

        <div className="flex-1 overflow-y-auto min-h-[200px] max-h-[400px] flex flex-col gap-2 pr-1">
          {loading && espolios.length === 0 ? (
            <div className="flex-1 flex items-center justify-center text-xs text-muted gap-2">
              <Icon name="loader" size={14} />
              Carregando lista…
            </div>
          ) : error ? (
            <div
              className="rounded-sm p-3 text-xs flex items-start gap-2"
              style={{
                background: "var(--danger-10)",
                border: "1px solid var(--danger-20)",
                color: "var(--danger)",
              }}
            >
              <Icon name="alert" size={14} strokeWidth={2.5} />
              {error}
            </div>
          ) : espolios.length === 0 ? (
            <div
              className="flex-1 flex flex-col items-center justify-center text-xs text-muted p-8 text-center gap-2"
              style={{
                border: "1px dashed var(--border-solid)",
                borderRadius: "var(--r-md)",
              }}
            >
              <Icon name="folder" size={24} className="text-muted-2" />
              <span>Nenhum espólio encontrado na nuvem.</span>
              <span className="text-[10px] text-muted-2">
                Salve o espólio atual primeiro usando "Salvar".
              </span>
            </div>
          ) : (
            espolios.map((esp) => (
              <div
                key={esp.id}
                className="flex items-center justify-between p-3 transition-colors"
                style={{
                  background: "var(--surface-elev)",
                  border: "1px solid var(--border-solid)",
                  borderRadius: "var(--r-md)",
                }}
              >
                <div className="flex flex-col gap-0.5 min-w-0">
                  <span className="font-semibold text-sm text-text truncate">
                    {esp.nome || "(Sem nome)"}
                  </span>
                  <div className="flex gap-2 text-[10px] text-muted-2">
                    <span>CPF: {esp.cpf_falecido || "N/A"}</span>
                    <span>•</span>
                    <span>
                      Óbito:{" "}
                      {esp.data_obito
                        ? new Date(esp.data_obito + "T12:00:00").toLocaleDateString("pt-BR")
                        : "N/A"}
                    </span>
                  </div>
                </div>
                <div className="flex gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={() => void handleCarregar(esp.id)}
                    className="btn-primary text-xs px-3 py-1.5"
                    disabled={loading}
                  >
                    Carregar
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleExcluir(esp.id, esp.nome)}
                    className="btn-danger"
                    disabled={loading}
                    title="Excluir da nuvem"
                    aria-label={`Excluir espólio ${esp.nome}`}
                  >
                    <Icon name="trash" size={12} />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
