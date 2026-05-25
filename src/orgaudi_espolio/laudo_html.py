# -*- coding: utf-8 -*-
"""
laudo_html.py — Geração do laudo em HTML (desktop light) e HTML dark mobile.

Design system idêntico ao laudo_detalhado.html de referência:
  Fontes   : Playfair Display (títulos) + Source Sans 3 (corpo)
  Paleta   : navy #12345e, blue #1f7fb8, cyan #38c4e6
  Variantes: tema="light" → desktop A4 print-ready
             tema="dark"  → mobile dark, viewport responsivo

Funções públicas:
  gerar_laudo_html(espolio, caminho_saida, analise_ia, tema) → str
  gerar_laudo_html_dark(espolio, caminho_saida, analise_ia) → str

Sistema OrgAudi · ORGATEC CONTABILIDADE E AUDITORIA
"""
from __future__ import annotations

import base64
import os
from datetime import datetime
from typing import Optional

from .dominio import Espolio, Regime, StatusApuracao
from .motor import MotorApuracao

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))


# ───────────────────────────────────────────────────────────────────────
# Logo
# ───────────────────────────────────────────────────────────────────────

def _logo_data_url() -> str:
    for path in [
        os.path.join(_ROOT, "frontend", "dist", "OrgatecOrg1.png"),
        os.path.join(_HERE, "assets", "logo.png"),
    ]:
        try:
            with open(path, "rb") as f:
                return "data:image/png;base64," + base64.b64encode(f.read()).decode()
        except FileNotFoundError:
            continue
    return ""


# ───────────────────────────────────────────────────────────────────────
# CSS — variáveis compartilhadas (tema injetado depois)
# ───────────────────────────────────────────────────────────────────────

_CSS_VARS_LIGHT = """
  :root {
    --navy:       #12345e;
    --blue:       #1f7fb8;
    --cyan:       #38c4e6;
    --cyan2:      #8fe6ee;
    --text:       #1b2733;
    --text-sec:   #364a5e;
    --text-muted: #51616f;
    --text-dim:   #8a93a0;
    --border:     #d4dde6;
    --bg:         #ffffff;
    --bg-light:   #f6fafc;
    --bg-table:   #eff4f9;
    --bg-key:     #eef3f8;
    --bg-total:   #dce9f4;
    --ok:         #2f7d4f;
    --ok-bg:      #e3f1e8;
    --ok-text:    #226b42;
    --warn:       #b7791f;
    --warn-bg:    #fbf1da;
    --warn-text:  #8a5c0e;
    --err:        #b33a3a;
    --err-bg:     #fbf0ef;
    --err-text:   #b33a3a;
    --nv-text:    #5a6470;
    --nv-bg:      #eceff2;
    --nv-border:  #94a0ad;
  }
"""

_CSS_VARS_DARK = """
  :root {
    --navy:       #79c0ff;
    --blue:       #58a6ff;
    --cyan:       #56d0e3;
    --cyan2:      #39c5dd;
    --text:       #e6edf3;
    --text-sec:   #c9d1d9;
    --text-muted: #8b949e;
    --text-dim:   #6e7681;
    --border:     #30363d;
    --bg:         #0d1117;
    --bg-light:   #161b22;
    --bg-table:   #1c2128;
    --bg-key:     #21262d;
    --bg-total:   #1c2840;
    --ok:         #56d364;
    --ok-bg:      #132214;
    --ok-text:    #56d364;
    --warn:       #e3b341;
    --warn-bg:    #2d1d09;
    --warn-text:  #e3b341;
    --err:        #f85149;
    --err-bg:     #2c0b0b;
    --err-text:   #f85149;
    --nv-text:    #8b949e;
    --nv-bg:      #21262d;
    --nv-border:  #484f58;
  }
"""

_CSS_BASE = """
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Source+Sans+3:ital,wght@0,400;0,600;0,700;1,400&display=swap');

  @page {
    size: A4; margin: 20mm 18mm 22mm 18mm;
    @bottom-center {
      content: "OrgAudi · ORGATEC CONTABILIDADE E AUDITORIA  —  página " counter(page) " de " counter(pages);
      font-family: 'Source Sans 3', sans-serif; font-size: 7.4pt; color: #8a93a0;
    }
  }
  @page :first { margin: 0; @bottom-center { content: ""; } }

  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Source Sans 3','Segoe UI',sans-serif; font-size: 10.2pt;
         line-height: 1.58; color: var(--text); background: var(--bg); }

  /* ---- CAPA ---- */
  .capa {
    height: 297mm; padding: 30mm 26mm 26mm 26mm;
    display: flex; flex-direction: column; justify-content: space-between;
    page-break-after: always; position: relative;
    background:
      radial-gradient(ellipse 62% 42% at 15% 7%, rgba(120,198,233,.46), transparent 60%),
      radial-gradient(ellipse 56% 40% at 88% 19%, rgba(142,182,224,.42), transparent 63%),
      radial-gradient(ellipse 72% 40% at 52% 38%, rgba(150,212,225,.26), transparent 66%),
      linear-gradient(180deg,#d3e6f3 0%,#e2eef6 30%,#eef5fa 54%,#f8fbfc 76%,#fff 100%);
  }
  .capa::before { content:""; position:absolute; top:0; left:0; right:0; height:5mm;
    background: linear-gradient(90deg,#1f7fb8 0%,#38c4e6 52%,#7fe0ec 100%); }
  .capa-brand { display:flex; align-items:center; }
  .capa-logo  { width:19mm; height:21mm; object-fit:contain; margin-right:5mm;
    filter:drop-shadow(0 1mm 2.5mm rgba(40,100,150,.22)); }
  .capa-wm .nome { font-size:21pt; font-weight:700; letter-spacing:.20em; color:#12345e; line-height:1; }
  .capa-wm .desc { font-size:8pt; letter-spacing:.26em; text-transform:uppercase; color:#5a82a8; margin-top:2.2mm; }
  .capa-sub  { font-size:8pt; letter-spacing:.16em; text-transform:uppercase; color:#7593af; margin-top:8mm; }
  .capa-mid  { display:flex; flex-direction:column; }
  .capa-titulo { font-family:'Playfair Display',serif; font-size:30pt; font-weight:700; line-height:1.16; color:#12345e; }
  .capa-rule { width:40mm; height:2.4pt; margin:9mm 0;
    background:linear-gradient(90deg,#1f7fb8,#38c4e6,#8fe6ee); }
  .capa-objeto { font-size:11.5pt; color:#3f5468; max-width:124mm; }
  .capa-selo { margin-top:8mm; display:inline-block; align-self:flex-start;
    border:.7pt solid #1f7fb8; color:#1f7fb8; font-size:7.6pt;
    letter-spacing:.14em; text-transform:uppercase; padding:2mm 4mm; }
  .capa-meta { border-top:.5pt solid #c4d4e2; padding-top:6mm;
    display:flex; justify-content:space-between; font-size:8.6pt; color:#65778a; }
  .capa-meta strong { color:#12345e; font-weight:600; display:block; font-size:9.4pt; margin-bottom:1mm; }

  /* ---- CONTEÚDO ---- */
  .conteudo { padding: 12mm 14mm 16mm 14mm; }

  h1.sec { font-family:'Playfair Display',serif; font-size:15pt; color:var(--navy);
    margin:9mm 0 3mm 0; padding-bottom:1.6mm; border-bottom:1.4pt solid var(--navy);
    page-break-after:avoid; }
  h1.sec .num { color:var(--blue); margin-right:2mm; }
  h2.sub { font-family:'Playfair Display',serif; font-size:11.5pt; color:var(--navy);
    margin:4mm 0 1.5mm 0; page-break-after:avoid; }
  p { margin:0 0 2.6mm 0; text-align:justify; }
  .lead { color:var(--text-sec); }
  strong { font-weight:600; }
  .termo { font-weight:700; color:var(--navy); }

  /* selos conf/cond/nv */
  .lbl { display:inline-block; font-size:6.8pt; font-weight:700; letter-spacing:.04em;
    padding:.5mm 1.5mm; border-radius:.8mm; vertical-align:.3mm; white-space:nowrap; }
  .lbl.conf { background:var(--ok-bg);   color:var(--ok-text);   border:.4pt solid var(--ok); }
  .lbl.cond { background:var(--warn-bg); color:var(--warn-text); border:.4pt solid var(--warn); }
  .lbl.nv   { background:var(--nv-bg);   color:var(--nv-text);   border:.4pt solid var(--nv-border); }

  /* tabela identidade */
  table.ident { width:100%; border-collapse:collapse; margin:3mm 0 4mm 0; font-size:9.5pt; }
  table.ident td { border:.5pt solid var(--border); padding:2mm 3mm; vertical-align:top; }
  table.ident td.k { background:var(--bg-key); font-weight:600; width:38mm; color:var(--text-sec); }

  /* alertas */
  .aviso { border-left:3pt solid var(--blue); background:#eef6fb; padding:3.5mm 4mm;
    margin:4mm 0; font-size:9.6pt; }
  .aviso .tag { display:block; font-size:7.8pt; letter-spacing:.12em; text-transform:uppercase;
    color:var(--blue); font-weight:700; margin-bottom:1.4mm; }
  .aviso.ok     { border-left-color:var(--ok);   background:var(--ok-bg); }
  .aviso.ok .tag { color:var(--ok); }
  .aviso.critico { border-left-color:var(--err);  background:var(--err-bg); }
  .aviso.critico .tag { color:var(--err); }
  .aviso.ambar  { border-left-color:var(--warn);  background:var(--warn-bg); }
  .aviso.ambar .tag { color:var(--warn); }

  /* conceito */
  .conceito { border:.6pt solid var(--border); border-left:2.6pt solid var(--blue);
    background:var(--bg-light); padding:3.2mm 4mm; margin:3mm 0; page-break-inside:avoid; }
  .conceito .ct { font-weight:700; color:var(--navy); font-size:10pt; margin-bottom:1mm; }
  .conceito p   { font-size:9.4pt; margin-bottom:0; }

  /* op-card */
  .op-card { border:.6pt solid var(--border); border-top:2.6pt solid var(--navy);
    padding:5mm 5.5mm 3mm 5.5mm; margin:5mm 0; page-break-inside:avoid; }
  .op-head { display:flex; justify-content:space-between; align-items:flex-start;
    gap:6mm; margin-bottom:3mm; break-inside:avoid; }
  .op-id { font-size:7.8pt; letter-spacing:.14em; text-transform:uppercase;
    color:var(--text-dim); font-weight:700; margin-bottom:.8mm; }
  h2.op { font-family:'Playfair Display',serif; font-size:12.5pt; color:var(--navy); margin:0; }

  /* badges ok/pendente */
  .badge { flex-shrink:0; font-size:7.6pt; font-weight:700; letter-spacing:.06em;
    text-transform:uppercase; padding:1.6mm 3mm; border-radius:1mm; white-space:nowrap; }
  .badge.ok   { background:var(--ok-bg);   color:var(--ok-text); border:.5pt solid var(--ok); }
  .badge.pend { background:var(--warn-bg); color:var(--warn-text); border:.5pt solid var(--warn); }

  /* step + fórmula */
  .step { margin:2.6mm 0; break-inside:avoid; }
  .step-label { font-size:8pt; letter-spacing:.10em; text-transform:uppercase;
    font-weight:700; color:var(--navy); border-left:2.4pt solid var(--blue);
    padding-left:2.4mm; margin-bottom:1mm; break-after:avoid; }
  .step p { margin-bottom:1.4mm; }
  .formula { font-family:'Source Code Pro',Consolas,monospace; font-size:8.7pt;
    background:var(--bg-light); border:.5pt solid var(--border);
    border-left:2.4pt solid var(--blue); padding:2.6mm 3mm;
    margin:2mm 0; color:var(--text); line-height:1.5; white-space:pre; }

  /* tabela dados */
  table.dt { width:100%; border-collapse:collapse; margin:3mm 0; font-size:8.7pt; }
  table.dt th { background:var(--navy); color:#eef4fb; font-weight:600;
    text-align:left; padding:2.2mm 2.6mm; font-size:8.2pt; }
  table.dt td { border:.5pt solid var(--border); padding:2mm 2.6mm; vertical-align:top; }
  table.dt tr:nth-child(even) td { background:var(--bg-table); }
  table.dt td.num { text-align:right; font-variant-numeric:tabular-nums; }
  table.dt tr.total td { background:var(--bg-total); font-weight:700;
    border-top:1pt solid var(--navy); }
  table.dt tr.pend td  { background:var(--warn-bg); }
  .ok-t  { color:var(--ok);   font-weight:600; }
  .err-t { color:var(--err);  font-weight:600; }
  .pend-t { color:var(--warn); font-style:italic; }

  /* métricas do resumo */
  .metrics { display:flex; gap:4mm; margin:4mm 0; flex-wrap:wrap; }
  .metric { flex:1; min-width:40mm; border:.6pt solid var(--border);
    border-radius:1mm; padding:3.5mm 4mm; text-align:center; page-break-inside:avoid; }
  .metric.destaque { border-top:2.6pt solid var(--blue); background:var(--bg-light); }
  .metric .ml { font-size:7.4pt; letter-spacing:.08em; text-transform:uppercase;
    color:var(--text-dim); font-weight:700; margin-bottom:1mm; }
  .metric .mv { font-family:'Playfair Display',serif; font-size:18pt;
    color:var(--navy); font-weight:700; line-height:1; }
  .metric .ms { font-size:8pt; color:var(--text-muted); margin-top:1mm; }

  /* cenários */
  .cenarios { display:flex; gap:4mm; margin:3mm 0; }
  .cen { flex:1; border:.6pt solid var(--border); border-radius:1mm;
    padding:3.5mm 4mm; page-break-inside:avoid; }
  .cen.a { border-top:2.6pt solid var(--ok);   }
  .cen.b { border-top:2.6pt solid var(--warn); }
  .cen .cl { font-size:7.6pt; letter-spacing:.08em; text-transform:uppercase;
    font-weight:700; margin-bottom:2mm; }
  .cen.a .cl { color:var(--ok);   }
  .cen.b .cl { color:var(--warn); }
  .cen .ct { font-family:'Playfair Display',serif; font-size:11pt; color:var(--navy); margin-bottom:1mm; }
  .cen p   { font-size:9pt; margin-bottom:1.6mm; }
  .cen .big { font-size:12.5pt; font-weight:700; color:var(--navy); }

  /* base legal dois colunas */
  .norma { font-size:8.8pt; color:var(--text-sec); columns:2; column-gap:8mm; margin-top:2mm; }
  .norma div { margin-bottom:1.4mm; break-inside:avoid; }
  .norma b { color:var(--navy); }

  /* assinatura */
  .assinatura { margin-top:9mm; page-break-inside:avoid; }
  .assinatura .linha { border-top:.6pt solid var(--navy); width:78mm; margin-bottom:1.3mm; }
  .assinatura .nome  { font-weight:600; color:var(--navy); }
  .assinatura .cargo { font-size:8.6pt; color:var(--text-muted); }

  /* encerramento */
  .encerr { margin-top:5mm; border-top:.5pt solid var(--border); padding-top:3mm;
    font-size:8.6pt; color:var(--text-muted); }
"""

_CSS_DARK_MOBILE_OVERRIDES = """
  /* ---- DARK MOBILE OVERRIDES ---- */
  body { background: #0d1117; }

  .capa {
    height: auto; min-height: 100vh;
    padding: clamp(8mm, 6vw, 24mm) clamp(5mm, 5vw, 20mm);
    background: linear-gradient(135deg,#0d1117 0%,#161b22 60%,#0d1b2a 100%);
  }
  .capa::before { background: linear-gradient(90deg,#1f7fb8,#30363d); }
  .capa-titulo { font-size: clamp(18pt,7vw,28pt); color:#79c0ff; }
  .capa-wm .nome { color:#79c0ff; }
  .capa-wm .desc { color:#58a6ff; }
  .capa-objeto { max-width:100%; color:#8b949e; }
  .capa-meta { flex-direction:column; gap:2mm; }
  .capa-meta > div + div { border-top:.5pt solid #30363d; padding-top:2mm; }
  .capa-meta strong { color:#79c0ff; }

  .conteudo { padding: clamp(4mm,4vw,12mm) clamp(3mm,4vw,12mm); }
  h1.sec { font-size:13pt; }

  table.dt th  { background:#1f2937; }
  table.dt tr:nth-child(even) td { background:#1c2128; }
  table.dt tr.pend td  { background:#2d1d09; }
  table.dt tr.total td { background:#1c2840; border-top-color:#30363d; }
  table.ident td.k { background:#21262d; color:#c9d1d9; }

  .aviso           { background:#161b22; }
  .aviso.ok        { background:#132214; }
  .aviso.critico   { background:#2c0b0b; }
  .aviso.ambar     { background:#2d1d09; }
  .conceito        { background:#161b22; }
  .op-card         { background:#0d1117; }
  .metric          { background:#161b22; }
  .metric.destaque { background:#0d1b2a; }
  .cenarios        { flex-direction:column; }
  .cen             { background:#161b22; }
  .norma           { columns:1; }
"""

_CSS_RESPONSIVE = """
  @media (max-width: 768px) {
    .capa    { height:auto; min-height:100vh; padding:6vw 5vw; }
    .metrics { flex-direction:column; }
    .cenarios { flex-direction:column; }
    .norma   { columns:1; }
    table.dt, table.ident { font-size:9pt; }
    table.dt td, table.dt th { padding:2mm 2mm; }
    .op-head { flex-direction:column; gap:2mm; }
    .capa-meta { flex-direction:column; gap:3mm; }
    body { font-size:11pt; }
  }
"""


# ───────────────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────────────

def _m(v) -> str:
    """Formata valor monetário em reais (formato BR) ou '—'."""
    if v is None:
        return "<em class='pend-t'>—</em>"
    s = f"{v:,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def _d(d) -> str:
    if d is None:
        return "—"
    return d.strftime("%d/%m/%Y") if hasattr(d, "strftime") else str(d)


def _regime_label(regime: Regime) -> str:
    m = {
        Regime.TRANSMISSAO_HERDEIRO:         "Transmissão a herdeiro",
        Regime.VENDA_PELO_ESPOLIO:           "Venda pelo espólio",
        Regime.CESSAO_DIREITOS_HEREDITARIOS: "Cessão de direitos",
        Regime.FORA_DO_ESPOLIO:              "Fora do monte",
        Regime.INDETERMINADO:                "Indeterminado",
    }
    return m.get(regime, regime.value)


def _chip_status(r: dict) -> str:
    if r.get("status") == StatusApuracao.OK:
        return '<span class="lbl conf">CONCLUSIVO</span>'
    return '<span class="lbl cond">PENDENTE</span>'


def _badge_status(r: dict) -> str:
    if r.get("status") == StatusApuracao.OK:
        return '<span class="badge ok">Conclusivo</span>'
    return '<span class="badge pend">Pendente</span>'


# ───────────────────────────────────────────────────────────────────────
# Seções HTML
# ───────────────────────────────────────────────────────────────────────

def _html_capa(espolio: Espolio, logo: str, emissao: str) -> str:
    logo_img = f'<img class="capa-logo" src="{logo}" alt="ORGATEC">' if logo else ""
    return f"""
<section class="capa">
  <div>
    <div class="capa-brand">
      {logo_img}
      <div class="capa-wm">
        <div class="nome">ORGATEC</div>
        <div class="desc">Contabilidade e Auditoria</div>
      </div>
    </div>
    <div class="capa-sub">Sistema OrgAudi &middot; AuditTax Compliance v3.0</div>
  </div>
  <div class="capa-mid">
    <div class="capa-titulo">Laudo de Apuração de IR<br>Ganho de Capital &mdash; Espólio</div>
    <div class="capa-rule"></div>
    <div class="capa-objeto">
      Apuração do Imposto de Renda sobre ganho de capital no espólio de
      <strong>{espolio.nome}</strong>, com memória de cálculo por bem e regime tributário.
    </div>
    <div class="capa-selo">Sistema OrgAudi v3.0 &middot; Gerado automaticamente</div>
  </div>
  <div class="capa-meta">
    <div>
      <strong>Espólio auditado</strong>
      {espolio.nome}<br>CPF {espolio.cpf_falecido}
    </div>
    <div>
      <strong>Datas</strong>
      Óbito: {_d(espolio.data_obito)}<br>Partilha: {_d(espolio.data_partilha)}
    </div>
    <div>
      <strong>Emissão</strong>
      {emissao}<br>ORGATEC Contabilidade e Auditoria
    </div>
  </div>
</section>
"""


def _html_resumo(resumo: dict, espolio: Espolio) -> str:
    ir_total = resumo.get("ir_espolio_total", 0.0)
    conc = resumo.get("bens_conclusivos", 0)
    pend = resumo.get("bens_pendentes", 0)
    status = "CONCLUSIVO" if resumo.get("conclusivo") else "PENDENTE"
    status_cls = "ok" if resumo.get("conclusivo") else "ambar"

    alerta_pend = ""
    if pend > 0:
        alerta_pend = f"""
    <div class="aviso ambar">
      <span class="tag">Atenção — apuração incompleta</span>
      {pend} bem(ns) com pendência de dados. O IR total acima <strong>não é definitivo</strong>
      enquanto houver lacunas. Resolva as pendências antes de qualquer entrega à RFB.
    </div>"""

    herdeiros_rows = ""
    for h in espolio.herdeiros:
        tipo = "Meeiro" if h.eh_meeiro else "Herdeiro"
        herdeiros_rows += f"""
      <tr>
        <td>{h.nome}</td>
        <td>{h.cpf or '—'}</td>
        <td class="num">{h.fracao_monte * 100:.2f}%</td>
        <td>{tipo}</td>
      </tr>"""

    return f"""
<h1 class="sec"><span class="num">1.</span>Resumo Executivo</h1>
<div class="metrics">
  <div class="metric destaque">
    <div class="ml">IR Total do Espólio</div>
    <div class="mv">{_m(ir_total)}</div>
    <div class="ms">soma dos bens conclusivos</div>
  </div>
  <div class="metric">
    <div class="ml">Bens Conclusivos</div>
    <div class="mv">{conc}</div>
    <div class="ms">apuração completa</div>
  </div>
  <div class="metric">
    <div class="ml">Bens Pendentes</div>
    <div class="mv">{pend}</div>
    <div class="ms">dados faltantes</div>
  </div>
  <div class="metric">
    <div class="ml">Status Geral</div>
    <div class="mv" style="font-size:14pt">{status}</div>
    <div class="ms">&nbsp;</div>
  </div>
</div>
{alerta_pend}

<h2 class="sub">Participantes</h2>
<table class="dt">
  <thead><tr>
    <th style="width:42%">Nome</th>
    <th style="width:26%">CPF</th>
    <th style="width:16%">Fração</th>
    <th>Tipo</th>
  </tr></thead>
  <tbody>{herdeiros_rows}</tbody>
</table>
"""


def _html_apuracao(espolio: Espolio) -> str:
    rows = ""
    for b in espolio.bens:
        r = b.resultado
        ok = r.get("status") == StatusApuracao.OK
        tr_cls = "" if ok else ' class="pend"'
        ganho = r.get("ganho_bruto") or r.get("ganho_diferido")
        base  = r.get("base_tributavel")
        ir    = r.get("ir_espolio")
        rows += f"""
      <tr{tr_cls}>
        <td><strong>{b.identificacao}</strong>
          {'<br><small>' + b.matricula + '</small>' if b.matricula else ''}</td>
        <td>{_regime_label(b.regime)}</td>
        <td style="text-align:center">{_chip_status(r)}</td>
        <td class="num">{'<em class="pend-t">—</em>' if ganho is None else _m(ganho)}</td>
        <td class="num">{'<em class="pend-t">—</em>' if base  is None else _m(base)}</td>
        <td class="num">{'<em class="pend-t">pendente</em>' if ir is None else _m(ir)}</td>
      </tr>"""
        if b.pendencias:
            for p in b.pendencias:
                rows += f'<tr class="pend"><td colspan="6"><small class="pend-t">&#9888; {p}</small></td></tr>'

    return f"""
<h1 class="sec"><span class="num">2.</span>Apuração por Bem</h1>
<table class="dt">
  <thead><tr>
    <th style="width:30%">Bem</th>
    <th style="width:22%">Regime</th>
    <th style="width:12%">Status</th>
    <th class="num" style="width:12%">Ganho bruto</th>
    <th class="num" style="width:12%">Base trib.</th>
    <th class="num" style="width:12%">IR (R$)</th>
  </tr></thead>
  <tbody>{rows}</tbody>
</table>
"""


def _html_herdeiros(espolio: Espolio) -> str:
    secoes = ""
    tem_conteudo = False

    for b in espolio.bens:
        r = b.resultado
        if r.get("status") != StatusApuracao.OK:
            continue

        if b.regime == Regime.TRANSMISSAO_HERDEIRO:
            tem_conteudo = True
            base   = r.get("base_custo_herdeiro")
            difer  = r.get("ganho_diferido", 0.0) or 0.0
            b_meei = r.get("base_custo_meeiro")
            opcao  = b.opcao.value
            secoes += f"""
<div class="op-card">
  <div class="op-head">
    <div>
      <div class="op-id">Transmissão a herdeiro &mdash; Art. 23 Lei 9.532/97</div>
      <h2 class="op">{b.identificacao}</h2>
    </div>
    <span class="badge ok">IR Espólio = R$ 0,00</span>
  </div>
  <div class="conceito">
    <div class="ct">Opção do Art. 23: {opcao}</div>
    <p>Herança é rendimento isento (Lei 7.713/88 Art. 6º XVI). Não há IR no espólio hoje.
    O ganho fica diferido e será tributado na venda futura pelo herdeiro.</p>
  </div>
  <table class="dt" style="margin-top:3mm">
    <thead><tr><th>Campo</th><th class="num">Valor</th></tr></thead>
    <tbody>
      <tr><td>Base de custo recebida pelo herdeiro</td><td class="num">{_m(base)}</td></tr>
      <tr><td>Base de custo da meação (cônjuge/companheiro)</td><td class="num">{_m(b_meei)}</td></tr>
      <tr><td>Ganho diferido — tributável na venda futura</td><td class="num">{_m(difer)}</td></tr>
      <tr class="total"><td>IR no espólio agora</td><td class="num ok-t">R$ 0,00 (isento)</td></tr>
    </tbody>
  </table>
</div>"""

        elif b.regime == Regime.CESSAO_DIREITOS_HEREDITARIOS:
            tem_conteudo = True
            ir_herd = r.get("ir_herdeiros") or {}
            rows_h = ""
            for nome, d in ir_herd.items():
                rows_h += f"""
        <tr>
          <td>{nome}</td>
          <td class="num">{d['fracao']:.4f}</td>
          <td class="num">{_m(d['ganho'])}</td>
          <td class="num">{_m(d['base_tributavel'])}</td>
          <td class="num"><strong>{_m(d['ir'])}</strong></td>
        </tr>"""
            secoes += f"""
<div class="op-card">
  <div class="op-head">
    <div>
      <div class="op-id">Cessão de Direitos Hereditários</div>
      <h2 class="op">{b.identificacao}</h2>
    </div>
    <span class="badge ok">IR no espólio = R$ 0,00</span>
  </div>
  <div class="aviso ambar">
    <span class="tag">Atenção — IR nas pessoas físicas dos cedentes</span>
    O ganho de capital é tributado na DIRPF de cada herdeiro cedente, não do espólio.
    Cada cedente deve recolher o GCAP no mês da operação.
  </div>
  <table class="dt" style="margin-top:3mm">
    <thead><tr>
      <th>Herdeiro cedente</th>
      <th class="num">Fração</th>
      <th class="num">Ganho rateado</th>
      <th class="num">Base tributável</th>
      <th class="num">IR (R$)</th>
    </tr></thead>
    <tbody>{rows_h}</tbody>
  </table>
</div>"""

    if not tem_conteudo:
        secoes = '<p class="lead">Nenhum bem conclusivo com repercussão fiscal para os herdeiros neste espólio.</p>'

    return f"""
<h1 class="sec"><span class="num">3.</span>IR dos Herdeiros</h1>
{secoes}
"""


def _html_memoria_fr(espolio: Espolio) -> str:
    cards = ""
    for b in espolio.bens:
        fr = b.resultado.get("fatores_reducao")
        if fr is None:
            continue
        if not fr.aplicavel:
            cards += f"""
<div class="conceito">
  <div class="ct">{b.identificacao}</div>
  <p>{fr.motivo_inaplicavel}</p>
</div>"""
            continue

        passos = "".join(
            f'<div class="step"><div class="step-label">Passo {i}</div><p>{p}</p></div>'
            for i, p in enumerate(fr.memoria, 1)
        )
        fr_vals = f"""
<div class="formula">M1={fr.m1}  FR1={fr.fr1:.6f}
M2={fr.m2}  FR2={fr.fr2:.6f}
Redução Lei 7.713/88 = {fr.reducao_7713:.4f}
Base final = {_m(fr.base_calculo_final)}</div>"""

        cards += f"""
<div class="op-card">
  <div class="op-head">
    <div>
      <div class="op-id">Fatores de Redução — Lei 11.196/2005 Arts. 39-40</div>
      <h2 class="op">{b.identificacao}</h2>
    </div>
  </div>
  {passos}
  {fr_vals}
  {('<div class="aviso ambar"><span class="tag">Alerta</span>' + b.resultado.get("alerta_reducao","") + '</div>') if b.resultado.get("alerta_reducao") else ""}
</div>"""

    if not cards:
        return ""

    return f"""
<h1 class="sec"><span class="num">4.</span>Memória dos Fatores de Redução</h1>
<div class="aviso">
  <span class="tag">Verificação obrigatória</span>
  Conferir estes valores contra o programa GCAP oficial da Receita Federal.
  Em caso de divergência, <strong>prevalece o GCAP</strong>.
</div>
{cards}
"""


def _html_analise_ia(analise: str) -> str:
    if not analise or not analise.strip():
        return ""
    paragrafos = ""
    for bloco in analise.split("\n\n"):
        bloco = bloco.strip()
        if not bloco:
            continue
        linhas = [l.strip() for l in bloco.split("\n") if l.strip()]
        if all(l.startswith(("-", "•", "*")) for l in linhas):
            items = "".join(f"<li>{l.lstrip('-•* ')}</li>" for l in linhas)
            paragrafos += f"<ul>{items}</ul>"
        elif bloco.startswith("**") and bloco.endswith("**"):
            texto = bloco.strip("*")
            paragrafos += f'<h2 class="sub">{texto}</h2>'
        else:
            texto = " ".join(linhas)
            partes = texto.split("**")
            out = []
            for i, p in enumerate(partes):
                out.append(f"<strong>{p}</strong>" if i % 2 == 1 else p)
            paragrafos += f'<p>{"".join(out)}</p>'

    return f"""
<h1 class="sec"><span class="num">5.</span>Análise Auditorial (IA)</h1>
<div class="aviso">
  <span class="tag">Nota sobre esta seção</span>
  Leitura redigida pelo Claude Sonnet sobre o relatório do motor.
  Não recalcula valores; comenta o que foi apurado.
</div>
{paragrafos}
"""


def _html_base_legal(secao: str = "5") -> str:
    return f"""
<h1 class="sec"><span class="num">{secao}.</span>Base Legal e Avisos</h1>
<div class="aviso ok">
  <span class="tag">Aviso de uso</span>
  Este laudo é software de apoio à auditoria. Não substitui o juízo do contador e do
  advogado responsáveis. A classificação de regime de cada bem, os valores de custo e os
  fatores de redução devem ser validados — estes últimos contra o programa GCAP oficial
  da RFB — antes de qualquer entrega.
</div>
<div class="norma">
  <div><b>Lei 9.532/97 Art. 23</b> — partilha do espólio; opção entre valor histórico
  (§2º) e valor de mercado (§1º).</div>
  <div><b>Lei 11.196/05 Arts. 39-40</b> — fatores de redução FR1 e FR2 para imóveis adquiridos antes de nov/2005.</div>
  <div><b>Lei 7.713/88 Art. 18</b> — redução por ano de aquisição anterior a 1989.</div>
  <div><b>Lei 7.713/88 Art. 6º XVI</b> — herança e doação: rendimento isento do IR.</div>
  <div><b>Lei 8.981/95 Art. 21 (Lei 13.259/16)</b> — alíquotas progressivas do ganho de capital (15% a 22,5%).</div>
  <div><b>IN SRF 599/2005 · RIR/2020 (Dec. 9.580/2018) Art. 150</b> — disposições complementares.</div>
</div>
<div class="assinatura">
  <div class="linha"></div>
  <div class="nome">Robson Alain Veloso</div>
  <div class="cargo">CRC/TO-002032/O-5 T-GO &nbsp;·&nbsp; ORGATEC Contabilidade e Auditoria</div>
</div>
<div class="encerr">
  Gerado pelo Sistema OrgAudi em {datetime.now().strftime("%d/%m/%Y às %H:%M")}.
  Este documento é sigiloso e destinado exclusivamente ao cliente identificado na capa.
</div>
"""


# ───────────────────────────────────────────────────────────────────────
# Funções públicas
# ───────────────────────────────────────────────────────────────────────

def gerar_laudo_html(
    espolio: Espolio,
    caminho_saida: Optional[str] = None,
    analise_ia: Optional[str] = None,
    tema: str = "light",
) -> str:
    """
    Gera o laudo em HTML.

    tema="light" → desktop, A4 print-ready (default)
    tema="dark"  → mobile dark-theme

    Retorna a string HTML e, se caminho_saida informado, salva o arquivo.
    """
    motor = MotorApuracao(espolio)
    resumo = motor.apurar()

    logo   = _logo_data_url()
    emissao = datetime.now().strftime("%d de %B de %Y").lower().capitalize()

    vars_css  = _CSS_VARS_DARK if tema == "dark" else _CSS_VARS_LIGHT
    extra_css = _CSS_DARK_MOBILE_OVERRIDES if tema == "dark" else ""
    viewport  = (
        '<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">'
        if tema == "dark" else ""
    )

    secao_ia  = _html_analise_ia(analise_ia) if analise_ia else ""
    secao_bas = _html_base_legal("6" if analise_ia else "5")

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Laudo OrgAudi — {espolio.nome}</title>
{viewport}
<style>
{vars_css}
{_CSS_BASE}
{extra_css}
{_CSS_RESPONSIVE}
</style>
</head>
<body>
{_html_capa(espolio, logo, emissao)}
<section class="conteudo">
{_html_resumo(resumo, espolio)}
{_html_apuracao(espolio)}
{_html_herdeiros(espolio)}
{_html_memoria_fr(espolio)}
{secao_ia}
{secao_bas}
</section>
</body>
</html>"""

    if caminho_saida:
        with open(caminho_saida, "w", encoding="utf-8") as f:
            f.write(html)

    return html


def gerar_laudo_html_dark(
    espolio: Espolio,
    caminho_saida: Optional[str] = None,
    analise_ia: Optional[str] = None,
) -> str:
    """Atalho para gerar_laudo_html com tema='dark' (mobile dark-theme)."""
    return gerar_laudo_html(espolio, caminho_saida, analise_ia, tema="dark")
