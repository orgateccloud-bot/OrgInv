# -*- coding: utf-8 -*-
"""
tributario.py — Tabelas legais e funções de cálculo de IR sobre ganho
de capital. Camada pura: recebe números, devolve números.

ATENÇÃO — este módulo concentra os parâmetros legais. Qualquer mudança
de legislação se faz AQUI, num único lugar, com a fonte documentada.
As alíquotas e fatores abaixo devem ser CONFERIDOS contra a legislação
vigente antes de cada uso em produção — não tratar como imutáveis.

Sistema OrgAudi · ORGATEC CONTABILIDADE E AUDITORIA
"""

from __future__ import annotations
from datetime import date


# ───────────────────────────────────────────────────────────────────────
# ALÍQUOTAS PROGRESSIVAS — GANHO DE CAPITAL
# Lei 8.981/1995 Art. 21 com redação da Lei 13.259/2016.
# Faixas em reais; cada faixa tributada à sua própria alíquota.
# CONFERIR vigência antes do uso.
# ───────────────────────────────────────────────────────────────────────

FAIXAS_GANHO_CAPITAL = [
    # (limite inferior, limite superior, alíquota)
    (0.0,          5_000_000.0,   0.150),
    (5_000_000.0,  10_000_000.0,  0.175),
    (10_000_000.0, 30_000_000.0,  0.200),
    (30_000_000.0, float("inf"),  0.225),
]


def ir_ganho_capital(ganho: float) -> float:
    """
    IR sobre ganho de capital pela tabela progressiva.
    Retorna 0.0 para ganho não-positivo. Resultado arredondado a 2 casas.
    """
    if ganho is None:
        raise ValueError("Ganho não pode ser None ao calcular IR.")
    if ganho <= 0:
        return 0.0
    imposto = 0.0
    for inf, sup, aliq in FAIXAS_GANHO_CAPITAL:
        if ganho > inf:
            base_faixa = min(ganho, sup) - inf
            imposto += base_faixa * aliq
    return round(imposto, 2)


# NOTA: o percentual de redução por aquisição até 1988 (Lei 7.713/88
# Art. 18) está implementado em `fatores_reducao.percentual_reducao_7713`,
# que também é onde se aplica FR1/FR2. Não duplicar aqui.


# ───────────────────────────────────────────────────────────────────────
# ALERTA SOBRE FATORES DE REDUÇÃO
# O cálculo efetivo de FR1/FR2 e da redução Lei 7.713/88 está em
# `fatores_reducao.py`. Este alerta é apenas um lembrete informativo
# para conferência no GCAP oficial — não substitui o cálculo.
# ───────────────────────────────────────────────────────────────────────


def alerta_fatores_reducao(bem_data_aquisicao: date | None) -> str | None:
    """
    Sinaliza, de forma informativa, que um imóvel está em faixa de
    aquisição com direito a algum fator de redução, lembrando que o
    GCAP oficial é a referência final. Retorna mensagem ou None.

    Faixas cobertas:
      • Aquisição até 1988 → redução da Lei 7.713/88 + FR1/FR2.
      • Aquisição entre 1989 e 1995 → FR1 conta desde jan/1996 (§2º) + FR2.
      • Aquisição entre 1996 e 2005 → FR1 + FR2.
      • Aquisição após 2005 → apenas FR2.
    """
    if bem_data_aquisicao is None:
        return None
    ano = bem_data_aquisicao.year
    if ano <= 1988:
        return (f"Imóvel adquirido em {ano}: redução da Lei 7.713/88 + "
                f"FR1/FR2 (Lei 11.196/05). Conferir no GCAP oficial.")
    if ano <= 1995:
        return (f"Imóvel adquirido em {ano}: FR1 conta desde jan/1996 "
                f"(Lei 11.196/05 Art. 40 §2º) + FR2. Conferir no GCAP.")
    if ano <= 2005:
        return (f"Imóvel adquirido em {ano}: FR1 e FR2 (Lei 11.196/05 "
                f"Art. 40). Conferir no GCAP oficial.")
    return (f"Imóvel adquirido em {ano}: FR2 (Lei 11.196/05 Art. 40 II). "
            f"Conferir no GCAP oficial.")


# ───────────────────────────────────────────────────────────────────────
# ISENÇÕES — registradas para verificação, não aplicadas automaticamente.
# ───────────────────────────────────────────────────────────────────────

ISENCOES_CONHECIDAS = {
    "imovel_unico_ate_440k": (
        "Imóvel único, valor de venda até R$ 440.000, sem outra alienação "
        "nos últimos 5 anos — Lei 9.250/95 Art. 23. Verificar elegibilidade."),
    "venda_residencial_reinvestida": (
        "Venda de imóvel residencial com reinvestimento em outro imóvel "
        "residencial em 180 dias — Lei 11.196/2005 Art. 39. Verificar."),
}
