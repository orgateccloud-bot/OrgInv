<script src="https://cdn.tailwindcss.com"></script>

# 🔬 Exemplo Interativo: Simulador Forense de Risco de Autuação

Este é um documento interativo (`exemplo_reactive.md`) criado para demonstrar as capacidades da extensão **Reactive MD**. 

> [!TIP]
> **Como visualizar este documento:**
> 1. Certifique-se de ter a extensão **Reactive MD** instalada no VS Code.
> 2. Abra a paleta de comandos do VS Code (`Ctrl+Shift+P` ou `Cmd+Shift+P`).
> 3. Digite `Reactive MD: Open Preview` ou abra o Preview padrão do VS Code para Markdown (`Ctrl+K V` ou `Cmd+K V`).

---

## ⚖️ Simulador de Probabilidade de Autuação

O componente interativo abaixo calcula a probabilidade matemática de autuação fiscal com base em fatores de risco de conformidade e o imposto simulado sob as regras atuais vs. a Reforma Tributária.

```jsx live
function SimuladorForense() {
  const [incongruencias, setIncongruencias] = React.useState(2);
  const [valorBens, setValorBens] = React.useState(1500000);
  const [historicoDirpf, setHistoricoDirpf] = React.useState(false);

  // Cálculo da Probabilidade de Autuação (Regra Determinística da Persona @Gama)
  const calcularRisco = () => {
    let score = incongruencias * 20;
    if (!historicoDirpf) score += 30;
    return Math.min(score, 99);
  };

  // Comparação de Regimes Tributários (Persona @Sigma)
  const gcapAtual = (valorBens * 0.15); // Alíquota fixa simulada de 15%
  const ibsCbsFuturo = (valorBens * 0.265); // Alíquota simulada de 26.5% no novo regime

  const risco = calcularRisco();

  return (
    <div className="p-6 bg-slate-900 text-slate-100 rounded-xl border border-white/10 shadow-2xl font-sans">
      <h3 className="m-0 mb-4 text-sky-400 text-lg font-semibold flex items-center gap-2">
        <span>🔍</span> Painel de Simulação Forense (Tailwind CSS)
      </h3>

      {/* Controles */}
      <div className="flex flex-col gap-3 mb-5">
        <div>
          <label className="block mb-1 text-xs text-slate-400 font-medium">
            Quantidade de Incongruências Operacionais:
          </label>
          <input 
            type="number" 
            min="0" 
            max="5"
            value={incongruencias} 
            onChange={e => setIncongruencias(Math.max(0, Number(e.target.value)))}
            className="w-full p-2 rounded-md border border-slate-700 bg-slate-950 text-slate-100 focus:outline-none focus:ring-2 focus:ring-sky-500 text-sm"
          />
        </div>

        <div>
          <label className="block mb-1 text-xs text-slate-400 font-medium">
            Valor Total dos Bens sob Análise (R$):
          </label>
          <input 
            type="number" 
            step="100000"
            value={valorBens} 
            onChange={e => setValorBens(Number(e.target.value))}
            className="w-full p-2 rounded-md border border-slate-700 bg-slate-950 text-slate-100 focus:outline-none focus:ring-2 focus:ring-sky-500 text-sm"
          />
        </div>

        <div className="flex items-center gap-2 mt-1">
          <input 
            type="checkbox" 
            id="dirpf" 
            checked={historicoDirpf} 
            onChange={e => setHistoricoDirpf(e.target.checked)}
            className="w-4 h-4 rounded text-sky-600 focus:ring-sky-500 focus:ring-2 bg-slate-950 border-slate-700 cursor-pointer"
          />
          <label htmlFor="dirpf" className="text-sm text-slate-200 cursor-pointer select-none">
            Possui Histórico de Custo na DIRPF
          </label>
        </div>
      </div>

      {/* Métricas Resultantes */}
      <div className="grid grid-cols-2 gap-3 border-t border-white/10 pt-4">
        <div className="bg-white/5 p-3 rounded-lg border border-white/5">
          <span className="text-xs text-slate-400 block font-medium">Risco de Autuação</span>
          <div className={`text-2xl font-bold mt-1 ${risco > 50 ? 'text-red-400' : 'text-emerald-400'}`}>
            {risco}%
          </div>
        </div>

        <div className="bg-white/5 p-3 rounded-lg border border-white/5">
          <span className="text-xs text-slate-400 block font-medium">Diferença Reforma (IBS/CBS)</span>
          <div className="text-xl font-bold mt-1 text-orange-400">
            + R$ {(ibsCbsFuturo - gcapAtual).toLocaleString('pt-BR', { maximumFractionDigits: 0 })}
          </div>
        </div>
      </div>

      <div className="mt-4 text-[11px] text-slate-500 text-center">
        Cenário Atual (GCAP 15%): R$ {gcapAtual.toLocaleString('pt-BR')} | Novo Cenário (26.5%): R$ {ibsCbsFuturo.toLocaleString('pt-BR')}
      </div>
    </div>
  );
}
```
```

---

## 📈 Benefícios do Reactive MD em Laudos Técnicos

* **Relatórios Dinâmicos:** Em vez de screenshots de tabelas que ficam obsoletas, o laudo se torna a própria calculadora operacional.
* **Integridade dos Dados:** Os valores exibidos são gerados por fórmulas e estados transparentes descritos diretamente no código.
* **Facilidade de Compartilhamento:** Como é apenas um arquivo `.md` simples, ele pode ser compartilhado em qualquer repositório Git e versionado de maneira limpa.
