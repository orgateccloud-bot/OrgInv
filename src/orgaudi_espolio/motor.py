# -*- coding: utf-8 -*-
"""
motor.py — Motor de apuração de IR sobre ganho de capital em espólio.

Recebe bens JÁ classificados (regime definido) e aplica a fórmula
correta de cada regime. Onde falta dado, marca pendência e NÃO conclui
— jamais assume zero para uma lacuna.

Sistema OrgAudi · ORGATEC CONTABILIDADE E AUDITORIA
"""

from __future__ import annotations
from .dominio import (Bem, Espolio, Regime, OpcaoArt23, StatusApuracao,
                      AVISO_IMOVEL_RURAL)
from .tributario import ir_ganho_capital, alerta_fatores_reducao
from .fatores_reducao import calcular_fatores_reducao


class MotorApuracao:
    """Aplica as regras tributárias sobre um Espolio."""

    def __init__(self, espolio: Espolio):
        self.e = espolio
        # Fração acumulada de meação baseada em herdeiros marcados como meeiro
        self.fracao_meacao = sum(h.fracao_monte for h in espolio.herdeiros if h.eh_meeiro)
        self.fracao_meacao = min(max(self.fracao_meacao, 0.0), 1.0)
        self.fracao_heranca = 1.0 - self.fracao_meacao

    # ---- validação de pré-condições ------------------------------------

    def _pendencias(self, b: Bem) -> list[str]:
        p: list[str] = []

        if b.regime == Regime.INDETERMINADO:
            p.append("Regime não classificado. Rodar o classificador "
                     "e definir o regime antes de apurar.")

        # custo é exigido em todo regime que calcula ganho
        precisa_custo = b.regime in (
            Regime.TRANSMISSAO_HERDEIRO,
            Regime.VENDA_PELO_ESPOLIO,
            Regime.CESSAO_DIREITOS_HEREDITARIOS)
        if precisa_custo and b.custo_aquisicao_dirpf is None:
            p.append("Custo de aquisição ausente. Obter da última DIRPF "
                     "do falecido. NÃO assumir zero — zero é um valor, "
                     "não uma lacuna.")

        if b.regime == Regime.TRANSMISSAO_HERDEIRO:
            if b.valor_partilha is None:
                p.append("Valor de partilha ausente.")
            if b.opcao == OpcaoArt23.NAO_APLICAVEL:
                p.append("Opção do Art. 23 não definida (histórico/mercado).")

        if b.regime in (Regime.VENDA_PELO_ESPOLIO,
                        Regime.CESSAO_DIREITOS_HEREDITARIOS):
            if b.valor_venda is None:
                p.append("Valor de venda ausente.")
            if b.data_operacao is None:
                p.append("Data da operação ausente.")

        # B-2: imóvel rural — regras de custo distintas (Lei 9.393/96)
        if b.eh_imovel_rural:
            p.append(AVISO_IMOVEL_RURAL)

        return p

    # ---- apuração de um bem --------------------------------------------

    def apurar_bem(self, b: Bem) -> None:
        b.pendencias = self._pendencias(b)

        # Alerta informativo sobre fatores de redução — somente para alienações
        # de imóveis (FR1/FR2 não se aplicam a TRANSMISSAO_HERDEIRO nem a bens
        # não-imóveis como cotas societárias — Lei 11.196/05 Art. 40).
        # C-4: evita ruído em TRANSMISSAO_HERDEIRO §2º onde não há ganho apurado
        # no espólio e os fatores só serão relevantes na venda futura pelo herdeiro.
        _eh_alienacao_imovel = (
            b.regime in (Regime.VENDA_PELO_ESPOLIO,
                         Regime.CESSAO_DIREITOS_HEREDITARIOS)
            and b.eh_imovel
        )
        alerta = alerta_fatores_reducao(b.data_aquisicao) if _eh_alienacao_imovel else None

        if b.pendencias:
            b.resultado = {"status": StatusApuracao.PENDENTE,
                           "ir_espolio": None,
                           "ir_meeiro": None,
                           "alerta_reducao": alerta}
            return

        c = b.custo_aquisicao_dirpf

        # M-2: fração de meação por-bem.
        # Se o bem for particular (adquirido antes do casamento, por herança
        # individual etc. — CC/2002 arts. 1.659, 1.661, 1.668), meação é zero
        # DESTE BEM, mesmo que o esposa seja meeira no monte partilhável geral.
        if b.eh_bem_particular:
            fm = 0.0   # meeiro não tem quinhaó sobre bem particular
            fh = 1.0
            _nota_particular = " [BEM PARTICULAR: meação zero neste bem — CC art. 1.659/1.668]"
        else:
            fm = self.fracao_meacao
            fh = self.fracao_heranca
            _nota_particular = ""

        if b.regime == Regime.TRANSMISSAO_HERDEIRO:
            # M-2: Proporções por-bem (fh/fm já respeitam eh_bem_particular)
            c_heranca = c * fh
            c_meacao = c * fm
            partilha_heranca = b.valor_partilha * fh if b.valor_partilha is not None else 0.0
            partilha_meacao = b.valor_partilha * fm if b.valor_partilha is not None else 0.0

            if b.opcao == OpcaoArt23.VALOR_HISTORICO:
                b.resultado = {
                    "status": StatusApuracao.OK,
                    "regime": b.regime.value,
                    "ganho_diferido": round(partilha_heranca - c_heranca, 2),
                    "ir_espolio": 0.0,
                    "ir_meeiro": 0.0,
                    "base_custo_herdeiro": round(c_heranca, 2),
                    "base_custo_meeiro": round(c_meacao, 2),
                    "alerta_reducao": alerta,
                    "nota": (
                        "Art. 23 §2º — Sem IR no espólio. Os herdeiros "
                        "recebem o quinhaó de herança pelo valor histórico "
                        "(R$ %.2f). A meação do cônjuge sobrevivente (R$ %.2f) "
                        "não é transmitida e mantém o custo proporcional histórico.%s" %
                        (c_heranca, c_meacao, _nota_particular)
                    ),
                }
            else:  # VALOR_MERCADO
                ganho = max(partilha_heranca - c_heranca, 0.0)
                ir = ir_ganho_capital(ganho)
                b.resultado = {
                    "status": StatusApuracao.OK,
                    "regime": b.regime.value,
                    "ganho_apurado": round(ganho, 2),
                    "ir_espolio": ir,
                    "ir_meeiro": 0.0,  # Não há incidência na meação, pois não é transmissão
                    "base_custo_herdeiro": round(partilha_heranca, 2),
                    "base_custo_meeiro": round(c_meacao, 2),
                    "alerta_reducao": alerta,
                    "nota": (
                        "Art. 23 §1º — IR R$ %.2f no espólio sobre a herança transmitida (base R$ %.2f). "
                        "A meação do meeiro sobrevivente (R$ %.2f) não é tributada na partilha e "
                        "conserva o custo de aquisição histórico original (R$ %.2f).%s" %
                        (ir, partilha_heranca, partilha_meacao, c_meacao, _nota_particular)
                    ),
                }

        elif b.regime == Regime.VENDA_PELO_ESPOLIO:
            ganho_bruto_total = max(b.valor_venda - c, 0.0)
            # aplica fatores de redução legais (FR1/FR2 + Lei 7.713/88)
            fr = calcular_fatores_reducao(
                ganho_bruto_total, b.data_aquisicao, b.data_operacao,
                eh_imovel=b.eh_imovel)
            base_tributavel_total = (fr.base_calculo_final if fr.aplicavel
                               else ganho_bruto_total)

            # M-2: segrega usando frações por-bem (fh/fm, não globais)
            base_espolio = base_tributavel_total * fh
            base_meeiro = base_tributavel_total * fm

            ir_espolio = ir_ganho_capital(base_espolio)
            ir_meeiro = ir_ganho_capital(base_meeiro)

            b.resultado = {
                "status": StatusApuracao.OK,
                "regime": b.regime.value,
                "ganho_bruto": round(ganho_bruto_total, 2),
                "base_tributavel": round(base_espolio, 2),
                "base_tributavel_meeiro": round(base_meeiro, 2),
                "fatores_reducao": fr,
                "ir_espolio": ir_espolio,
                "ir_meeiro": ir_meeiro,
                "base_custo_herdeiro": None,
                "alerta_reducao": alerta,
                "nota": (
                    "Venda pelo espólio. Base total de ganho R$ %.2f. "
                    "Espólio (Fração Herança %.1f%%): base R$ %.2f → IR R$ %.2f. "
                    "Meeiro (Fração Meação %.1f%%): base R$ %.2f → IR R$ %.2f "
                    "(a recolher no CPF do meeiro).%s" %
                    (base_tributavel_total, fh * 100, base_espolio, ir_espolio,
                     fm * 100, base_meeiro, ir_meeiro, _nota_particular)
                ),
            }

        elif b.regime == Regime.CESSAO_DIREITOS_HEREDITARIOS:
            ganho_bruto_total = max(b.valor_venda - c, 0.0)
            fr = calcular_fatores_reducao(
                ganho_bruto_total, b.data_aquisicao, b.data_operacao,
                eh_imovel=b.eh_imovel)
            base_tributavel_total = (fr.base_calculo_final if fr.aplicavel
                               else ganho_bruto_total)
            por_herdeiro = {}
            ir_meeiro_total = 0.0
            
            for h in self.e.herdeiros:
                # M-2: bem particular → meeiro não tem quinhaó neste bem;
                # sua fração é redistribuída proporcionalmente entre herdeiros
                if b.eh_bem_particular and h.eh_meeiro:
                    continue   # pula: meeiro não cede direitos num bem particular
                base_h = base_tributavel_total * h.fracao_monte
                ir_h = ir_ganho_capital(base_h)
                if h.eh_meeiro:
                    ir_meeiro_total += ir_h
                
                por_herdeiro[h.nome] = {
                    "fracao": h.fracao_monte,
                    "ganho": round(ganho_bruto_total * h.fracao_monte, 2),
                    "base_tributavel": round(base_h, 2),
                    "ir": ir_h,
                    "eh_meeiro": h.eh_meeiro
                }
                
            b.resultado = {
                "status": StatusApuracao.OK,
                "regime": b.regime.value,
                "ganho_bruto": round(ganho_bruto_total, 2),
                "base_tributavel": round(base_tributavel_total * fh, 2),
                "base_tributavel_meeiro": round(base_tributavel_total * fm, 2),
                "fatores_reducao": fr,
                "ir_espolio": 0.0,  # IR é rateado nas PFs dos cedentes
                "ir_meeiro": ir_meeiro_total,
                "ir_herdeiros": por_herdeiro,
                "alerta_reducao": alerta,
                "nota": ("Cessão de direitos. Base total tributável R$ %.2f rateada entre herdeiros/meeiro "
                         "de acordo com quinhão. IR devido pelos herdeiros e meeiro nas respectivas declarações PF.%s" %
                         (base_tributavel_total, _nota_particular)),
            }

        elif b.regime == Regime.FORA_DO_ESPOLIO:
            b.resultado = {
                "status": StatusApuracao.OK,
                "regime": b.regime.value,
                "ir_espolio": 0.0,
                "ir_meeiro": 0.0,
                "nota": "Fora do monte partilhável. Não entra na apuração.",
            }

    # ---- correção de progressividade — cessão com múltiplos bens ----------

    def _recalcular_cessao_agregado(self) -> None:
        """
        Correção C-2: progressividade para cessão de direitos hereditários
        com múltiplos bens.

        O art. 21 da Lei 8.981/95 c/c Lei 13.259/16 aplica as alíquotas
        progressivas sobre o GANHO TOTAL do cedente no período, não por
        operação. Quando há mais de um bem em CESSAO_DIREITOS_HEREDITARIOS
        conclusivo, o IR de cada herdeiro deve ser recalculado sobre a soma
        das bases de todos os bens — e redistribuído proporcionalmente.

        Exemplo de distorção sem este ajuste (faixas 15% e 17,5%):
          Herdeiro com base R$ 4 M em bem-1 e R$ 4 M em bem-2
          Sem agregar: 4M×15% + 4M×15% = R$ 1.200.000
          Com agregar: (4+4)M = 8M → 5M×15% + 3M×17,5% = R$ 1.275.000
          Subestimação: R$ 75.000 (IR incorretamente baixo).
        """
        cessao_ok = [
            b for b in self.e.bens
            if (b.regime == Regime.CESSAO_DIREITOS_HEREDITARIOS
                and b.resultado.get("status") == StatusApuracao.OK
                and b.resultado.get("ir_herdeiros"))
        ]
        if len(cessao_ok) <= 1:
            return  # um só bem: progressividade por bem já é exata

        # 1. Acumula base tributável por herdeiro em todos os bens de cessão
        base_total_por_h: dict[str, float] = {}
        for b in cessao_ok:
            for h_nome, h_data in b.resultado["ir_herdeiros"].items():
                base_total_por_h[h_nome] = (
                    base_total_por_h.get(h_nome, 0.0)
                    + h_data["base_tributavel"]
                )

        # 2. IR progressivo correto sobre a base agregada de cada cedente
        ir_total_por_h = {
            nome: ir_ganho_capital(base)
            for nome, base in base_total_por_h.items()
        }

        # 3. Distribui o IR total proporcionalmente a cada bem (fração da base)
        for b in cessao_ok:
            novo_ir_meeiro = 0.0
            for h_nome, h_data in b.resultado["ir_herdeiros"].items():
                base_h = h_data["base_tributavel"]
                base_total_h = base_total_por_h.get(h_nome, 0.0)
                ir_total_h = ir_total_por_h.get(h_nome, 0.0)
                ir_h_corrigido = (
                    round(ir_total_h * (base_h / base_total_h), 2)
                    if base_total_h > 0 else 0.0
                )
                b.resultado["ir_herdeiros"][h_nome] = {
                    **h_data,
                    "ir": ir_h_corrigido,
                }
                herdeiro = next(
                    (h for h in self.e.herdeiros if h.nome == h_nome), None)
                if herdeiro and herdeiro.eh_meeiro:
                    novo_ir_meeiro += ir_h_corrigido
            b.resultado["ir_meeiro"] = round(novo_ir_meeiro, 2)

    # ---- apuração de todo o espólio ------------------------------------

    def apurar(self) -> dict:
        for b in self.e.bens:
            self.apurar_bem(b)

        # C-2: recalcula progressividade agregada para cessões com múltiplos bens
        self._recalcular_cessao_agregado()

        ok = [b for b in self.e.bens
              if b.resultado.get("status") == StatusApuracao.OK]
        pend = [b for b in self.e.bens
                if b.resultado.get("status") == StatusApuracao.PENDENTE]

        ir_total = sum((b.resultado.get("ir_espolio") or 0.0) for b in ok)
        ir_meeiro_total = sum((b.resultado.get("ir_meeiro") or 0.0) for b in ok)

        return {
            "espolio": self.e.nome,
            "ir_espolio_total": round(ir_total, 2),
            "ir_meeiro_total": round(ir_meeiro_total, 2),
            "bens_conclusivos": len(ok),
            "bens_pendentes": len(pend),
            "conclusivo": len(pend) == 0,
            "soma_fracoes_herdeiros": self.e.soma_fracoes(),
        }
