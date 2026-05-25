# -*- coding: utf-8 -*-
"""
otimizador.py — Otimização tributária LÍCITA da apuração de espólio.

PRINCÍPIO INEGOCIÁVEL
---------------------
O otimizador escolhe entre opções QUE A LEI ABRE. Ele nunca altera o
regime de um bem — regime é fato consumado (quem alienou, quando, a que
título), não variável de decisão. Otimizar = dentro do regime correto,
encontrar a opção legal de menor imposto.

  - Regime TRANSMISSAO_HERDEIRO  -> há escolha real: §2º vs §1º do Art.23.
                                    O otimizador compara e recomenda.
  - Regime VENDA_PELO_ESPOLIO    -> NÃO há opção de diferimento. O único
                                    espaço lícito de redução são os
                                    fatores de redução e isenções legais.
  - Regime CESSAO_DIREITOS       -> idem: sem diferimento; só redução/isenção.
  - Regime FORA_DO_ESPOLIO       -> nada a otimizar.

Se um bem está em regime que não oferece escolha, o otimizador diz
exatamente isso — não fabrica uma economia inexistente.

Sistema OrgAudi · ORGATEC CONTABILIDADE E AUDITORIA
"""

from __future__ import annotations
from dataclasses import dataclass
from .dominio import Bem, Espolio, Regime, OpcaoArt23
from .tributario import ir_ganho_capital, alerta_fatores_reducao


@dataclass
class CenarioBem:
    """Um cenário possível de apuração para um bem, com seu IR."""
    descricao: str
    base_legal: str
    ir_espolio: float
    ir_herdeiros_futuro_estimado: float  # ganho diferido que o herdeiro herda
    observacao: str = ""


@dataclass
class RecomendacaoBem:
    bem: Bem
    cenarios: list[CenarioBem]
    recomendado: CenarioBem
    economia_vs_pior: float
    nota_decisao: str


class Otimizador:
    """Gera cenários lícitos por bem e recomenda o de menor impacto."""

    def __init__(self, espolio: Espolio):
        self.e = espolio

    def _cenarios_transmissao(self, b: Bem) -> list[CenarioBem]:
        """
        Para bem transmitido ao herdeiro, a lei abre DUAS opções reais.
        Importante: a comparação não é só do IR do espólio. Optar pelo
        §2º zera o IR hoje mas TRANSFERE o ganho ao herdeiro. Uma
        otimização honesta mostra os dois lados.
        """
        if b.custo_aquisicao_dirpf is None or b.valor_partilha is None:
            return []  # sem dados não há cenário — pendência tratada no motor

        c = b.custo_aquisicao_dirpf
        vp = b.valor_partilha
        ganho = max(vp - c, 0.0)

        # Opção §2º — valor histórico: IR zero agora, ganho vai ao herdeiro
        cen_hist = CenarioBem(
            descricao="Art. 23 §2º — valor histórico",
            base_legal="Lei 9.532/97, Art. 23, §2º",
            ir_espolio=0.0,
            ir_herdeiros_futuro_estimado=ir_ganho_capital(ganho),
            observacao=("IR zero no espólio agora. O herdeiro recebe pela "
                        "base histórica (R$ %.2f) e assume o ganho "
                        "diferido de R$ %.2f, tributável só na venda "
                        "futura — e possivelmente com fatores de redução "
                        "maiores por mais tempo de posse." % (c, ganho)),
        )

        # Opção §1º — valor de mercado: IR agora, herdeiro recebe base limpa
        ir_agora = ir_ganho_capital(ganho)
        cen_merc = CenarioBem(
            descricao="Art. 23 §1º — valor de mercado",
            base_legal="Lei 9.532/97, Art. 23, §1º",
            ir_espolio=ir_agora,
            ir_herdeiros_futuro_estimado=0.0,
            observacao=("IR de R$ %.2f recolhido pelo espólio agora. O "
                        "herdeiro recebe pela base atualizada (R$ %.2f); "
                        "futura venda só tributa valorização posterior."
                        % (ir_agora, vp)),
        )
        return [cen_hist, cen_merc]

    def _cenarios_venda(self, b: Bem) -> list[CenarioBem]:
        """
        Venda pelo espólio ou cessão: NÃO há diferimento. O único espaço
        lícito é fator de redução / isenção. O otimizador calcula o IR
        cheio e sinaliza reduções a verificar — não as aplica sozinho
        (FR1/FR2 exigem a fórmula mensal validada).
        """
        if b.custo_aquisicao_dirpf is None or b.valor_venda is None:
            return []

        ganho = max(b.valor_venda - b.custo_aquisicao_dirpf, 0.0)
        ir_cheio = ir_ganho_capital(ganho)

        cen = CenarioBem(
            descricao="Apuração sem reduções (piso de IR a confirmar)",
            base_legal="Lei 8.981/95 Art. 21; Lei 13.259/16",
            ir_espolio=ir_cheio,
            ir_herdeiros_futuro_estimado=0.0,
            observacao="Venda a terceiro — sem diferimento possível.",
        )
        cenarios = [cen]

        # sinaliza espaço lícito de redução (sem aplicar automaticamente)
        alerta = alerta_fatores_reducao(b.data_aquisicao)
        if alerta:
            cen.observacao += " " + alerta + (
                " Se aplicável, o fator reduz o ganho tributável — "
                "calcular no GCAP oficial.")
        if b.valor_venda is not None and b.valor_venda <= 440_000:
            cen.observacao += (" Verificar isenção de imóvel único até "
                               "R$ 440 mil (Lei 9.250/95 Art. 23).")
        return cenarios

    def otimizar_bem(self, b: Bem) -> RecomendacaoBem | None:
        if b.regime == Regime.TRANSMISSAO_HERDEIRO:
            cenarios = self._cenarios_transmissao(b)
        elif b.regime in (Regime.VENDA_PELO_ESPOLIO,
                          Regime.CESSAO_DIREITOS_HEREDITARIOS):
            cenarios = self._cenarios_venda(b)
        else:
            return None  # FORA_DO_ESPOLIO ou INDETERMINADO: nada a otimizar

        if not cenarios:
            return None  # sem dados — o motor trata como pendência

        # critério de recomendação: menor IR TOTAL (espólio + ganho que
        # recai sobre o herdeiro). Otimização honesta não empurra imposto
        # para o herdeiro fingindo que sumiu.
        def custo_total(c: CenarioBem) -> float:
            return c.ir_espolio + c.ir_herdeiros_futuro_estimado

        recomendado = min(cenarios, key=custo_total)
        pior = max(cenarios, key=custo_total)
        economia = round(custo_total(pior) - custo_total(recomendado), 2)

        if len(cenarios) == 1:
            nota = ("Regime sem opção de escolha — IR determinado pela "
                    "lei. Espaço lícito de redução limitado a fatores/"
                    "isenções, a confirmar.")
        elif economia == 0:
            nota = ("As opções resultam no mesmo IR total — a escolha "
                    "passa a ser de fluxo de caixa, não de economia.")
        else:
            nota = ("Recomendado o cenário de menor IR TOTAL "
                    "(espólio + ganho diferido ao herdeiro). A diferença "
                    "real é de fluxo de caixa e de quem paga, quando.")

        return RecomendacaoBem(bem=b, cenarios=cenarios,
                               recomendado=recomendado,
                               economia_vs_pior=economia,
                               nota_decisao=nota)

    def otimizar(self) -> list[RecomendacaoBem]:
        out = []
        for b in self.e.bens:
            r = self.otimizar_bem(b)
            if r is not None:
                out.append(r)
        return out
