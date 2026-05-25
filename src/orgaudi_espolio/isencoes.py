# -*- coding: utf-8 -*-
"""
isencoes.py — Verificação de elegibilidade a isenções de ganho de capital.

PRINCÍPIO: este módulo VERIFICA e SINALIZA elegibilidade. Ele NÃO aplica
isenção automaticamente. Toda isenção depende de fatos que o software
não tem como confirmar sozinho (ex.: se o contribuinte fez outra venda
nos últimos 5 anos). Aplicar isenção indevida é causa comum de autuação.

A saída é sempre: "este bem PARECE elegível à isenção X; confirme os
requisitos A, B, C antes de aplicá-la".

Isenções cobertas:
  • Imóvel único de pequeno valor — Lei 9.250/95, Art. 23
  • Reinvestimento em imóvel residencial em 180 dias — Lei 11.196/05 Art.39
  • (herança em si é rendimento isento — Lei 7.713/88 Art. 6º XVI — mas
    isso é tratado no motor, não aqui: não é isenção de ganho de capital.)

Sistema OrgAudi · ORGATEC CONTABILIDADE E AUDITORIA
"""

from __future__ import annotations
from dataclasses import dataclass
from .dominio import Bem, Regime


@dataclass
class VerificacaoIsencao:
    isencao: str
    base_legal: str
    elegivel_em_tese: bool
    requisitos_a_confirmar: list[str]
    observacao: str = ""


# limite legal da isenção de imóvel único de pequeno valor.
# CONFERIR vigência — Lei 9.250/95 Art. 23.
LIMITE_IMOVEL_UNICO = 440_000.0


def verificar_imovel_unico(bem: Bem) -> VerificacaoIsencao | None:
    """
    Isenção do ganho na venda de imóvel por valor até R$ 440 mil, desde
    que seja o único imóvel e não tenha havido outra venda nos últimos
    5 anos.

    Regimes cobertos:
      • VENDA_PELO_ESPOLIO e CESSAO_DIREITOS_HEREDITARIOS — alienação
        onerosa, valor de referência = valor_venda.
      • TRANSMISSAO_HERDEIRO com VALOR_MERCADO (Art. 23 §1º) — há
        ganho apurado no espólio; valor de referência = valor_partilha.
        (No §2º histórico não há IR no espólio, isenção irrelevante aqui.)

    M-1 (correção): anteriormente apenas alienações a terceiro eram
    verificadas. A transmissão §1º também gera ganho e pode se beneficiar
    desta isenção, desde que os requisitos sejam cumpridos.
    """
    from .dominio import OpcaoArt23, Regime as R

    # Determina o valor de referência e se o regime tem ganho apurado
    if bem.regime in (R.VENDA_PELO_ESPOLIO, R.CESSAO_DIREITOS_HEREDITARIOS):
        valor = bem.valor_venda
        nota_regime = "alienação onerosa"
    elif (bem.regime == R.TRANSMISSAO_HERDEIRO
          and bem.opcao == OpcaoArt23.VALOR_MERCADO):
        valor = bem.valor_partilha
        nota_regime = "transmissão §1º (valor de mercado)"
    else:
        return None  # sem ganho apurado no espólio: isenção irrelevante

    if valor is None:
        return None

    if valor > LIMITE_IMOVEL_UNICO:
        return VerificacaoIsencao(
            isencao="Imóvel único de pequeno valor",
            base_legal="Lei 9.250/95, Art. 23",
            elegivel_em_tese=False,
            requisitos_a_confirmar=[],
            observacao=(
                f"Valor de referência (R$ {valor:,.2f}) acima do limite de "
                f"R$ {LIMITE_IMOVEL_UNICO:,.2f} — regime: {nota_regime}. "
                f"Não elegível."
            ),
        )
    return VerificacaoIsencao(
        isencao="Imóvel único de pequeno valor",
        base_legal="Lei 9.250/95, Art. 23",
        elegivel_em_tese=True,
        requisitos_a_confirmar=[
            "É o Único imóvel do alienante (espólio ou herdeiro)?",
            "Não houve outra alienação de imóvel nos últimos 5 anos?",
            "A isenção não foi usada por outro membro no mesmo período?",
        ],
        observacao=(
            f"Valor dentro do limite (regime: {nota_regime}). A isenção SÓ se "
            "confirma se todos os requisitos acima forem verdadeiros — "
            "verificar antes de aplicar."
        ),
    )


def verificar_reinvestimento_residencial(bem: Bem) -> VerificacaoIsencao | None:
    """
    Isenção do ganho na venda de imóvel residencial cujo produto seja
    aplicado na compra de outro imóvel residencial em 180 dias.
    O software não sabe se houve reinvestimento — só sinaliza a hipótese.
    """
    if bem.valor_venda is None or bem.regime not in (
            Regime.VENDA_PELO_ESPOLIO,
            Regime.CESSAO_DIREITOS_HEREDITARIOS):
        return None
    return VerificacaoIsencao(
        isencao="Reinvestimento em imóvel residencial",
        base_legal="Lei 11.196/2005, Art. 39",
        elegivel_em_tese=True,
        requisitos_a_confirmar=[
            "O imóvel vendido é RESIDENCIAL?",
            "O produto da venda foi/será aplicado na compra de outro "
            "imóvel residencial no País em até 180 dias?",
            "O benefício não foi usado nos últimos 5 anos?",
        ],
        observacao=("Hipótese a investigar. Aplica-se proporcionalmente "
                    "se só parte do produto for reinvestida. Não presumir."))


def verificar_isencoes(bem: Bem) -> list[VerificacaoIsencao]:
    """Roda todas as verificações de isenção aplicáveis a um bem."""
    out = []
    for fn in (verificar_imovel_unico, verificar_reinvestimento_residencial):
        v = fn(bem)
        if v is not None:
            out.append(v)
    return out
