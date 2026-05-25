# -*- coding: utf-8 -*-
"""
fatores_reducao.py — Fatores de redução do ganho de capital.

Implementa:
  • FR1/FR2 — Lei 11.196/2005, Art. 40 (alienações a partir de 14/10/2005)
  • Redução por aquisição até 1988 — Lei 7.713/88, Art. 18

REGRA DE APLICAÇÃO (confirmada por pesquisa legislativa, mai/2026):
  FR1 = 1 / 1,0060^m1
    m1 = nº de meses entre a aquisição e novembro/2005.
    Para imóveis adquiridos ATÉ 31/12/1995, a contagem de m1 começa
    em janeiro/1996 (Lei 11.196/05, Art. 40 §2º).
  FR2 = 1 / 1,0035^m2
    m2 = nº de meses entre dezembro/2005 (ou o mês da aquisição, se
    posterior) e o mês da alienação.
  As reduções são aplicadas SUCESSIVAMENTE: primeiro a da Lei 7.713/88
  sobre o ganho, depois FR1, depois FR2 sobre o resultado anterior.

ESCOPO — IMPORTANTE:
  Estes fatores aplicam-se SOMENTE a BENS IMÓVEIS alienados por pessoa
  física (e por espólio, equiparado a PF). NÃO se aplicam a cotas
  societárias, veículos, ou outros bens móveis. O motor deve marcar
  cada bem com `eh_imovel` e só então invocar este módulo.

AVISO DE VALIDAÇÃO:
  O resultado deste módulo DEVE ser conferido contra o programa GCAP
  oficial da Receita Federal. Divergências de arredondamento entre esta
  implementação e o GCAP não são raras; em caso de conflito, prevalece
  o GCAP. Numa base de milhões, centavos de fator viram milhares de IR.

Base legal: Lei 11.196/2005 Art. 40; Lei 7.713/88 Art. 18;
IN SRF 599/2005; RIR/2020 (Decreto 9.580/2018) Art. 150.

Sistema OrgAudi · ORGATEC CONTABILIDADE E AUDITORIA
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import date


# ───────────────────────────────────────────────────────────────────────
# COEFICIENTES LEGAIS — confirmados por pesquisa (mai/2026).
# Centralizados aqui: qualquer alteração de norma se faz num só ponto.
# ───────────────────────────────────────────────────────────────────────

COEF_FR1 = 1.0060          # base do FR1 — Lei 11.196/05 Art. 40 I
COEF_FR2 = 1.0035          # base do FR2 — Lei 11.196/05 Art. 40 II
MES_REF_FR1 = (2005, 11)   # FR1 conta até novembro/2005
MES_INICIO_FR2 = (2005, 12)  # FR2 conta a partir de dezembro/2005
MES_INICIO_FR1_PRE96 = (1996, 1)  # imóvel adquirido até 1995: m1 desde 01/1996
DATA_VIGENCIA_FR = date(2005, 10, 14)  # fatores valem p/ alienação >= 14/10/2005


# Convenção de contagem de borda. A lei diz "meses-calendário OU FRAÇÃO".
# Na prática, há divergência entre fontes sobre incluir ou não o mês
# inicial. O GCAP oficial é a referência final. Este parâmetro deixa a
# premissa EXPLÍCITA e conferível, em vez de escondida no código.
#   "exclusiva"  -> conta só a diferença de meses (m = af*12+mf - ai*12-mi)
#   "inclusiva"  -> soma 1 (conta o mês inicial como mês cheio / fração)
CONVENCAO_CONTAGEM_MESES = "inclusiva"   # padrão; ajustar p/ casar c/ GCAP


def _meses_entre(ini: tuple[int, int], fim: tuple[int, int],
                 convencao: str = None) -> int:
    """
    Número de meses entre (ano,mês) inicial e final.
    A convenção de borda é parâmetro explícito — ver CONVENCAO_CONTAGEM_MESES.
    Nunca retorna negativo.
    """
    conv = convencao or CONVENCAO_CONTAGEM_MESES
    (ai, mi), (af, mf) = ini, fim
    n = (af - ai) * 12 + (mf - mi)
    if conv == "inclusiva" and n > 0:
        n += 1   # conta o mês inicial como fração de mês (Art. 40: "ou fração")
    return max(n, 0)


# ───────────────────────────────────────────────────────────────────────
# REDUÇÃO LEI 7.713/88 — imóveis adquiridos até 1988
# ───────────────────────────────────────────────────────────────────────

def percentual_reducao_7713(ano_aquisicao: int) -> float:
    """
    Percentual de redução do ganho para imóveis adquiridos até 1988.
    5% por ano, decrescente: 1988->5%, 1987->10%, ... 1969 ou antes->100%.
    Retorna fração [0,1]. Imóvel adquirido em 1989+ : 0.
    """
    if ano_aquisicao >= 1989:
        return 0.0
    if ano_aquisicao <= 1969:
        return 1.0
    return round((1989 - ano_aquisicao) * 0.05, 4)


# ───────────────────────────────────────────────────────────────────────
# FATORES FR1 / FR2 — Lei 11.196/2005
# ───────────────────────────────────────────────────────────────────────

@dataclass
class ResultadoFR:
    """Detalhamento auditável do cálculo de fatores de redução."""
    aplicavel: bool
    motivo_inaplicavel: str = ""
    m1: int = 0
    m2: int = 0
    fr1: float = 1.0
    fr2: float = 1.0
    reducao_7713: float = 0.0
    ganho_original: float = 0.0
    ganho_apos_7713: float = 0.0
    ganho_apos_fr1: float = 0.0
    base_calculo_final: float = 0.0
    memoria: list[str] = None

    def __post_init__(self):
        if self.memoria is None:
            self.memoria = []


def calcular_fatores_reducao(
        ganho: float,
        data_aquisicao: date | None,
        data_alienacao: date | None,
        eh_imovel: bool) -> ResultadoFR:
    """
    Aplica, sucessivamente e quando cabíveis, a redução da Lei 7.713/88
    e os fatores FR1/FR2 da Lei 11.196/05 sobre o ganho de capital.

    Devolve ResultadoFR com a memória de cálculo passo a passo, para
    conferência contra o GCAP oficial.
    """
    r = ResultadoFR(aplicavel=False, ganho_original=ganho)

    if not eh_imovel:
        r.motivo_inaplicavel = (
            "Bem não é imóvel. FR1/FR2 e redução da Lei 7.713/88 "
            "aplicam-se apenas a bens imóveis. Ex.: cotas societárias "
            "(BRADIV) NÃO têm direito a estes fatores.")
        r.base_calculo_final = ganho
        return r

    if data_aquisicao is None or data_alienacao is None:
        r.motivo_inaplicavel = (
            "Data de aquisição e/ou de alienação ausente — necessárias "
            "para contar os meses dos fatores. NÃO assumir.")
        r.base_calculo_final = ganho
        return r

    if data_alienacao < DATA_VIGENCIA_FR:
        r.motivo_inaplicavel = (
            f"Alienação em {data_alienacao} anterior a 14/10/2005 — "
            f"fatores FR1/FR2 não vigentes à época.")
        r.base_calculo_final = ganho
        return r

    if ganho <= 0:
        r.motivo_inaplicavel = "Ganho não-positivo — nada a reduzir."
        r.base_calculo_final = 0.0
        return r

    r.aplicavel = True
    ano_aq = data_aquisicao.year

    # --- passo 1: redução da Lei 7.713/88 (imóvel adquirido até 1988) ---
    r.reducao_7713 = percentual_reducao_7713(ano_aq)
    r.ganho_apos_7713 = round(ganho * (1.0 - r.reducao_7713), 2)
    if r.reducao_7713 > 0:
        r.memoria.append(
            f"Lei 7.713/88: imóvel adquirido em {ano_aq} → redução de "
            f"{r.reducao_7713*100:.0f}%. Ganho: R$ {ganho:,.2f} → "
            f"R$ {r.ganho_apos_7713:,.2f}")
    else:
        r.memoria.append(
            f"Lei 7.713/88: imóvel adquirido em {ano_aq} (após 1988) → "
            f"sem redução por esta regra.")

    # --- passo 2: FR1 ---------------------------------------------------
    # imóvel adquirido até 1995 → m1 conta desde 01/1996
    if ano_aq <= 1995:
        ini_m1 = MES_INICIO_FR1_PRE96
        nota_m1 = "(adquirido até 1995: contagem desde jan/1996, Art.40 §2º)"
    else:
        ini_m1 = (data_aquisicao.year, data_aquisicao.month)
        nota_m1 = ""
    # FR1 só conta se a aquisição é anterior a dez/2005
    if (data_aquisicao.year, data_aquisicao.month) < MES_INICIO_FR2:
        r.m1 = _meses_entre(ini_m1, MES_REF_FR1)
        r.fr1 = round(1.0 / (COEF_FR1 ** r.m1), 6)
        r.memoria.append(
            f"FR1: m1 = {r.m1} meses {nota_m1} → "
            f"FR1 = 1/{COEF_FR1}^{r.m1} = {r.fr1:.6f}")
    else:
        r.m1 = 0
        r.fr1 = 1.0
        r.memoria.append(
            "FR1: imóvel adquirido em dez/2005 ou depois → FR1 não se "
            "aplica (m1 = 0, fator = 1).")
    r.ganho_apos_fr1 = round(r.ganho_apos_7713 * r.fr1, 2)

    # --- passo 3: FR2 ---------------------------------------------------
    # m2: de dez/2005 (ou mês da aquisição, se posterior) até a alienação
    aq = (data_aquisicao.year, data_aquisicao.month)
    ini_m2 = aq if aq > MES_INICIO_FR2 else MES_INICIO_FR2
    fim_m2 = (data_alienacao.year, data_alienacao.month)
    r.m2 = _meses_entre(ini_m2, fim_m2)
    r.fr2 = round(1.0 / (COEF_FR2 ** r.m2), 6)
    r.memoria.append(
        f"FR2: m2 = {r.m2} meses → FR2 = 1/{COEF_FR2}^{r.m2} = {r.fr2:.6f}")

    r.base_calculo_final = round(r.ganho_apos_fr1 * r.fr2, 2)
    r.memoria.append(
        f"Base de cálculo final: R$ {r.ganho_apos_fr1:,.2f} × "
        f"{r.fr2:.6f} = R$ {r.base_calculo_final:,.2f}")
    r.memoria.append(
        f"Convenção de contagem de meses: '{CONVENCAO_CONTAGEM_MESES}'. "
        f"⚠ CONFERIR este resultado no GCAP oficial da RFB. Se o GCAP "
        f"contar os meses de forma diferente, ajustar "
        f"CONVENCAO_CONTAGEM_MESES até casar. Em caso de divergência, "
        f"prevalece o GCAP.")
    return r
