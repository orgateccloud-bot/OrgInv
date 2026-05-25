# Mapeamento Frontend OrgAudi & Plano de Modernização

**Data:** 2026-05-24  •  **Versão atual:** 0.4.0  •  **Autor:** Warley Veloso / ORGATEC

> **STATUS — 2026-05-24 ✅ EXECUTADO**
>
> Todas as 6 fases foram implementadas em uma única sessão, seguidas por uma 7ª fase de **reestruturação total** após análise visual com Playwright.
> Estado final commitado em [github.com/orgateccloud-bot/OrgInv](https://github.com/orgateccloud-bot/OrgInv) (`8df90cd`).
>
> Pule para a [seção 10 — Execução](#10-execução-2026-05-24) para o relatório do que foi realmente entregue (que difere do plano original).

---

## 1. Resumo Executivo

O projeto possui hoje **três design systems coexistindo**, cada um nascido em contexto diferente:

| Sistema | Onde vive | Estética | Função |
|---|---|---|---|
| **A) "Bureau Blue" (React)** | `frontend/src/index.css` (722 linhas) + Tailwind | Glass morphism azul-ciano, Inter, gradientes em quase tudo | App operacional (Documentos, Bens, Apuração, Análise, Laudo) |
| **B) "Aurora" (Standalone)** | `login.html` (dark), `index_conciliacao.html` (light) | Glass morphism premium, Manrope + Instrument Serif + JetBrains Mono, aurora animada | Login + landing institucional |
| **C) "Oficial Laudo" (Print)** | `laudo_light.html`, `laudo_dark.html`, `laudo_html.py` | Playfair Display + Source Sans 3, navy #12345e, layout A4 | Documento final entregue ao cliente |

**Problema central:** o cliente entra pelo Aurora (login premium), opera no Bureau Blue (UI datada com emojis e gradientes em excesso) e recebe um laudo em Playfair (terceira identidade). A jornada é dissonante.

**Proposta:** Adotar **Aurora como design system mestre da aplicação React**, mantendo **Oficial Laudo intocado para o documento final** (é print-optimized e correto). Aposentar gradualmente o Bureau Blue.

---

## 2. Mapeamento Detalhado

### 2.1 Aplicação React (Bureau Blue) — estado atual

**Stack:** React 18 + TS strict + Vite 5 + Tailwind 3 + Supabase. Zero libs de UI third-party.

**Estrutura:**
```
frontend/src/
├── App.tsx                      # Shell + tab manager
├── index.css                    # 722 linhas — todo design system
├── state.tsx                    # Reducer (21 actions, espolio invalida derivados)
├── api.ts                       # 13 endpoints
├── types.ts                     # Espolio, Bem, Herdeiro, ResultadoBem
├── components/
│   ├── Header.tsx               # Gradient #172554→#06B6D4
│   ├── Sidebar.tsx              # w-72 glass, emojis 📂💾🔒✕
│   ├── Logo.tsx                 # img wrapper
│   ├── AuthModal.tsx            # Login Supabase
│   ├── AbrirEspolioModal.tsx    # Lista cloud
│   ├── SupabaseBadge.tsx        # Status chip
│   └── ui/
│       ├── Card, Field, Skeleton
│       ├── SegmentedControl, Tabs, Metric, Toast
├── tabs/
│   ├── DocumentosTab            # Dropzone PDF + Claude extrai
│   ├── BensTab                  # Form bens + validação real-time
│   ├── ApuracaoTab              # Hero IR + donut SVG interativo
│   ├── RelatorioTab             # Downloads TXT/XLSX/PDF
│   ├── AnaliseTab               # MdView streaming SSE
│   └── LaudoTab                 # Risk score + anomalias + cenários reforma
└── lib/ (fmt, supabase, espolioRepo)
```

**Tokens atuais (extraídos de tailwind.config.ts + index.css):**
- **Cores brand:** ember `#172554`, coal `#1E3A8A`, deep `#1D4ED8`, royal `#2563EB`, bright `#3B82F6`, sky `#60A5FA`, cyan `#06B6D4`, glow `#67E8F9`, aurora `#DBEAFE`, ash `#E0F2FE`
- **Surface:** bg `#F0F7FF`, panel `#FFFFFF`, muted `#E8F2FF`, glass `#F5FAFF`
- **Ink:** `#0F172A` / muted `#475569` / subtle `#94A3B8`
- **Raios:** card 16px, btn 10px, input 8px, pill 999px
- **Sombras:** glass (4 32px rgba 0.10), glass-lg, btn, focus (3px ring), glow cyan
- **Blur:** 16px sat 140% (cards), 22px (sidebar), 8px (input)
- **Animações:** aurora-drift-a/b/c/d (22-40s blobs), pulse-dot, skeleton-shimmer, toast-in, fade-in
- **Fonte:** Inter 300-700, mono ui-monospace
- **Display:** 2.75rem / 3.5rem (800)
- **Eyebrow:** 11px 700 uppercase tracking +0.16em

**Componentes (avaliação):**

| Componente | Decisão | Motivo |
|---|---|---|
| Header | **Refatorar** | Gradient excessivo, chips só em md+, falta densidade Aurora |
| Sidebar | **Refatorar** | Emojis 📂💾🔒, sem feedback de loading |
| Logo | Mantém | img simples, funciona |
| AuthModal | Migrar para Aurora dark | Login já é Aurora — manter consistência |
| AbrirEspolioModal | Mantém com restyle | UX sólida |
| SupabaseBadge | Mantém | Status icônico funciona |
| Card | **Refatorar tokens** | Glass excessivo (16px em tudo) |
| Field | Mantém | Padrão sólido label+children+error |
| Skeleton | Mantém | Shimmer ok |
| SegmentedControl | Mantém | a11y ok |
| Tabs | **Refatorar visual** | Estilo Aurora (mono labels) |
| Metric | **Refatorar tipografia** | Display deveria ser Instrument Serif |
| Toast | Mantém com ícones SVG | Substituir emojis ✓⚠✕ℹ |
| DocumentosTab | UX mantém, visual Aurora | Dropzone ok, restyle |
| BensTab | UX mantém, visual Aurora | Validação real-time é forte |
| ApuracaoTab | UX mantém, donut polir | Hero precisa Instrument Serif |
| RelatorioTab | **Add preview MD** | Falta syntax highlight |
| AnaliseTab | UX mantém | MdView ok |
| LaudoTab | **Expandir risk score** | Círculo pequeno demais |

**Pontos fracos identificados:**
- 13+ emojis como ícones (📥📋🧮📄🤖📊 nas tabs; 📂💾🔒✕ na sidebar)
- Glass morphism em **tudo** (inputs, buttons, panels, sidebar) — parece web3
- Gradientes lineares em demasia (header, todos botões, todos cards)
- Inline `style={{}}` disperso por toda parte (Header.tsx, modals)
- Sem `:root { --custom-properties }` — tokens vivem em Tailwind config e classes CSS misturados
- Hierarquia tipográfica fraca: display 2.75rem vs eyebrow 10px (sem h2/h3/h4)
- Labels não associadas a inputs (`htmlFor` ausente)
- BensTab validation = `<ul>` text amber (sem hierarquia visual)
- LaudoTab risk score circular SVG 100px (subdimensionado)
- Donut chart só mostra labels em hover (sem legenda lateral)

### 2.2 Aurora (Standalone HTMLs) — direção futura

**Filosofia:** dois extremos do mesmo universo
- **`login.html`** = dark ethereal (aurora animada, stars canvas, shooting stars)
- **`index_conciliacao.html`** = light bank-grade (mesh gradient pastel, glass premium)

**Tokens Aurora consolidados:**

```css
/* Tipografia triádica */
--font-sans:    'Manrope', system-ui;                  /* headings, body */
--font-serif:   'Instrument Serif', Georgia;            /* taglines, italics */
--font-mono:    'JetBrains Mono', ui-monospace;        /* labels, stats, code */

/* Paleta (light bank-grade) */
--navy:         #0F172A;
--blue:         #0052FF;    /* CTA primário */
--sky:          #0EA5E9;
--aurora-1:     #93C5FD;
--aurora-2:     #60A5FA;
--aurora-3:     #3B82F6;
--blue-10:      #DBEAFE;
--blue-20:      #BFDBFE;

/* Semânticos */
--success:      #16A34A;  --success-10: #DCFCE7;
--warning:      #D97706;  --warning-10: #FEF3C7;
--danger:       #DC2626;  --danger-10:  #FEE2E2;
--info:         #0B6BD4;  --info-10:    #DBEAFE;

/* Superfícies */
--bg:           #F0F7FF;
--surface:      rgba(255,255,255,0.72);
--text:         #0F172A;
--text-2:       #334155;
--muted:        #64748B;

/* Glass */
--glass-bg:     rgba(255,255,255,0.55);
--glass-blur:   blur(24px) saturate(180%);
--glass-blur-lg: blur(36px) saturate(200%);
--border:       rgba(186,230,253,0.5);

/* Raios */
--r-sm: 8px; --r-md: 14px; --r-lg: 22px; --r-xl: 32px;

/* Sombras estratificadas */
--shadow-sm: 0 1px 3px rgba(15,23,42,.06), 0 1px 2px rgba(15,23,42,.04);
--shadow-md: 0 4px 12px rgba(15,23,42,.08), 0 2px 4px rgba(15,23,42,.05);
--shadow-lg: 0 18px 50px rgba(15,23,42,.10), 0 4px 14px rgba(15,23,42,.05);
--shadow-xl: 0 25px 70px rgba(15,23,42,.15), 0 10px 20px rgba(15,23,42,.08);
--glass-shadow: 0 8px 32px rgba(15,23,42,.08), 0 2px 8px rgba(30,111,217,.06), inset 0 1px 0 rgba(255,255,255,.7);
--glass-shadow-hover: 0 18px 50px rgba(15,23,42,.12), 0 4px 14px rgba(30,111,217,.15), inset 0 1px 0 rgba(255,255,255,.85);

/* Easing */
--easing: cubic-bezier(.4, 0, .2, 1);
--spring: cubic-bezier(.34, 1.56, .64, 1);

/* Background mesh (light) */
--bg-mesh:
  radial-gradient(at 20% 10%, #DBEAFE 0%, transparent 50%),
  radial-gradient(at 80% 80%, #E0E7FF 0%, transparent 50%),
  radial-gradient(at 50% 50%, #F0F9FF 0%, transparent 60%);
```

**Componentes prontos para portar:**
- `nav` (fixed, glass, scroll shadow)
- `btn-primary` / `btn-ghost` / `btn-hero` / `btn-hero-lg` / `btn-demo`
- `dashboard-card` / `feature-card` / `cert-card`
- `chip` (floating glass badge)
- `hero-badge` (pill com pulse-ring)
- `progress-bar` + `progress-fill`
- `step-num` (numbered process)
- `audit-trail` (timestamped log)
- `field input` (border-bottom only, focus aurora)
- `eye-btn` (password toggle SVG)
- `alt-btn` (SSO ghost)
- `reveal` (IntersectionObserver fade-up)

**Animações reutilizáveis:**
- `fadeUp` (opacity + translateY 24px)
- `pulse-ring` (box-shadow expanding)
- `float` (translateY -8px)
- `auroraPulse` (mix-blend-mode screen bands)
- `shimmer` (background-position 200%)

### 2.3 Oficial Laudo (Print) — manter intocado

**Stack:** Python → HTML → Playwright headless → PDF

**Identidade:** Playfair Display + Source Sans 3, navy `#12345e`, blue `#1F7FB8`, layout A4 com margins 20mm 18mm 22mm 18mm.

**Por que manter separado:**
- Print-optimized (pt em vez de px, page-break, counter(page))
- Hierarquia formal (Playfair serif → autoridade, comum em laudos jurídicos)
- Já bem executado (capa, sumário, op-cards, tabelas zebra, métricas)
- A jornada do usuário entrega o laudo como artefato externo (separação intencional)

**Única consideração:** os componentes do laudo (op-card, metric, badge OK/PEND) **podem inspirar** representações visuais correspondentes na app React — mas sem unificar fontes.

### 2.4 Backend API (referência)

13 endpoints, request `EspolioIn`, response `apurar` retorna `{resumo: {ir_espolio_total, bens_conclusivos, bens_pendentes, conclusivo, audit_hash}, bens: [{resultado: {status, ganhos, ir_*, fatores_reducao}}]}`.

Não precisa mudar para o redesign do frontend.

---

## 3. Diagnóstico — o que precisa mudar

### Problemas estruturais
1. **Três identidades visuais sem ponte** — usuário troca de cidade visual a cada tela
2. **Tokens dispersos** — `tailwind.config.ts` + `index.css` + inline `style={{}}` = 3 fontes da verdade
3. **Sem hierarquia tipográfica clara** — display gigante, depois eyebrow minúsculo, nada no meio
4. **Emojis fazendo papel de ícones** em produto B2B fiscal (quebra de confiança visual)
5. **Glass morphism saturado** — perde efeito quando aplicado em tudo
6. **Acessibilidade lacunar** — labels não associadas, contraste não verificado, focus pouco visível

### O que está bom (preservar)
- Arquitetura React/state limpa (reducer + actions, invalidação de derivados)
- Componentes UI reutilizáveis (Card, Field, Tabs, Toast, Metric, Skeleton)
- Validação real-time em BensTab
- Streaming SSE em AnaliseTab
- Auditoria SHA256 em Documentos/Análise
- Sistema de notificações Toast (a11y ok)
- Donut chart SVG interativo
- Risk score (conceito — só precisa crescer)

---

## 4. Estratégia de Unificação

**Direção:** Aurora vira o design system da aplicação inteira. Laudo fica intocado.

**Por que Aurora e não Bureau Blue:**
- Aurora já é a primeira impressão (login)
- Tipografia triádica (Manrope/Instrument Serif/JetBrains Mono) tem mais personalidade B2B premium que Inter monolítica
- Glass morphism mais maduro (sombras estratificadas com inset highlights)
- Tokens já organizados em `--custom-properties`
- Easing/animações mais polidas

**Tradeoffs:**
- Custo: refatorar ~30 arquivos React
- Risco: introduzir regressões em validações/fluxos enquanto move CSS
- Mitigação: fazer por camadas (tokens → primitives → componentes → tabs), com app rodando o tempo todo

---

## 5. Plano de Modernização em 6 Fases

> Cada fase é um PR atômico que pode ser revisado e revertido independentemente. A app funciona ao final de cada fase.

### **Fase 1 — Fundação de Tokens** ✅ (1-2 dias)

**Objetivo:** estabelecer `:root { --tokens }` como única fonte da verdade.

- [ ] Criar `frontend/src/styles/tokens.css` com tokens Aurora (cores, fontes, raios, sombras, easing, mesh)
- [ ] Criar `frontend/src/styles/tokens.ts` (mirror JS para consumir em componentes)
- [ ] Importar Google Fonts (Manrope + Instrument Serif + JetBrains Mono) em `index.html`
- [ ] Atualizar `tailwind.config.ts` para consumir CSS vars (`colors.brand = "var(--blue)"`)
- [ ] Manter `index.css` antigo intacto (compat) — apenas adicionar tokens novos

**Critério de aceite:** `getComputedStyle(document.documentElement).getPropertyValue('--blue')` retorna `#0052FF`. App roda igual.

### **Fase 2 — Primitives da Camada UI** ✅ (2-3 dias)

**Objetivo:** atualizar os 7 componentes em `components/ui/` para Aurora.

- [ ] `Card.tsx` → glass-bg + glass-blur + glass-shadow + r-xl (32px). Header em Manrope 700 + label em JetBrains Mono 10px uppercase
- [ ] `Field.tsx` → label JetBrains Mono 0.6rem uppercase tracking .12em, input border-bottom only (no estilo login)
- [ ] `Tabs.tsx` → tab bar glass, label JetBrains Mono uppercase, ícones SVG (Heroicons), active = blue underline (sem gradient)
- [ ] `Metric.tsx` → valor em Instrument Serif italic 2.4rem ou Manrope 800 (escolher por tone), label JetBrains Mono
- [ ] `SegmentedControl.tsx` → mesmo padrão da tab bar
- [ ] `Skeleton.tsx` → manter (shimmer já é Aurora-compatível, ajustar cores)
- [ ] `Toast.tsx` → trocar emojis ✓⚠✕ℹ por ícones Heroicons inline SVG

**Critério de aceite:** abrir cada tab e verificar que cards/inputs/tabs já têm a estética Aurora. Validações continuam funcionando.

### **Fase 3 — Ícones e Microfeedback** ✅ (1 dia)

**Objetivo:** remover todos emojis-como-ícone.

- [ ] Adicionar `@heroicons/react` (ou criar `components/ui/Icon.tsx` com SVGs inline)
- [ ] Substituir nas Tabs: 📥→DocumentArrowUp, 📋→ClipboardDocumentList, 🧮→Calculator, 📄→DocumentText, 🤖→Sparkles, 📊→ChartBar
- [ ] Substituir na Sidebar: 📂→FolderOpen, 💾→CloudArrowUp, 🔒→LockClosed, ✕→XMark
- [ ] Substituir nos botões danger: 🗑️→Trash
- [ ] Loading states: spinner SVG inline em vez de "Salvando..."

**Critério de aceite:** `grep -rE "[📥📋🧮📄🤖📊📂💾🔒✕🗑️]" frontend/src` retorna zero.

### **Fase 4 — Shell (Header + Sidebar + Modals)** ✅ (2 dias) — *Sidebar removida na Fase 7*

**Objetivo:** chassis da app igual Aurora.

- [ ] `Header.tsx` → reduzir altura, fundo `rgba(240,247,255,0.8)` + `backdrop-filter: var(--glass-blur)`, brand em Manrope+Instrument Serif italic ("OrgAudi" / "Espólio."), status chips com pill + pulse-ring
- [ ] Aplicar `--bg-mesh` no body (mesh radial pastel)
- [ ] `Sidebar.tsx` → glass-bg + r-xl, sections com label JetBrains Mono uppercase, herdeiros como `cert-card` mini, soma frações com `progress-bar` Aurora
- [ ] `AuthModal.tsx` → adotar visual do `login.html` (campo border-bottom, CTA fill blue, alt-btn para SSO futuro)
- [ ] `AbrirEspolioModal.tsx` → dashboard-card style, lista como cert-cards
- [ ] Animações: `fadeUp` ao abrir modals, `pulse-ring` em status ativo

**Critério de aceite:** primeira impressão da app idêntica em "linguagem" ao login.

### **Fase 5 — Telas Operacionais (Tabs)** ✅ (3-4 dias)

**Objetivo:** todas 6 tabs em Aurora.

- [ ] **DocumentosTab** — dropzone glass-bg dashed border var(--blue), result list como feature-cards
- [ ] **BensTab** — bem-row como dashboard-card colapsível, validation alerts com `aviso`-style do laudo (border-left 3pt color, sem fundo)
- [ ] **ApuracaoTab** — hero IR em Instrument Serif italic gigante, donut chart com legenda lateral colorida (não só hover), mini-metrics como `.metric` do laudo
- [ ] **RelatorioTab** — adicionar preview markdown com syntax minimal (já tem o conteúdo), buttons em btn-hero style
- [ ] **AnaliseTab** — manter MdView, restyle container com `audit-trail` para SHA256 final
- [ ] **LaudoTab** — risk score: expandir SVG para 200px+, gauge meter horizontal em vez de circle (mais legível), anomalias em `aviso` com 3 níveis (border-left blue/warn/danger), scenarios em `cenarios` (2 colunas a/b)

**Critério de aceite:** screenshot side-by-side antes/depois mostra que toda app fala mesma linguagem visual.

### **Fase 6 — Acessibilidade e Polimento** ✅ (1-2 dias) — *parcial; expandida na Fase 7*

**Objetivo:** atingir WCAG AA + microinterações finais.

- [ ] Associar `<label htmlFor>` em todos inputs (Field.tsx)
- [ ] Verificar contraste com axe-core (DevTools) — corrigir <4.5:1 em text e <3:1 em UI
- [ ] `focus-visible` 3px ring var(--blue) com 30% alpha em todos interactive
- [ ] `aria-label` em botões icon-only
- [ ] Testar Tab/Shift+Tab/Enter/Escape em formulários e modals
- [ ] IntersectionObserver `.reveal` em cards de listas (fadeUp progressivo)
- [ ] Animação de loading em "Salvando..." (spinner + texto)
- [ ] Empty states: `feature-card` style com ícone + texto + CTA

**Critério de aceite:** Lighthouse a11y ≥95, keyboard navigation completa, screen reader OK.

### **Fase opcional 7 — Performance**

- [ ] Lazy load tabs (`React.lazy` + Suspense — render apenas active tab)
- [ ] Memoize donut chart (recalcular só quando `apuracao` muda)
- [ ] Code-split por tab
- [ ] Logo PNG → SVG inline (one less request)
- [ ] Auditar bundle size

---

## 6. Decisões em Aberto

Antes de começar a Fase 1, alinhar:

1. **Tema único ou dual (light/dark)?** Login é dark, conciliação é light. Para a app operacional dia-a-dia, recomendo **light bank-grade** (índice_conciliacao) — usuário fica horas operando, dark cansa. Login mantém o dark dramatic.

2. **Tipografia em valores monetários?** Opções:
   - (a) Manrope 800 (limpo, moderno)
   - (b) Instrument Serif italic (dramático, premium — combina com laudo Playfair)
   - Recomendo (a) para tabelas/listagens, (b) para hero/destaques

3. **Aurora animada no login mantém na app?** Stars canvas + aurora bands são caros (RAF + 4 blobs animados). Recomendo:
   - Login/landing: full Aurora animada
   - App operacional: apenas mesh gradient estático (sem stars, sem bands)

4. **Continuar com Tailwind ou migrar para CSS modules?** Recomendo **manter Tailwind** + tokens CSS vars. Custo de migração é alto e não compensa.

5. **`@heroicons/react` ou inline SVG?** Heroicons = ~30KB adicionais ao bundle, mas vasta cobertura. Inline = controle total. Recomendo **inline SVG** num único arquivo `components/ui/icons.tsx` (apenas os ~15 ícones que vamos usar).

---

## 7. Riscos e Mitigações

| Risco | Mitigação |
|---|---|
| Quebrar validações ao mover CSS | Tests visuais (screenshot diff) entre fases; smoke test manual a cada PR |
| Performance degradar com glass-blur em todos cards | `will-change: transform` apenas em hover; auditar com DevTools |
| Inter→Manrope troca FOIT (flash of invisible text) | `font-display: swap` no Google Fonts link |
| `--bg-mesh` afetar legibilidade em tabelas densas | Tabelas dentro de cards com `surface-solid` (#FFFFFF opaco) |
| Animações reveal incomodarem usuários power-user | `@media (prefers-reduced-motion: reduce)` desliga tudo |

---

## 8. Cronograma Sugerido

Assumindo dedicação parcial (2-4h/dia):

```
Semana 1:  Fase 1 (Tokens)
Semana 1:  Fase 2 (Primitives)
Semana 2:  Fase 3 (Ícones)  + Fase 4 (Shell)
Semana 3:  Fase 5 (Tabs — DocumentosTab, BensTab, ApuracaoTab)
Semana 4:  Fase 5 (cont. — RelatorioTab, AnaliseTab, LaudoTab)
Semana 4:  Fase 6 (a11y + polimento)
```

**Total: ~4 semanas** com app funcional ao final de cada semana.

---

## 9. Decisões tomadas (seção 6 resolvida)

Antes da execução, todas as 5 decisões em aberto foram fechadas com os defaults recomendados:

| # | Pergunta | Decisão |
|---|---|---|
| 1 | Tema único ou dual? | **Dual** — app light bank-grade, login dark dramatic |
| 2 | Tipografia em valores monetários | **Manrope 800** em tabelas/listagens; **Instrument Serif italic** em hero/destaques |
| 3 | Aurora animada na app? | **Não** — app usa mesh estático; login mantém stars + aurora bands |
| 4 | Tailwind ou CSS modules? | **Manter Tailwind** + tokens CSS vars |
| 5 | `@heroicons/react` ou inline SVG? | **Inline SVG** em `components/ui/icons.tsx` (35 ícones) |

---

## 10. Execução (2026-05-24)

**Concluída em uma única sessão**, somando **7 fases** (as 6 do plano + 1 de reestruturação total). Estado final em [`8df90cd`](https://github.com/orgateccloud-bot/OrgInv/commit/8df90cd).

### 10.1 — Fases 1–6 (plano original)

Todas executadas em ordem. Build final limpo (`tsc --noEmit` 0 erros, `vite build` 4.47s — 250KB JS gz72KB, 31KB CSS gz7KB).

| Fase | Arquivos principais |
|---|---|
| 1 — Tokens | [`frontend/src/styles/tokens.css`](frontend/src/styles/tokens.css), [`tokens.ts`](frontend/src/styles/tokens.ts), [`tailwind.config.ts`](frontend/tailwind.config.ts), [`index.html`](frontend/index.html) com Google Fonts triádicas |
| 2 — Primitives | 7 arquivos em [`components/ui/`](frontend/src/components/ui/) — `Field` ganhou `htmlFor` automático via `useId`+`cloneElement` |
| 3 — Ícones | [`components/ui/icons.tsx`](frontend/src/components/ui/icons.tsx) com 35 ícones Heroicons-inspired; 13+ emojis removidos |
| 4 — Shell | `Header`, `Sidebar`, `AuthModal`, `AbrirEspolioModal`, `SupabaseBadge`, `App.tsx` |
| 5 — Tabs | 6 tabs: `DocumentosTab`, `BensTab`, `ApuracaoTab`, `RelatorioTab`, `AnaliseTab`, `LaudoTab` |
| 6 — A11y | `prefers-reduced-motion` em [`tokens.css`](frontend/src/styles/tokens.css), `aria-label` em ícones isolados |

### 10.2 — Fase 7: Reestruturação total (após análise visual)

Disparada após screenshots via Playwright revelarem **excesso de glass morphism, densidade da sidebar e ruído visual**. Mudanças:

| Aspecto | Antes (após Fases 1–6) | Depois (Fase 7) |
|---|---|---|
| **Sidebar** | 288px com 4 seções aninhadas em glass | **Deletada** — dados migraram para nova aba "Espólio" |
| **Header** | 70px com 2 status pills decorativas | **52px** com breadcrumb do espólio ativo + actions inline |
| **Tabs** | 6 tabs | **7 tabs** — "Espólio" virou a primeira |
| **AuditFooter** | Hash SHA-256 repetido em 4 tabs | **Componente único** ([`AuditFooter.tsx`](frontend/src/components/AuditFooter.tsx)) no rodapé global |
| **ApuracaoTab** | Hero + métricas + donut + simulador todos expandidos | Hero compacto + donut em destaque; simulador, detalhamento, isenções e cenários **colapsados** por padrão |
| **LaudoTab** | Risk gauge 96px + 3 cards verticais de download | Risk gauge **256px** como hero (número 4.5rem) + downloads em 1 row |
| **Glass morphism** | Em tudo (cards, sidebar, dropzone, segmented, toast, chip) | Removido de elementos aninhados; apenas backgrounds sólidos com borda fina |
| **Gradientes** | Headers de cards com gradientes diagonais | Removidos |
| **Background** | Mesh gradient pastel (3 radiais) | Neutro `#F8FAFC` |
| **Raios** | 22–32px na maioria dos cards | Padrão `r-md` (14px); só hero/risk gauge usam mais |

**Arquivos removidos:** [`Sidebar.tsx`](frontend/src/components/Sidebar.tsx) (deletado).
**Arquivo criado:** [`EspolioTab.tsx`](frontend/src/tabs/EspolioTab.tsx), [`AuditFooter.tsx`](frontend/src/components/AuditFooter.tsx).

### 10.3 — Publicação

- **Repo:** [github.com/orgateccloud-bot/OrgInv](https://github.com/orgateccloud-bot/OrgInv) (público)
- **Commit inicial completo:** `8df90cd` — *"OrgAudi v0.4.0 — initial code drop with Aurora redesign"* (91 arquivos, 19.304 linhas)
- **Excluídos antes do push (dados de cliente real):** `auditoria_adilson.py`, `data/laudo_exemplo/laudo.{pdf,docx,xlsx,html}`
- **`.gitignore`** criado cobrindo `node_modules/`, `dist/`, `__pycache__/`, `.env`, `.claude/settings.local.json`

### 10.4 — Próximos passos (não executados nesta sessão)

- [ ] **Performance (Fase opcional 7 do plano original)** — lazy load por tab, memoize donut, code-split, logo PNG → SVG
- [ ] **Auditoria axe-core** para contrast ratios WCAG AA
- [ ] **Keyboard navigation** completa (Tab/Shift+Tab/Enter/Escape em modais)
- [ ] **Screen reader test** (NVDA/JAWS)
- [ ] **Animação reveal (`IntersectionObserver`)** em listas longas — está estruturada no CSS mas não conectada
- [ ] **Substituir `prompt()`/`confirm()`/`alert()`** por modais Aurora (ainda usados em `AbrirEspolioModal`, `SupabaseBadge`, `RelatorioTab`, `LaudoTab`)
- [ ] **Tests visuais** com screenshot diff entre commits
