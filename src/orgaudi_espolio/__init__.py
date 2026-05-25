# -*- coding: utf-8 -*-
"""
orgaudi_espolio — Pacote de apuração de IR sobre ganho de capital em espólio.

Sistema OrgAudi · ORGATEC CONTABILIDADE E AUDITORIA
Autor técnico: Warley Veloso
Versão: 0.4.0

Importação canônica:

    from orgaudi_espolio import (Bem, Espolio, Herdeiro,
                                 Regime, OpcaoArt23, StatusApuracao,
                                 MotorApuracao, Otimizador,
                                 classificar, Fatos,
                                 ir_ganho_capital,
                                 calcular_fatores_reducao,
                                 verificar_isencoes,
                                 gerar_relatorio_texto,
                                 gerar_laudo_xlsx)
"""
from __future__ import annotations

__version__ = "0.4.0"

# --- domínio ---
from .dominio import (
    Bem,
    Espolio,
    Herdeiro,
    Regime,
    OpcaoArt23,
    StatusApuracao,
)

# --- cálculo puro ---
from .tributario import (
    ir_ganho_capital,
    FAIXAS_GANHO_CAPITAL,
    alerta_fatores_reducao,
)
from .fatores_reducao import (
    calcular_fatores_reducao,
    percentual_reducao_7713,
    ResultadoFR,
    CONVENCAO_CONTAGEM_MESES,
)

# --- decisão / aplicação ---
from .classificador import classificar, Fatos
from .motor import MotorApuracao
from .otimizador import Otimizador, CenarioBem, RecomendacaoBem

# --- validações ---
from .isencoes import verificar_isencoes, VerificacaoIsencao
from .reconciliador import (
    reconciliar,
    relatorio_conflitos,
    Conflito,
    QuadroReconciliacao,
)

# --- entrada ---
from .ingestao import (
    extrair_valores_pdf,
    resumo_extracao,
    ValorCandidato,
    ExtracaoDocumento,
)

# --- saída ---
from .relatorio import gerar_relatorio_texto
from .laudo_xlsx import gerar_laudo_xlsx
from .laudo_pdf import gerar_laudo_pdf
from .laudo_html import gerar_laudo_html, gerar_laudo_html_dark
from .laudo_docx import gerar_laudo_docx

# --- IA (Claude Sonnet) ---
from .ai_extrator import (
    extrair_de_pdfs,
    regime_do_extraido,
    opcao_do_extraido,
    EspolioExtraido,
    BemExtraido,
    HerdeiroExtraido,
)
from .ai_analista import analisar, analisar_stream

# --- tipos estruturados (B-1) ---
from .tipos import (
    ResultadoBem,
    ResultadoPendente,
    ResultadoTransmissaoHistorico,
    ResultadoTransmissaoMercado,
    ResultadoVenda,
    ResultadoCessao,
    ResultadoForaEspolio,
    HerdeiroRateio,
)

# --- logging estruturado (B-5) ---
from .logging_config import get_logger, configure_logging

__all__ = [
    "__version__",
    # domínio
    "Bem", "Espolio", "Herdeiro",
    "Regime", "OpcaoArt23", "StatusApuracao",
    # cálculo
    "ir_ganho_capital", "FAIXAS_GANHO_CAPITAL", "alerta_fatores_reducao",
    "calcular_fatores_reducao", "percentual_reducao_7713",
    "ResultadoFR", "CONVENCAO_CONTAGEM_MESES",
    # decisão / aplicação
    "classificar", "Fatos",
    "MotorApuracao",
    "Otimizador", "CenarioBem", "RecomendacaoBem",
    # validações
    "verificar_isencoes", "VerificacaoIsencao",
    "reconciliar", "relatorio_conflitos", "Conflito", "QuadroReconciliacao",
    # entrada
    "extrair_valores_pdf", "resumo_extracao",
    "ValorCandidato", "ExtracaoDocumento",
    # saída
    "gerar_relatorio_texto", "gerar_laudo_xlsx", "gerar_laudo_pdf",
    "gerar_laudo_html", "gerar_laudo_html_dark", "gerar_laudo_docx",
    # IA
    "extrair_de_pdfs", "regime_do_extraido", "opcao_do_extraido",
    "EspolioExtraido", "BemExtraido", "HerdeiroExtraido",
    "analisar", "analisar_stream",
    # tipos estruturados (B-1)
    "ResultadoBem",
    "ResultadoPendente", "ResultadoTransmissaoHistorico",
    "ResultadoTransmissaoMercado", "ResultadoVenda",
    "ResultadoCessao", "ResultadoForaEspolio", "HerdeiroRateio",
    # logging (B-5)
    "get_logger", "configure_logging",
]
