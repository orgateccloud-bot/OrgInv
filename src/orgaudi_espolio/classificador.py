# -*- coding: utf-8 -*-
"""
classificador.py — Árvore de decisão que SUGERE o regime tributário de
um bem a partir dos fatos conhecidos.

Princípio: o classificador nunca "fecha" sozinho um regime ambíguo.
Quando os fatos não bastam, devolve INDETERMINADO com a pergunta exata
que precisa ser respondida por quem conhece o caso. É melhor uma
pendência explícita do que um regime errado silencioso.

Sistema OrgAudi · ORGATEC CONTABILIDADE E AUDITORIA
"""

from __future__ import annotations
from datetime import date
from .dominio import Bem, Regime


# vocabulário de fatos que o classificador precisa receber sobre o bem.
# Cada fato é uma resposta a uma pergunta objetiva.
class Fatos:
    """Fatos sobre uma operação. Campos None = 'ainda não sei'."""
    def __init__(self,
                 houve_alienacao: bool | None = None,
                 comprador_eh_terceiro: bool | None = None,
                 alienou_o_espolio: bool | None = None,
                 data_alienacao: date | None = None,
                 bem_pertencia_ao_de_cujus_no_obito: bool | None = None):
        self.houve_alienacao = houve_alienacao
        self.comprador_eh_terceiro = comprador_eh_terceiro
        self.alienou_o_espolio = alienou_o_espolio
        self.data_alienacao = data_alienacao
        self.bem_pertencia_ao_de_cujus_no_obito = \
            bem_pertencia_ao_de_cujus_no_obito


def classificar(bem: Bem, fatos: Fatos, data_partilha: date) -> tuple[Regime, list[str]]:
    """
    Devolve (regime_sugerido, lista_de_avisos).

    Se algum fato essencial for None, o regime volta INDETERMINADO e a
    lista de avisos contém a pergunta a responder.
    """
    avisos: list[str] = []

    # nó 0 — o bem sequer integra o monte?
    if fatos.bem_pertencia_ao_de_cujus_no_obito is False:
        return Regime.FORA_DO_ESPOLIO, [
            "Bem não pertencia ao de cujus na data do óbito (vendido em "
            "vida, adjudicado a terceiro, etc.). Não entra na apuração."]

    if fatos.bem_pertencia_ao_de_cujus_no_obito is None:
        return Regime.INDETERMINADO, [
            "FATO FALTANTE: o bem pertencia ao de cujus na data do óbito? "
            "(Se foi vendido em vida ou adjudicado a terceiro por sentença, "
            "está fora do monte.)"]

    # nó 1 — houve alienação a terceiro?
    if fatos.houve_alienacao is None:
        return Regime.INDETERMINADO, [
            "FATO FALTANTE: este bem foi alienado a terceiro, ou foi "
            "partilhado entre os herdeiros?"]

    # ramo A — não houve alienação: o bem foi partilhado ao herdeiro.
    if fatos.houve_alienacao is False:
        return Regime.TRANSMISSAO_HERDEIRO, [
            "Bem partilhado a herdeiro. Definir a opção do Art. 23 "
            "(valor histórico ou valor de mercado) — ver módulo motor."]

    # ramo B — houve alienação a terceiro: quem vendeu, e quando?
    if fatos.alienou_o_espolio is None:
        return Regime.INDETERMINADO, [
            "FATO FALTANTE: a alienação foi feita em nome do ESPÓLIO ou "
            "pelos HERDEIROS (cessão de direitos hereditários)? Conferir "
            "quem assina o contrato como vendedor e a que título."]

    if fatos.data_alienacao is None:
        avisos.append(
            "FATO FALTANTE: data da alienação não informada — necessária "
            "para confirmar se ocorreu antes ou depois da partilha.")

    # B.1 — vendeu o espólio
    if fatos.alienou_o_espolio is True:
        if (fatos.data_alienacao is not None
                and fatos.data_alienacao > data_partilha):
            avisos.append(
                f"INCONSISTÊNCIA: alienação em {fatos.data_alienacao} é "
                f"posterior à partilha ({data_partilha}). Se o bem já fora "
                f"partilhado, quem vendeu foi o herdeiro — reclassificar "
                f"como cessão/venda do herdeiro.")
        return Regime.VENDA_PELO_ESPOLIO, avisos

    # B.2 — venderam os herdeiros (cessão de direitos)
    avisos.append(
        "Cessão de direitos hereditários: o ganho é de cada herdeiro, na "
        "proporção do quinhão. O espólio não é o contribuinte.")
    return Regime.CESSAO_DIREITOS_HEREDITARIOS, avisos
