# -*- coding: utf-8 -*-
"""
relatorio.py — Geração do relatório consolidado da apuração.

Estrutura do relatório, conforme o foco pedido:
  1. IR FINAL DO ESPÓLIO  — total a recolher, por bem.
  2. GCAP                 — campos do Ganho de Capital por bem, com a
                            opção recomendada e a justificativa legal.
  3. IR DOS HERDEIROS     — base de custo recebida por herdeiro e o
                            ganho diferido que cada um assume.
  4. COMPARATIVO          — cenário sem otimização vs. otimizado.

Sistema OrgAudi · ORGATEC CONTABILIDADE E AUDITORIA
"""

from __future__ import annotations
from .dominio import Espolio, Regime, OpcaoArt23, StatusApuracao
from .motor import MotorApuracao
from .otimizador import Otimizador


def _moeda(v) -> str:
    if v is None:
        return "— (pendente)"
    return f"R$ {v:,.2f}"


def gerar_relatorio_texto(espolio: Espolio) -> str:
    """Relatório textual completo. Roda motor + otimizador internamente."""
    motor = MotorApuracao(espolio)
    resumo = motor.apurar()
    recomendacoes = Otimizador(espolio).otimizar()
    rec_por_bem = {r.bem.identificacao: r for r in recomendacoes}

    L: list[str] = []
    add = L.append

    add("=" * 74)
    add(f"  RELATÓRIO DE APURAÇÃO — {espolio.nome}")
    add(f"  Óbito: {espolio.data_obito}  |  Partilha: {espolio.data_partilha}")
    add(f"  Sistema OrgAudi · ORGATEC CONTABILIDADE E AUDITORIA")
    add("=" * 74)

    # checagem de consistência das frações
    soma = espolio.soma_fracoes()
    if abs(soma - 1.0) > 0.001:
        add(f"\n⚠ ATENÇÃO: soma das frações dos herdeiros = {soma:.4f} "
            f"(esperado 1,0000). Conferir a partilha.")

    # ---- 1. IR FINAL DO ESPÓLIO --------------------------------------
    add("\n" + "─" * 74)
    add("1. IR FINAL DO ESPÓLIO")
    add("─" * 74)
    for b in espolio.bens:
        r = b.resultado
        add(f"\n  {b.identificacao}  (mat. {b.matricula})")
        add(f"    Regime: {b.regime.value}")
        if r.get("status") == StatusApuracao.PENDENTE:
            add(f"    STATUS: PENDENTE")
            for p in b.pendencias:
                add(f"      • {p}")
        else:
            add(f"    IR do espólio: {_moeda(r.get('ir_espolio'))}")
            if r.get("nota"):
                add(f"    {r['nota']}")
    add(f"\n  ▸ IR TOTAL DEVIDO PELO ESPÓLIO: "
        f"{_moeda(resumo['ir_espolio_total'])}")
    if not resumo["conclusivo"]:
        add(f"  ▸ {resumo['bens_pendentes']} bem(ns) pendente(s) — "
            f"valor NÃO é definitivo até resolução.")

    # ---- 2. GCAP ------------------------------------------------------
    add("\n" + "─" * 74)
    add("2. GCAP — GANHO DE CAPITAL POR BEM")
    add("─" * 74)
    for b in espolio.bens:
        add(f"\n  {b.identificacao}")
        add(f"    Custo de aquisição (DIRPF falecido): "
            f"{_moeda(b.custo_aquisicao_dirpf)}")
        add(f"    Valor de partilha/venda: "
            f"{_moeda(b.valor_partilha or b.valor_venda)}")
        rec = rec_por_bem.get(b.identificacao)
        if rec:
            add(f"    Opção recomendada: {rec.recomendado.descricao}")
            add(f"    Base legal: {rec.recomendado.base_legal}")
            add(f"    {rec.recomendado.observacao}")
        else:
            add(f"    (sem cenário de otimização — regime sem escolha "
                f"ou dados pendentes)")

    # ---- 3. IR DOS HERDEIROS -----------------------------------------
    add("\n" + "─" * 74)
    add("3. IR DOS HERDEIROS")
    add("─" * 74)
    add("  Base de custo que cada herdeiro recebe e ganho diferido "
        "assumido:")
    for b in espolio.bens:
        r = b.resultado
        if r.get("status") != StatusApuracao.OK:
            continue
        if b.regime == Regime.TRANSMISSAO_HERDEIRO:
            base = r.get("base_custo_herdeiro")
            dif = r.get("ganho_diferido", 0.0)
            add(f"\n  {b.identificacao}:")
            add(f"    Base de custo do herdeiro: {_moeda(base)}")
            if dif:
                add(f"    Ganho diferido (tributável na venda futura): "
                    f"{_moeda(dif)}")
            add(f"    IR dos herdeiros HOJE a título de herança: R$ 0,00 "
                f"(herança é rendimento isento — Lei 7.713/88 Art. 6º XVI)")
        elif b.regime == Regime.CESSAO_DIREITOS_HEREDITARIOS:
            add(f"\n  {b.identificacao} (cessão de direitos):")
            for nome, d in (r.get("ir_herdeiros") or {}).items():
                add(f"    {nome}: ganho {_moeda(d['ganho'])} → "
                    f"IR {_moeda(d['ir'])}")

    # ---- 4. COMPARATIVO ----------------------------------------------
    add("\n" + "─" * 74)
    add("4. COMPARATIVO — SEM OTIMIZAÇÃO vs. OTIMIZADO")
    add("─" * 74)
    total_pior = 0.0
    total_rec = 0.0
    for rec in recomendacoes:
        def ct(c):
            return c.ir_espolio + c.ir_herdeiros_futuro_estimado
        pior = max(rec.cenarios, key=ct)
        total_pior += ct(pior)
        total_rec += ct(rec.recomendado)
        add(f"\n  {rec.bem.identificacao}:")
        add(f"    Pior cenário legal:   {_moeda(ct(pior))}  "
            f"({pior.descricao})")
        add(f"    Cenário recomendado:  {_moeda(ct(rec.recomendado))}  "
            f"({rec.recomendado.descricao})")
        if rec.economia_vs_pior > 0:
            add(f"    Diferença: {_moeda(rec.economia_vs_pior)}")
        add(f"    {rec.nota_decisao}")
    add(f"\n  ▸ IR TOTAL (pior cenário legal):  {_moeda(total_pior)}")
    add(f"  ▸ IR TOTAL (cenário recomendado): {_moeda(total_rec)}")
    add(f"  ▸ Diferença total: {_moeda(round(total_pior - total_rec, 2))}")
    add("\n  Nota: a 'diferença' é, em boa parte, deslocamento de quem "
        "paga e quando — o §2º não elimina o ganho, transfere-o ao "
        "herdeiro. Não confundir diferimento com isenção.")

    add("\n" + "=" * 74)
    add("  AVISO: relatório de apoio. A classificação de regime de cada "
        "bem e os valores de custo devem ser validados pelo contador e "
        "advogado responsáveis antes de qualquer entrega à RFB.")
    add("=" * 74)
    return "\n".join(L)
