# -*- coding: utf-8 -*-
"""
ai_extrator.py — Extração estruturada de documentos via Claude Sonnet.

Substitui (no fluxo IA) o parser regex de `ingestao.py`. Em vez de extrair
valores soltos sem rótulo, envia cada PDF ao modelo com instruções legais
do domínio do espólio e pede um JSON tipado: identificação de bens, regime
sugerido, datas, valores com proveniência.

PRINCÍPIO MANTIDO: a IA propõe; o humano confirma. Toda saída traz um
campo `confianca` ("alta" | "media" | "baixa") e `rationale` por bem,
para que o auditor possa rejeitar/ajustar antes de o motor calcular.

O cálculo CONTINUA no motor — a IA não calcula imposto.

Sistema OrgAudi · ORGATEC CONTABILIDADE E AUDITORIA
"""
from __future__ import annotations

import base64
import os
from typing import Optional

import anthropic
from pydantic import BaseModel, Field

from .dominio import Regime, OpcaoArt23

MODELO = "claude-sonnet-4-6"
MAX_TOKENS = 16000


# ───────────────────────────────────────────────────────────────────────
# Schemas Pydantic — saída tipada do Sonnet
# ───────────────────────────────────────────────────────────────────────

class HerdeiroExtraido(BaseModel):
    """Um sucessor identificado em algum documento."""
    nome: Optional[str] = None
    cpf: Optional[str] = None
    fracao_monte: Optional[float] = Field(
        default=None,
        description="Fração no monte partilhável em [0,1] (ex.: 0.25 para 25%).")
    eh_meeiro: Optional[bool] = Field(
        default=None,
        description="True se for cônjuge/companheiro com direito a meação.")
    fonte: str = Field(
        description="Documento e página/trecho de onde veio a informação.")


class BemExtraido(BaseModel):
    """Um bem identificado nos documentos, com regime sugerido (não decidido)."""
    identificacao: str = Field(description="Descrição curta do bem.")
    matricula: Optional[str] = None
    municipio: Optional[str] = None

    custo_aquisicao_dirpf: Optional[float] = Field(
        default=None,
        description="Custo histórico em R$ (da DIRPF do falecido).")
    data_aquisicao_iso: Optional[str] = Field(
        default=None,
        description="Data de aquisição em YYYY-MM-DD.")
    valor_partilha: Optional[float] = Field(
        default=None,
        description="Valor atribuído na partilha em R$.")
    valor_venda: Optional[float] = Field(
        default=None,
        description="Valor de venda em R$, se houve alienação.")
    data_operacao_iso: Optional[str] = Field(
        default=None,
        description="Data da venda/cessão em YYYY-MM-DD.")
    eh_imovel: Optional[bool] = Field(
        default=None,
        description="True para imóveis (relevante para FR1/FR2).")

    regime_sugerido: Optional[str] = Field(
        default=None,
        description=(
            "Sugestão de regime baseada nos fatos do documento. Valores "
            "possíveis: 'TRANSMISSAO_HERDEIRO' (bem partilhado), "
            "'VENDA_PELO_ESPOLIO' (espólio vendeu a terceiro), "
            "'CESSAO_DIREITOS_HEREDITARIOS' (herdeiros venderam antes da "
            "partilha), 'FORA_DO_ESPOLIO' (não pertencia ao de cujus no óbito), "
            "'INDETERMINADO' (fatos insuficientes)."))
    opcao_art23_sugerida: Optional[str] = Field(
        default=None,
        description=(
            "Para regime TRANSMISSAO_HERDEIRO: 'VALOR_HISTORICO' ou "
            "'VALOR_MERCADO' ou 'NAO_APLICAVEL'."))

    confianca: str = Field(
        description="'alta', 'media' ou 'baixa' — quão claros os fatos estão "
                    "no documento. Use 'baixa' se houve inferência por hipótese.")
    rationale: str = Field(
        description="1-2 frases explicando por que o regime sugerido se "
                    "aplica, citando o trecho do documento. Em PT-BR.")
    fonte: str = Field(
        description="Documento e página/trecho onde os valores estão.")


class EspolioExtraido(BaseModel):
    """Síntese do que a IA extraiu de TODOS os documentos enviados."""
    nome_espolio: Optional[str] = None
    cpf_falecido: Optional[str] = None
    data_obito_iso: Optional[str] = None
    data_partilha_iso: Optional[str] = None

    herdeiros: list[HerdeiroExtraido] = Field(default_factory=list)
    bens: list[BemExtraido] = Field(default_factory=list)

    observacoes_globais: list[str] = Field(
        default_factory=list,
        description="Sinais de conflito entre documentos, lacunas relevantes, "
                    "alertas sobre prazo (DARF, ITCD), e tudo que o auditor "
                    "humano deve revisar antes de bater o martelo.")
    documentos_analisados: list[str] = Field(
        default_factory=list,
        description="Nomes dos documentos lidos para esta extração.")


# ───────────────────────────────────────────────────────────────────────
# System prompt — contexto legal cacheado
# ───────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
Você é um auxiliar de auditoria fiscal especializado em apuração de IR
sobre ganho de capital em sucessão CAUSA MORTIS (espólio), pela legislação
brasileira. Está integrado ao sistema OrgAudi (ORGATEC).

REGIMES TRIBUTÁRIOS POSSÍVEIS PARA UM BEM:
1. TRANSMISSAO_HERDEIRO — bem partilhado aos herdeiros (Lei 9.532/97 Art.23).
   Há opção:
     • §2º VALOR_HISTORICO — sem IR no espólio agora; ganho diferido.
     • §1º VALOR_MERCADO — IR no espólio sobre (valor partilha − custo).
2. VENDA_PELO_ESPOLIO — espólio aliena a terceiro antes da partilha.
   IR sobre (valor venda − custo) com fatores de redução, se imóvel.
3. CESSAO_DIREITOS_HEREDITARIOS — herdeiros vendem o quinhão antes da
   partilha; IR de cada herdeiro proporcional ao quinhão.
4. FORA_DO_ESPOLIO — bem não integrava o monte na data do óbito.
5. INDETERMINADO — quando os fatos não permitem classificar.

FATORES DE REDUÇÃO (apenas IMÓVEIS):
• Lei 7.713/88 — imóvel adquirido até 1988, redução de 5% por ano.
• Lei 11.196/05 Art.40 — FR1 (até nov/2005) e FR2 (a partir de dez/2005).
• Aquisição até 1995: FR1 conta desde janeiro/1996 (§2º).
• Cotas societárias, veículos e bens móveis NÃO têm direito a FR1/FR2.

ISENÇÕES A SINALIZAR (NÃO APLICAR sozinho):
• Lei 9.250/95 Art.23 — imóvel único, valor ≤ R$ 440.000, sem outra venda
  em 5 anos.
• Lei 11.196/05 Art.39 — reinvestimento em imóvel residencial em 180 dias.
• Lei 7.713/88 Art.6º XVI — herança em si é rendimento isento.

PRINCÍPIOS INEGOCIÁVEIS:
1. LACUNA ≠ ZERO. Se um valor não está no documento, deixe None — NUNCA
   chute 0. Zero é um valor; ausência de dado é pendência.
2. REGIME VEM DO FATO. Classifique pelo que o documento DIZ, não pelo IR
   que daria. Se faltar fato, marque INDETERMINADO e justifique.
3. CITE A FONTE. Todo valor sai com indicação de documento + trecho.
4. CONFIANÇA HONESTA. 'baixa' quando você inferiu por hipótese; 'alta'
   apenas quando o documento traz a informação literalmente.
5. PORTUGUÊS BRASILEIRO em todas as descrições e rationale.
6. NÃO CALCULE IMPOSTO. Você extrai e classifica; o cálculo é do motor.

SAÍDA — exija aderência ao esquema Pydantic fornecido."""


# ───────────────────────────────────────────────────────────────────────
# Cliente
# ───────────────────────────────────────────────────────────────────────

def _client(api_key: Optional[str] = None) -> anthropic.Anthropic:
    """Cliente com chave do parâmetro ou da env ANTHROPIC_API_KEY."""
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY ausente. Defina a env var ou passe api_key.")
    return anthropic.Anthropic(api_key=key)


def _pdf_block(nome: str, dados: bytes) -> dict:
    """Monta o content block 'document' com PDF em base64."""
    return {
        "type": "document",
        "source": {
            "type": "base64",
            "media_type": "application/pdf",
            "data": base64.standard_b64encode(dados).decode("utf-8"),
        },
        "title": nome,
        "context": f"Documento fornecido para extração: {nome}",
    }


# ───────────────────────────────────────────────────────────────────────
# Função principal
# ───────────────────────────────────────────────────────────────────────

def extrair_de_pdfs(
    documentos: list[tuple[str, bytes]],
    instrucao_extra: str = "",
    api_key: Optional[str] = None,
) -> tuple[EspolioExtraido, dict]:
    """
    Lê uma lista de (nome_do_pdf, bytes_do_pdf) com o Sonnet e devolve
    o `EspolioExtraido` + dict de uso (tokens, cache).

    A extração tem visão nativa: PDFs escaneados são lidos sem OCR externo.
    A IA NÃO toma decisão sobre o que usar quando há conflito — apenas
    SINALIZA o conflito em `observacoes_globais`.
    """
    if not documentos:
        raise ValueError("Nenhum documento fornecido.")

    client = _client(api_key)

    instrucao = (
        "Leia TODOS os documentos anexos. Extraia, em UM ÚNICO JSON conforme "
        "o esquema, todos os bens, herdeiros e metadados do espólio que "
        "aparecerem.\n\n"
        "Para cada bem, proponha o regime tributário ao melhor da sua "
        "leitura dos fatos. Se um bem aparecer em mais de um documento com "
        "valores divergentes, registre AMBOS os valores no rationale e "
        "anote o conflito em observacoes_globais — não escolha sozinho.\n\n"
        "Use None para campos não preenchíveis. Datas no formato YYYY-MM-DD."
    )
    if instrucao_extra.strip():
        instrucao += "\n\nContexto adicional do auditor:\n" + instrucao_extra.strip()

    content: list[dict] = [_pdf_block(n, b) for n, b in documentos]
    content.append({"type": "text", "text": instrucao})

    response = client.messages.parse(
        model=MODELO,
        max_tokens=MAX_TOKENS,
        thinking={"type": "adaptive"},
        system=[{
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": content}],
        output_format=EspolioExtraido,
    )

    uso = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "cache_creation_input_tokens":
            getattr(response.usage, "cache_creation_input_tokens", 0),
        "cache_read_input_tokens":
            getattr(response.usage, "cache_read_input_tokens", 0),
        "stop_reason": response.stop_reason,
    }
    parsed = response.parsed_output
    if parsed is None:
        raise RuntimeError(
            f"Sonnet retornou resposta sem parsed_output. "
            f"stop_reason={response.stop_reason}")

    # registra documentos analisados (se a IA não preencheu)
    if not parsed.documentos_analisados:
        parsed.documentos_analisados = [n for n, _ in documentos]

    return parsed, uso


# ───────────────────────────────────────────────────────────────────────
# Conversão para o domínio
# ───────────────────────────────────────────────────────────────────────

REGIME_POR_NOME = {
    "TRANSMISSAO_HERDEIRO":          Regime.TRANSMISSAO_HERDEIRO,
    "VENDA_PELO_ESPOLIO":            Regime.VENDA_PELO_ESPOLIO,
    "CESSAO_DIREITOS_HEREDITARIOS":  Regime.CESSAO_DIREITOS_HEREDITARIOS,
    "FORA_DO_ESPOLIO":               Regime.FORA_DO_ESPOLIO,
    "INDETERMINADO":                 Regime.INDETERMINADO,
}
OPCAO_POR_NOME = {
    "VALOR_HISTORICO": OpcaoArt23.VALOR_HISTORICO,
    "VALOR_MERCADO":   OpcaoArt23.VALOR_MERCADO,
    "NAO_APLICAVEL":   OpcaoArt23.NAO_APLICAVEL,
}


def regime_do_extraido(nome: Optional[str]) -> Regime:
    if not nome:
        return Regime.INDETERMINADO
    return REGIME_POR_NOME.get(nome.upper(), Regime.INDETERMINADO)


def opcao_do_extraido(nome: Optional[str]) -> OpcaoArt23:
    if not nome:
        return OpcaoArt23.NAO_APLICAVEL
    return OPCAO_POR_NOME.get(nome.upper(), OpcaoArt23.NAO_APLICAVEL)
