import { useEffect, useState } from "react";
import { relatorio, laudoXlsx, laudoReactive } from "../api";
import { useEspolio } from "../state";
import { Card } from "../components/ui/Card";
import { SkeletonCard } from "../components/ui/Skeleton";
import { Icon } from "../components/ui/icons";

function triggerDownload(blob: Blob, nome: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = nome;
  a.click();
  URL.revokeObjectURL(url);
}

function slugify(s: string) {
  return s.replace(/\s+/g, "_").replace(/[^\w_]/g, "").slice(0, 40);
}

export function RelatorioTab() {
  const { state, setRelatorio } = useEspolio();
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [dlXlsx, setDlXlsx] = useState(false);
  const [dlPdf, setDlPdf] = useState(false);

  useEffect(() => {
    if (!state.espolio || state.relatorio !== null) return;
    setCarregando(true);
    setErro(null);
    relatorio(state.espolio)
      .then((r) => setRelatorio(r.texto))
      .catch((e: Error) => setErro(e.message))
      .finally(() => setCarregando(false));
  }, [state.espolio, state.relatorio, setRelatorio]);

  const baixarTxt = () => {
    if (!state.relatorio || !state.espolio) return;
    const blob = new Blob([state.relatorio], { type: "text/plain;charset=utf-8" });
    triggerDownload(blob, `relatorio_${slugify(state.espolio.nome)}.txt`);
  };

  const baixarXlsx = async () => {
    if (!state.espolio) return;
    setDlXlsx(true);
    try {
      const blob = await laudoXlsx(state.espolio);
      triggerDownload(blob, `laudo_${slugify(state.espolio.nome)}.xlsx`);
    } catch (e: unknown) {
      alert((e as Error).message ?? "Erro ao gerar XLSX");
    } finally {
      setDlXlsx(false);
    }
  };

  const baixarPdfReactive = async () => {
    if (!state.espolio) return;
    setDlPdf(true);
    try {
      const blob = await laudoReactive(state.espolio);
      triggerDownload(blob, `laudo_reativo_${slugify(state.espolio.nome)}.pdf`);
    } catch (e: unknown) {
      alert((e as Error).message ?? "Erro ao gerar PDF");
    } finally {
      setDlPdf(false);
    }
  };

  if (erro)
    return (
      <Card title="Erro na geração do relatório">
        <p className="text-sm" style={{ color: "var(--danger)" }}>
          {erro}
        </p>
      </Card>
    );

  if (carregando || !state.relatorio)
    return (
      <div className="flex flex-col gap-4">
        <SkeletonCard lines={4} />
        <SkeletonCard lines={8} />
      </div>
    );

  return (
    <div className="flex flex-col gap-4">
      <Card title="Relatório textual" subtitle="Gerado pelo motor de apuração determinístico — sem inferências da IA.">
        <div className="flex flex-wrap gap-2 mb-4">
          <button className="btn-ghost text-xs" onClick={baixarTxt}>
            <Icon name="download" size={12} />
            Baixar .txt
          </button>
          <button className="btn-primary text-xs" onClick={() => void baixarXlsx()} disabled={dlXlsx}>
            {dlXlsx ? <Icon name="loader" size={12} /> : <Icon name="download" size={12} />}
            Baixar .xlsx
          </button>
          <button className="btn-primary text-xs" onClick={() => void baixarPdfReactive()} disabled={dlPdf}>
            {dlPdf ? <Icon name="loader" size={12} /> : <Icon name="download" size={12} />}
            Baixar .pdf reativo
          </button>
        </div>

        <pre
          className="text-xs whitespace-pre-wrap p-4 max-h-[60vh] overflow-y-auto leading-relaxed"
          style={{
            background: "var(--surface-elev)",
            border: "1px solid var(--border-solid)",
            borderRadius: "var(--r-sm)",
            fontFamily: "var(--font-mono)",
            color: "var(--text)",
          }}
        >
          {state.relatorio}
        </pre>
      </Card>

      <div
        className="p-3 text-xs"
        style={{
          background: "var(--surface-elev)",
          border: "1px solid var(--border-solid)",
          borderLeft: "3px solid var(--muted-2)",
          borderRadius: "var(--r-sm)",
          color: "var(--text-2)",
        }}
      >
        <strong className="text-eyebrow flex items-center gap-1.5 mb-1" style={{ color: "var(--warning)" }}>
          <Icon name="alert" size={11} strokeWidth={2.5} />
          Aviso
        </strong>
        Relatório auxiliar técnico. Antes da entrega à RFB, deve ser revisado por contador (CRC) e advogado
        (OAB). Em caso de divergência com o GCAP oficial, prevalece o GCAP.
      </div>
    </div>
  );
}
