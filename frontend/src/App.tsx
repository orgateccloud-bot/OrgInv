import { Header } from "./components/Header";
import { AuditFooter } from "./components/AuditFooter";
import { Tabs, type TabDef } from "./components/ui/Tabs";
import { ToastProvider } from "./components/ui/Toast";
import { Icon } from "./components/ui/icons";
import { StateProvider } from "./state";
import { EspolioTab } from "./tabs/EspolioTab";
import { DocumentosTab } from "./tabs/DocumentosTab";
import { BensTab } from "./tabs/BensTab";
import { ApuracaoTab } from "./tabs/ApuracaoTab";
import { RelatorioTab } from "./tabs/RelatorioTab";
import { AnaliseTab } from "./tabs/AnaliseTab";
import { LaudoTab } from "./tabs/LaudoTab";
import { AuthModal } from "./components/AuthModal";
import { AbrirEspolioModal } from "./components/AbrirEspolioModal";

const TABS: TabDef[] = [
  { id: "espolio",   label: "Espólio",    icon: <Icon name="user" size={14} />,        render: () => <EspolioTab /> },
  { id: "docs",      label: "Documentos", icon: <Icon name="documents" size={14} />,   render: () => <DocumentosTab /> },
  { id: "bens",      label: "Bens",       icon: <Icon name="clipboard" size={14} />,   render: () => <BensTab /> },
  { id: "apuracao",  label: "Apuração",   icon: <Icon name="calculator" size={14} />,  render: () => <ApuracaoTab /> },
  { id: "relatorio", label: "Relatório",  icon: <Icon name="fileText" size={14} />,    render: () => <RelatorioTab /> },
  { id: "ia",        label: "Análise",    icon: <Icon name="sparkles" size={14} />,    render: () => <AnaliseTab /> },
  { id: "laudo",     label: "Laudo",      icon: <Icon name="chartBar" size={14} />,    render: () => <LaudoTab /> },
];

function Shell() {
  return (
    <div className="h-full flex flex-col">
      <Header />
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-6xl mx-auto px-6 py-6">
          <Tabs tabs={TABS} initial="espolio" />
          <AuditFooter />
          <footer
            className="mt-8 pt-5 text-xs text-muted leading-relaxed"
            style={{ borderTop: "1px solid var(--border-solid)" }}
          >
            Software de apoio à auditoria.{" "}
            <strong className="text-text-2">
              Não substitui o juízo do contador e do advogado.
            </strong>{" "}
            Em caso de divergência com o GCAP oficial da RFB, prevalece o GCAP.
          </footer>
        </div>
      </main>
      <AuthModal />
      <AbrirEspolioModal />
    </div>
  );
}

export default function App() {
  return (
    <StateProvider>
      <ToastProvider>
        <Shell />
      </ToastProvider>
    </StateProvider>
  );
}
