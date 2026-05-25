# -*- coding: utf-8 -*-
"""
backend/api.py — FastAPI expondo o pacote `orgaudi_espolio` para o frontend.

Endpoints:
  GET  /api/health
  GET  /api/exemplo                       espólio fictício para o estado inicial
  POST /api/apurar         {espolio}      → resumo + lista de bens detalhada
  POST /api/relatorio      {espolio}      → texto consolidado
  POST /api/laudo/xlsx     {espolio}      → .xlsx (binário)
  POST /api/laudo/pdf      {espolio, analise_ia?}  → .pdf (binário)
  POST /api/ia/extrair     multipart      → EspolioExtraido (Pydantic)
  POST /api/ia/analisar    {espolio}      → SSE de tokens do Sonnet
  POST /api/isencoes       {espolio}      → verificações de isenção
  POST /api/otimizar       {espolio}      → cenários recomendados

Sistema OrgAudi · ORGATEC CONTABILIDADE E AUDITORIA
"""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import uuid
from datetime import date, datetime
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

# adiciona src/ ao path
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "src"))

from orgaudi_espolio import (                                  # noqa: E402
    Bem, Espolio, Herdeiro,
    Regime, OpcaoArt23, StatusApuracao,
    MotorApuracao, Otimizador,
    verificar_isencoes,
    gerar_relatorio_texto, gerar_laudo_xlsx, gerar_laudo_pdf,
    gerar_laudo_html, gerar_laudo_html_dark, gerar_laudo_docx,
    extrair_de_pdfs, analisar_stream,
    regime_do_extraido, opcao_do_extraido,
    __version__,
)
from orgaudi_espolio.servicos import EspolioService
from orgaudi_espolio.anonimizador import AnonimizadorPII
from orgaudi_espolio.logging_config import configure_logging, get_logger
from orgaudi_espolio.reconciliador import ReconciliadorCognitivo

configure_logging()
_log = get_logger("api")


# ───────────────────────────────────────────────────────────────────────
# Modelos de entrada (espelham o domínio, com strings ISO para datas)
# ───────────────────────────────────────────────────────────────────────

class HerdeiroIn(BaseModel):
    nome: str
    cpf: str = ""
    fracao_monte: float
    eh_meeiro: bool = False

    @field_validator("fracao_monte")
    @classmethod
    def validar_fracao(cls, v: float) -> float:
        if v < 0 or v > 1:
            raise ValueError("A fração deve estar entre 0.0 e 1.0")
        return v


class BemIn(BaseModel):
    identificacao: str
    matricula: str = ""
    municipio: str = ""
    custo_aquisicao_dirpf: Optional[float] = None
    data_aquisicao: Optional[str] = None
    valor_partilha: Optional[float] = None
    valor_venda: Optional[float] = None
    regime: str
    data_operacao: Optional[str] = None
    opcao: str = OpcaoArt23.NAO_APLICAVEL.value
    eh_imovel: bool = True
    # B-2: imóvel rural — motor sinaliza regras de custo distintas (Lei 9.393/96)
    eh_imovel_rural: bool = False

    @field_validator("custo_aquisicao_dirpf", "valor_partilha", "valor_venda")
    @classmethod
    def validar_valores_nao_negativos(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("O valor não pode ser negativo")
        return v


class EspolioIn(BaseModel):
    nome: str
    cpf_falecido: str
    data_obito: str
    data_partilha: str
    herdeiros: list[HerdeiroIn] = Field(default_factory=list)
    bens: list[BemIn] = Field(default_factory=list)

    @field_validator("data_obito", "data_partilha")
    @classmethod
    def validar_formato_data(cls, v: str) -> str:
        if v:
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError:
                raise ValueError("Data deve estar no formato YYYY-MM-DD")
        return v


class AnaliseIn(BaseModel):
    espolio: EspolioIn
    api_key: Optional[str] = None


class LaudoPdfIn(BaseModel):
    espolio: EspolioIn
    analise_ia: Optional[str] = None


# ───────────────────────────────────────────────────────────────────────
# Conversões
# ───────────────────────────────────────────────────────────────────────

def _slug(texto: str) -> str:
    import unicodedata, re
    s = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^\w\-_]+", "_", s).strip("_").lower()


def _serializa_bem(b: Bem) -> dict:
    r = b.resultado or {}
    fr = r.get("fatores_reducao")
    fr_dump = None
    if fr is not None:
        fr_dump = {
            "aplicavel": fr.aplicavel,
            "motivo_inaplicavel": fr.motivo_inaplicavel,
            "memoria": fr.memoria,
            "m1": fr.m1, "m2": fr.m2,
            "fr1": fr.fr1, "fr2": fr.fr2,
            "reducao_7713": fr.reducao_7713,
            "base_calculo_final": fr.base_calculo_final,
        }
    return {
        "identificacao": b.identificacao,
        "matricula": b.matricula,
        "regime": b.regime.value,
        "opcao": b.opcao.value,
        "eh_imovel": b.eh_imovel,
        "custo_aquisicao_dirpf": b.custo_aquisicao_dirpf,
        "data_aquisicao": b.data_aquisicao.isoformat() if b.data_aquisicao else None,
        "valor_partilha": b.valor_partilha,
        "valor_venda": b.valor_venda,
        "data_operacao": b.data_operacao.isoformat() if b.data_operacao else None,
        "pendencias": b.pendencias,
        "resultado": {
            "status": r.get("status").value if r.get("status") else None,
            "regime": r.get("regime"),
            "ganho_bruto": r.get("ganho_bruto"),
            "ganho_diferido": r.get("ganho_diferido"),
            "base_tributavel": r.get("base_tributavel"),
            "base_tributavel_meeiro": r.get("base_tributavel_meeiro"),
            "base_custo_herdeiro": r.get("base_custo_herdeiro"),
            "ir_espolio": r.get("ir_espolio"),
            "ir_meeiro": r.get("ir_meeiro"),
            "ir_herdeiros": r.get("ir_herdeiros"),
            "nota": r.get("nota"),
            "alerta_reducao": r.get("alerta_reducao"),
            "fatores_reducao": fr_dump,
        },
    }


# ───────────────────────────────────────────────────────────────────────
# App
# ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="OrgAudi · Espólio API",
    version=__version__,
    description="Apuração de IR sobre ganho de capital em sucessão.",
)

# B-5: middleware de logging de requisições
import time, uuid as _uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

class _RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        rid = _uuid.uuid4().hex[:12]
        t0 = time.perf_counter()
        response = await call_next(request)
        ms = round((time.perf_counter() - t0) * 1000, 1)
        _log.info(
            "request",
            extra={
                "request_id": rid,
                "endpoint": str(request.url.path),
                "method": request.method,
                "status": response.status_code,
                "duration_ms": ms,
            },
        )
        return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(_RequestLogMiddleware)


@app.get("/api/health")
def health():
    return {"status": "ok", "version": __version__,
            "anthropic_key_set": bool(os.environ.get("ANTHROPIC_API_KEY"))}


@app.get("/api/exemplo")
def exemplo():
    """Espólio fictício — para inicialização da UI."""
    return {
        "nome": "Espólio Adilson Exemplo",
        "cpf_falecido": "000.000.000-00",
        "data_obito": "2023-09-27",
        "data_partilha": "2025-07-16",
        "herdeiros": [
            {"nome": "Filho 1", "cpf": "111.111.111-11",
             "fracao_monte": 0.25, "eh_meeiro": False},
            {"nome": "Filho 2", "cpf": "222.222.222-22",
             "fracao_monte": 0.25, "eh_meeiro": False},
            {"nome": "Filho 3", "cpf": "333.333.333-33",
             "fracao_monte": 0.25, "eh_meeiro": False},
            {"nome": "Cônjuge", "cpf": "444.444.444-44",
             "fracao_monte": 0.25, "eh_meeiro": True},
        ],
        "bens": [
            {"identificacao": "Lote A — Casa residencial",
             "matricula": "12345",
             "regime": Regime.TRANSMISSAO_HERDEIRO.value,
             "opcao": OpcaoArt23.VALOR_HISTORICO.value,
             "eh_imovel": True,
             "custo_aquisicao_dirpf": 12500.00,
             "data_aquisicao": "2003-07-24",
             "valor_partilha": 130000.00},
            {"identificacao": "Lote B — Imóvel rural (chácara)",
             "matricula": "67890",
             "regime": Regime.VENDA_PELO_ESPOLIO.value,
             "opcao": OpcaoArt23.NAO_APLICAVEL.value,
             "eh_imovel": True,
             "custo_aquisicao_dirpf": 42000.00,
             "data_aquisicao": "1985-03-10",
             "valor_venda": 1536000.00,
             "data_operacao": "2024-08-14"},
            {"identificacao": "Cotas BRADIV LTDA (15%)",
             "regime": Regime.CESSAO_DIREITOS_HEREDITARIOS.value,
             "opcao": OpcaoArt23.NAO_APLICAVEL.value,
             "eh_imovel": False,
             "custo_aquisicao_dirpf": 1050000.00,
             "data_aquisicao": "2018-06-05",
             "valor_venda": 2400000.00,
             "data_operacao": "2024-11-20"},
            {"identificacao": "Veículo X (vendido em vida 2021)",
             "regime": Regime.FORA_DO_ESPOLIO.value,
             "opcao": OpcaoArt23.NAO_APLICAVEL.value,
             "eh_imovel": False},
        ],
    }


@app.post("/api/apurar")
def apurar(data: EspolioIn):
    espolio = EspolioService.converter_para_dominio(data.model_dump())
    resumo = MotorApuracao(espolio).apurar()
    audit_hash = EspolioService.calcular_audit_hash(espolio)
    resumo["audit_hash"] = audit_hash
    _log.info(
        "apuracao concluida",
        extra={
            "espolio_hash": audit_hash[:16],
            "bens_conclusivos": resumo["bens_conclusivos"],
            "bens_pendentes": resumo["bens_pendentes"],
            "ir_total": resumo["ir_espolio_total"],
        },
    )
    return {
        "resumo": resumo,
        "bens": [_serializa_bem(b) for b in espolio.bens],
    }


@app.post("/api/relatorio")
def relatorio(data: EspolioIn):
    espolio = EspolioService.converter_para_dominio(data.model_dump())
    return {"texto": gerar_relatorio_texto(espolio)}


@app.post("/api/otimizar")
def otimizar(data: EspolioIn):
    espolio = EspolioService.converter_para_dominio(data.model_dump())
    MotorApuracao(espolio).apurar()  # popula resultados
    recs = Otimizador(espolio).otimizar()
    return [{
        "bem": rec.bem.identificacao,
        "economia_vs_pior": rec.economia_vs_pior,
        "recomendado": {
            "descricao": rec.recomendado.descricao,
            "base_legal": rec.recomendado.base_legal,
            "ir_espolio": rec.recomendado.ir_espolio,
            "ir_herdeiros_futuro_estimado":
                rec.recomendado.ir_herdeiros_futuro_estimado,
            "observacao": rec.recomendado.observacao,
        },
        "cenarios": [{
            "descricao": c.descricao,
            "base_legal": c.base_legal,
            "ir_espolio": c.ir_espolio,
            "ir_herdeiros_futuro_estimado": c.ir_herdeiros_futuro_estimado,
            "observacao": c.observacao,
        } for c in rec.cenarios],
        "nota_decisao": rec.nota_decisao,
    } for rec in recs]


@app.post("/api/isencoes")
def isencoes(data: EspolioIn):
    espolio = EspolioService.converter_para_dominio(data.model_dump())
    out: list[dict] = []
    for b in espolio.bens:
        for v in verificar_isencoes(b):
            out.append({
                "bem": b.identificacao,
                "isencao": v.isencao,
                "base_legal": v.base_legal,
                "elegivel_em_tese": v.elegivel_em_tese,
                "requisitos_a_confirmar": v.requisitos_a_confirmar,
                "observacao": v.observacao,
            })
    return out


@app.post("/api/reconciliar")
def reconciliar_ia(data: AnaliseIn):
    espolio = EspolioService.converter_para_dominio(data.espolio.model_dump())
    
    # Anonimiza localmente os dados sensíveis (PII) antes de enviar para a LLM (Soberania de Dados)
    espolio_anom, mapeamento = AnonimizadorPII.anonimizar(espolio)
    
    try:
        divergencias_anom = ReconciliadorCognitivo.reconciliar_apuracao(espolio_anom, api_key=data.api_key)
        
        # Desanonimiza os resultados localmente antes de entregar ao usuário
        divergencias = []
        for div in divergencias_anom:
            bem_original = AnonimizadorPII.desanonimizar(div.bem, mapeamento)
            justificativa_original = AnonimizadorPII.desanonimizar(div.justificativa_ia, mapeamento)
            divergencias.append({
                "bem": bem_original,
                "campo": div.campo,
                "valor_motor": div.valor_motor,
                "valor_ia": div.valor_ia,
                "justificativa_ia": justificativa_original,
                "observacao": div.observacao
            })
        
        _log.info(
            "reconciliacao cognitiva concluida",
            extra={
                "espolio_hash": EspolioService.calcular_audit_hash(espolio)[:16],
                "divergencias_detectadas": len(divergencias),
            }
        )
        return divergencias
    except Exception as e:
        _log.error("erro na reconciliacao cognitiva", extra={"erro": str(e)})
        raise HTTPException(500, f"Erro na reconciliação cognitiva: {e}")


@app.post("/api/laudo/xlsx")
def laudo_xlsx(data: EspolioIn):
    espolio = EspolioService.converter_para_dominio(data.model_dump())
    # A-3: uuid4 evita race condition quando múltiplas requisições concorrentes
    tmp = os.path.join(tempfile.gettempdir(), f"laudo_{uuid.uuid4().hex}.xlsx")
    gerar_laudo_xlsx(espolio, tmp)
    with open(tmp, "rb") as f:
        body = f.read()
    try:
        os.remove(tmp)
    except OSError:
        pass
    return Response(
        content=body,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"),
        headers={"Content-Disposition":
                 f'attachment; filename="laudo.xlsx"'},
    )


@app.post("/api/laudo/pdf")
def laudo_pdf(data: LaudoPdfIn):
    espolio = EspolioService.converter_para_dominio(data.espolio.model_dump())
    _, mapeamento = AnonimizadorPII.anonimizar(espolio)
    analise_ia_limpa = AnonimizadorPII.desanonimizar(data.analise_ia or "", mapeamento)
    # A-3: uuid4 evita race condition quando múltiplas requisições concorrentes
    tmp = os.path.join(tempfile.gettempdir(), f"laudo_{uuid.uuid4().hex}.pdf")
    gerar_laudo_pdf(espolio, tmp, analise_ia=analise_ia_limpa)
    with open(tmp, "rb") as f:
        body = f.read()
    try:
        os.remove(tmp)
    except OSError:
        pass
    return Response(
        content=body,
        media_type="application/pdf",
        headers={"Content-Disposition":
                 f'attachment; filename="laudo.pdf"'},
    )


@app.post("/api/laudo/html")
def laudo_html_light(data: EspolioIn):
    espolio = EspolioService.converter_para_dominio(data.model_dump())
    content = gerar_laudo_html(espolio, tema="light")
    nome_slug = _slug(espolio.nome)
    return Response(
        content=content.encode("utf-8"),
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition":
                 f'attachment; filename="laudo_{nome_slug}.html"'},
    )


@app.post("/api/laudo/html-dark")
def laudo_html_dark_mobile(data: EspolioIn):
    espolio = EspolioService.converter_para_dominio(data.model_dump())
    content = gerar_laudo_html_dark(espolio)
    nome_slug = _slug(espolio.nome)
    return Response(
        content=content.encode("utf-8"),
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition":
                 f'attachment; filename="laudo_dark_{nome_slug}.html"'},
    )


@app.post("/api/laudo/docx")
def laudo_docx_endpoint(data: EspolioIn):
    espolio = EspolioService.converter_para_dominio(data.model_dump())
    tmp = os.path.join(tempfile.gettempdir(), f"laudo_{uuid.uuid4().hex}.docx")
    gerar_laudo_docx(espolio, tmp)
    with open(tmp, "rb") as f:
        body = f.read()
    try:
        os.remove(tmp)
    except OSError:
        pass
    nome_slug = _slug(espolio.nome)
    return Response(
        content=body,
        media_type=(
            "application/vnd.openxmlformats-officedocument"
            ".wordprocessingml.document"),
        headers={"Content-Disposition":
                 f'attachment; filename="laudo_{nome_slug}.docx"'},
    )


def gerar_laudo_markdown_interativo(espolio: Espolio) -> str:
    # 1. Serializa bens e herdeiros em formato JSON para injetar no script JS
    bens_json = []
    for b in espolio.bens:
        bens_json.append({
            "identificacao": b.identificacao,
            "matricula": b.matricula,
            "custo_aquisicao_dirpf": b.custo_aquisicao_dirpf or 0.0,
            "valor_partilha": b.valor_partilha or 0.0,
            "valor_venda": b.valor_venda or 0.0,
            "regime": b.regime.value,
            "opcao": b.opcao.value,
            "eh_imovel": b.eh_imovel,
        })
    
    herdeiros_json = []
    for h in espolio.herdeiros:
        herdeiros_json.append({
            "nome": h.nome,
            "cpf": h.cpf,
            "fracao_monte": h.fracao_monte,
            "eh_meeiro": h.eh_meeiro,
        })

    bens_js_str = json.dumps(bens_json, indent=2, ensure_ascii=False)
    herdeiros_js_str = json.dumps(herdeiros_json, indent=2, ensure_ascii=False)
    
    # 2. Template de Markdown Interativo com chaves duplicadas para escapar o .format()
    markdown_template = """<script src="https://cdn.tailwindcss.com"></script>

# 🏛️ Dossiê Forense Interativo — Espólio de {nome_falecido}

Este documento técnico de conformidade e planejamento sucessório foi gerado de forma dinâmica. Ele integra a análise de riscos de autuação (Gama Profile) com a simulação quantitativa dos cenários pós-Reforma Tributária (Sigma Profile).

---

## ⚖️ Painel de Simulação Forense em Tempo Real

Abaixo está o componente interativo que roda localmente no VS Code. Você pode ajustar a alíquota estimada da reforma (IBS/CBS), bem como editar os custos de aquisição e valores de partilha de cada bem listado para recalcular o imposto em tempo real.

```jsx live
function SimuladorEspolio() {{
  const BENS_INICIAIS = {bens_json};
  const HERDEIROS_INICIAIS = {herdeiros_json};

  const [bens, setBens] = React.useState(BENS_INICIAIS);
  const [aliquotaReforma, setAliquotaReforma] = React.useState(26.5);

  const atualizarBem = (index, campo, valor) => {{
    const novosBens = [...bens];
    novosBens[index][campo] = Number(valor);
    setBens(novosBens);
  }};

  // Cálculos dinâmicos
  let totalCusto = 0;
  let totalPartilha = 0;
  let impostoAtualTotal = 0;
  let impostoReformaTotal = 0;
  let bensSemCusto = 0;

  bens.forEach(b => {{
    const custo = b.custo_aquisicao_dirpf || 0;
    const partilha = b.valor_partilha || 0;
    totalCusto += custo;
    totalPartilha += partilha;

    const ganho = Math.max(0, partilha - custo);
    impostoAtualTotal += ganho * 0.15; // Simulação de 15% fixa no GCAP
    impostoReformaTotal += ganho * (aliquotaReforma / 100);

    if (custo <= 0) {{
      bensSemCusto += 1;
    }}
  }});

  const somaFracoes = HERDEIROS_INICIAIS.reduce((acc, h) => acc + h.fracao_monte, 0);
  const fracoesInvalidas = Math.abs(somaFracoes - 1.0) > 0.001;

  // Lógica de Risco Forense (@Gama)
  let scoreRisco = bensSemCusto * 15;
  if (fracoesInvalidas) scoreRisco += 35;
  const herdeirosSemCpf = HERDEIROS_INICIAIS.filter(h => !h.cpf).length;
  scoreRisco += herdeirosSemCpf * 10;
  const risco = Math.min(scoreRisco, 99);

  return (
    <div className="p-6 bg-slate-900 text-slate-100 rounded-xl border border-white/10 shadow-2xl font-sans">
      <h3 className="m-0 mb-4 text-sky-400 text-lg font-semibold flex items-center gap-2 border-b border-white/10 pb-2">
        <span>🔍</span> Simulador de Cenários Tributários
      </h3>

      {{/* Grid de Controles */}}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div>
          <label className="block mb-1 text-xs text-slate-400 font-medium">
            Alíquota Estimada da Reforma (IBS/CBS): {{aliquotaReforma}}%
          </label>
          <input 
            type="range" 
            min="20" 
            max="35" 
            step="0.5" 
            value={{aliquotaReforma}} 
            onChange={{e => setAliquotaReforma(Number(e.target.value))}}
            className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-sky-500"
          />
          <div className="flex justify-between text-[10px] text-slate-500 mt-1">
            <span>20% (Mínimo)</span>
            <span>26.5% (Estimado)</span>
            <span>35% (Máximo)</span>
          </div>
        </div>

        <div className="bg-white/5 p-3 rounded-lg border border-white/5 text-xs">
          <span className="text-slate-400 font-medium block">Resumo de Consistência</span>
          <ul className="list-disc list-inside mt-1 space-y-1 text-slate-300">
            <li>Soma das Frações: <strong className={{color: fracoesInvalidas ? '#f87171' : '#4ade80'}}>{{(somaFracoes * 100).toFixed(1)}}%</strong></li>
            <li>Bens sem Custo DIRPF: <strong>{{bensSemCusto}}</strong></li>
            <li>Herdeiros sem CPF: <strong>{{herdeirosSemCpf}}</strong></li>
          </ul>
        </div>
      </div>

      {{/* Tabela de Bens */}}
      <div className="mb-6 overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-white/10 text-slate-400">
              <th className="py-2">Identificação</th>
              <th className="py-2 px-2 w-28">Custo DIRPF (R$)</th>
              <th className="py-2 px-2 w-28">Partilha/Venda (R$)</th>
              <th className="py-2 text-right">Ganho Estimado</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {{bens.map((b, idx) => {{
              const ganho = Math.max(0, b.valor_partilha - b.custo_aquisicao_dirpf);
              return (
                <tr key={{idx}} className="hover:bg-white/5 transition-colors">
                  <td className="py-2 text-slate-300 truncate max-w-[180px]" title={{b.identificacao}}>{{b.identificacao}}</td>
                  <td className="py-2 px-2">
                    <input 
                      type="number" 
                      value={{b.custo_aquisicao_dirpf}} 
                      onChange={{e => atualizarBem(idx, 'custo_aquisicao_dirpf', e.target.value)}}
                      className="w-full p-1 rounded bg-slate-950 border border-slate-700 text-slate-100 text-xs focus:ring-1 focus:ring-sky-500 focus:outline-none"
                    />
                  </td>
                  <td className="py-2 px-2">
                    <input 
                      type="number" 
                      value={{b.valor_partilha}} 
                      onChange={{e => atualizarBem(idx, 'valor_partilha', e.target.value)}}
                      className="w-full p-1 rounded bg-slate-950 border border-slate-700 text-slate-100 text-xs focus:ring-1 focus:ring-sky-500 focus:outline-none"
                    />
                  </td>
                  <td className="py-2 text-right text-slate-400 font-mono">
                    R$ {{ganho.toLocaleString('pt-BR', {{minimumFractionDigits: 0, maximumFractionDigits: 0}})}}
                  </td>
                </tr>
              );
            }})}}
          </tbody>
        </table>
      </div>

      {{/* Resultados de Métricas */}}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 border-t border-white/10 pt-4">
        <div className="bg-white/5 p-3 rounded-lg border border-white/5">
          <span className="text-[10px] text-slate-400 block font-medium uppercase tracking-wider">Risco de Autuação</span>
          <div className={{`text-2xl font-bold mt-1 ${{risco > 50 ? 'text-red-400' : 'text-emerald-400'}}`}}>
            {{risco}}%
          </div>
          <span className="text-[9px] text-slate-500 block mt-1">Baseado em anomalias de conformidade</span>
        </div>

        <div className="bg-white/5 p-3 rounded-lg border border-white/5">
          <span className="text-[10px] text-slate-400 block font-medium uppercase tracking-wider">IR Espólio Atual</span>
          <div className="text-2xl font-bold mt-1 text-sky-400 font-mono">
            R$ {{impostoAtualTotal.toLocaleString('pt-BR', {{maximumFractionDigits: 0}})}}
          </div>
          <span className="text-[9px] text-slate-500 block mt-1">Alíquota linear de 15% (GCAP)</span>
        </div>

        <div className="bg-white/5 p-3 rounded-lg border border-white/5">
          <span className="text-[10px] text-slate-400 block font-medium uppercase tracking-wider">Simulado Reforma</span>
          <div className="text-2xl font-bold mt-1 text-orange-400 font-mono">
            R$ {{impostoReformaTotal.toLocaleString('pt-BR', {{maximumFractionDigits: 0}})}}
          </div>
          <span className="text-[9px] text-slate-500 block mt-1">Diferença: +R$ {{(impostoReformaTotal - impostoAtualTotal).toLocaleString('pt-BR', {{maximumFractionDigits: 0}})}}</span>
        </div>
      </div>
    </div>
  );
}}
```

---

## 📋 Informações Gerais do Inventário

* **Nome do Falecido:** {nome_falecido}
* **CPF do Falecido:** {cpf_falecido}
* **Data do Óbito:** {data_obito}
* **Data da Partilha:** {data_partilha}
* **Assinatura de Integridade (Audit Hash):** `{audit_hash}`

### 👤 Lista de Herdeiros Cadastrados
{herdeiros_lista_md}

---

> **Aviso de Responsabilidade:** Este laudo interativo constitui uma simulação baseada em dados inseridos localmente e não substitui o parecer jurídico final dos assessores e contadores da ORGATEC CONTABILIDADE E AUDITORIA.
"""

    herdeiros_lista_md = ""
    for h in espolio.herdeiros:
        meeiro_tag = " (Meeiro)" if h.eh_meeiro else ""
        cpf_str = h.cpf if h.cpf else "CPF não informado"
        herdeiros_lista_md += f"* **{h.nome}** - CPF: {cpf_str} - Fração: {h.fracao_monte*100:.1f}%{meeiro_tag}\\n"

    if not herdeiros_lista_md:
        herdeiros_lista_md = "* Nenhum herdeiro cadastrado."

    audit_hash = EspolioService.calcular_audit_hash(espolio)
    return markdown_template.format(
        nome_falecido=espolio.nome,
        cpf_falecido=espolio.cpf_falecido,
        data_obito=espolio.data_obito.isoformat() if espolio.data_obito else "-",
        data_partilha=espolio.data_partilha.isoformat() if espolio.data_partilha else "-",
        bens_json=bens_js_str,
        herdeiros_json=herdeiros_js_str,
        herdeiros_lista_md=herdeiros_lista_md,
        audit_hash=audit_hash
    )


@app.post("/api/laudo/reactive")
def laudo_reactive(data: EspolioIn):
    espolio = EspolioService.converter_para_dominio(data.model_dump())
    MotorApuracao(espolio).apurar()  # popula resultados
    content = gerar_laudo_markdown_interativo(espolio)
    return Response(
        content=content,
        media_type="text/markdown",
        headers={"Content-Disposition":
                 f'attachment; filename="laudo_interativo_{_slug(espolio.nome)}.md"'},
    )


@app.post("/api/ia/extrair")
async def ia_extrair(
    files: list[UploadFile] = File(...),
    instrucao_extra: str = Form(""),
    api_key: Optional[str] = Form(None),
):
    if not files:
        raise HTTPException(400, "Nenhum arquivo enviado.")
    docs: list[tuple[str, bytes]] = []
    for f in files:
        if f.content_type and "pdf" not in f.content_type.lower():
            raise HTTPException(
                400, f"Arquivo {f.filename!r} não é PDF "
                     f"(content-type {f.content_type}).")
        docs.append((f.filename or "documento.pdf", await f.read()))
    try:
        extraido, uso = extrair_de_pdfs(
            docs, instrucao_extra=instrucao_extra, api_key=api_key,
        )
    except RuntimeError as e:
        raise HTTPException(401, str(e))
    except Exception as e:
        raise HTTPException(500, f"Falha na extração: {e}")
    return {
        "espolio": extraido.model_dump(),
        "uso": uso,
    }


@app.post("/api/ia/analisar")
def ia_analisar(data: AnaliseIn):
    """Server-Sent Events com tokens do Sonnet."""
    espolio = EspolioService.converter_para_dominio(data.espolio.model_dump())
    espolio_anom, mapeamento = AnonimizadorPII.anonimizar(espolio)

    def gerar():
        try:
            texto_cru = ""
            texto_limpo_acumulado = ""
            for delta in analisar_stream(espolio_anom, api_key=data.api_key):
                texto_cru += delta
                texto_limpo_atual = AnonimizadorPII.desanonimizar(texto_cru, mapeamento)
                
                # Emitir a diferença limpa
                novo_delta = texto_limpo_atual[len(texto_limpo_acumulado):]
                texto_limpo_acumulado = texto_limpo_atual
                
                if novo_delta:
                    yield f"data: {json.dumps({'t': novo_delta})}\n\n"
            yield "event: done\ndata: {}\n\n"
        except RuntimeError as e:
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"
        except Exception as e:
            yield (f"event: error\n"
                   f"data: {json.dumps({'message': f'{type(e).__name__}: {e}'})}\n\n")

    return StreamingResponse(
        gerar(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache",
                 "X-Accel-Buffering": "no"},
    )


# Serve o frontend buildado — deve ficar APÓS todas as rotas /api/*
_DIST = os.path.join(_HERE, "..", "frontend", "dist")
if os.path.isdir(_DIST):
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="spa")
