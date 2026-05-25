# -*- coding: utf-8 -*-
"""
exemplo_relatorio.py — Caso fictício de demonstração do OrgAudi-Espólio.

Monta um espólio sintético com quatro bens — um por regime — e roda o
pipeline completo:

  1. Motor de apuração
  2. Otimizador (cenários legais)
  3. Verificação de isenções (sem aplicar)
  4. Relatório textual consolidado
  5. Laudo .xlsx (4 abas)

NENHUM dado aqui é real. O objetivo é mostrar O QUE o sistema produz e
checar visualmente que cada regime se comporta como a lei manda.

Rodar (a partir da raiz do projeto):
    python data/exemplo_relatorio.py

Sistema OrgAudi · ORGATEC CONTABILIDADE E AUDITORIA
"""
from __future__ import annotations
import os
import sys
from datetime import date

# adiciona src/ ao path (mesmo padrão de tests/test_motor.py)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from orgaudi_espolio import (                                          # noqa: E402
    Bem, Espolio, Herdeiro,
    Regime, OpcaoArt23,
    MotorApuracao, Otimizador,
    verificar_isencoes,
    gerar_relatorio_texto, gerar_laudo_xlsx,
)


def montar_espolio_exemplo() -> Espolio:
    """
    Espólio fictício com quatro bens, um por regime — escolhidos para
    exercitar todos os ramos do motor:

      1. Lote A: transmissão a herdeiro, opção §2º (histórico → diferimento)
      2. Lote B: venda pelo espólio, imóvel adquirido em 1985
                 (toca Lei 7.713/88 + FR1 §2º + FR2)
      3. Cotas BRADIV: cessão de direitos, NÃO-imóvel (sem FR)
      4. Veículo X: fora do monte (vendido em vida)
    """
    e = Espolio(
        nome="Espólio Adilson Exemplo",
        cpf_falecido="000.000.000-00",
        data_obito=date(2023, 9, 27),
        data_partilha=date(2025, 7, 16),
    )

    # quatro sucessores: três filhos (25%) + cônjuge meeira (25%).
    e.adicionar_herdeiro(Herdeiro("Filho 1",   "111.111.111-11", 0.25))
    e.adicionar_herdeiro(Herdeiro("Filho 2",   "222.222.222-22", 0.25))
    e.adicionar_herdeiro(Herdeiro("Filho 3",   "333.333.333-33", 0.25))
    e.adicionar_herdeiro(Herdeiro("Cônjuge",   "444.444.444-44", 0.25,
                                  eh_meeiro=True))

    # --- Bem 1: TRANSMISSAO_HERDEIRO, §2º (valor histórico, diferido) ---
    e.adicionar_bem(Bem(
        identificacao="Lote A — Casa residencial",
        matricula="12345",
        municipio="Goiânia/GO",
        custo_aquisicao_dirpf=12_500.00,
        data_aquisicao=date(2003, 7, 24),
        valor_partilha=130_000.00,
        eh_imovel=True,
        regime=Regime.TRANSMISSAO_HERDEIRO,
        opcao=OpcaoArt23.VALOR_HISTORICO,
        fonte_custo="DIRPF/2022 do falecido",
        fonte_valores="Escritura de partilha (2025)",
    ))

    # --- Bem 2: VENDA_PELO_ESPOLIO, imóvel adquirido em 1985 -----------
    # toca os três fatores: redução Lei 7.713/88, FR1 desde 01/1996, FR2.
    e.adicionar_bem(Bem(
        identificacao="Lote B — Imóvel rural (chácara)",
        matricula="67890",
        municipio="Hidrolândia/GO",
        custo_aquisicao_dirpf=42_000.00,
        data_aquisicao=date(1985, 3, 10),
        valor_venda=1_536_000.00,
        data_operacao=date(2024, 8, 14),
        eh_imovel=True,
        regime=Regime.VENDA_PELO_ESPOLIO,
        fonte_custo="DIRPF/2022 do falecido",
        fonte_valores="Contrato de compra e venda (08/2024)",
    ))

    # --- Bem 3: CESSAO_DIREITOS_HEREDITARIOS, NÃO-imóvel ---------------
    # cotas societárias — explicitamente fora do escopo de FR1/FR2.
    e.adicionar_bem(Bem(
        identificacao="Cotas BRADIV LTDA (15%)",
        custo_aquisicao_dirpf=1_050_000.00,
        data_aquisicao=date(2018, 6, 5),
        valor_venda=2_400_000.00,
        data_operacao=date(2024, 11, 20),
        eh_imovel=False,
        regime=Regime.CESSAO_DIREITOS_HEREDITARIOS,
        fonte_custo="DIRPF/2022 + alteração contratual 2018",
        fonte_valores="Instrumento de cessão (11/2024)",
        observacao=("Bem móvel — sem direito a FR1/FR2 nem à redução "
                    "Lei 7.713/88. Tributação cheia."),
    ))

    # --- Bem 4: FORA_DO_ESPOLIO -----------------------------------------
    e.adicionar_bem(Bem(
        identificacao="Veículo X (vendido em vida em 2021)",
        regime=Regime.FORA_DO_ESPOLIO,
        observacao="Bem não pertencia ao de cujus na data do óbito.",
    ))

    return e


def main() -> int:
    espolio = montar_espolio_exemplo()

    # 1) apuração ----------------------------------------------------------
    resumo = MotorApuracao(espolio).apurar()

    # 2) otimização --------------------------------------------------------
    recomendacoes = Otimizador(espolio).otimizar()

    # 3) verificação de isenções (sem aplicar) -----------------------------
    print("=" * 74)
    print("VERIFICAÇÃO DE ISENÇÕES (apenas elegibilidade — não aplica)")
    print("=" * 74)
    for b in espolio.bens:
        verifs = verificar_isencoes(b)
        if not verifs:
            continue
        print(f"\n  {b.identificacao}:")
        for v in verifs:
            sit = "elegível em tese" if v.elegivel_em_tese else "NÃO elegível"
            print(f"    • {v.isencao}  ({v.base_legal})  → {sit}")
            if v.observacao:
                print(f"      {v.observacao}")
            for req in v.requisitos_a_confirmar:
                print(f"        ☐ confirmar: {req}")

    # 4) relatório textual -------------------------------------------------
    print()
    print(gerar_relatorio_texto(espolio))

    # 5) laudo Excel -------------------------------------------------------
    caminho_xlsx = os.path.join(os.path.dirname(__file__),
                                "laudo_exemplo.xlsx")
    gerar_laudo_xlsx(espolio, caminho_xlsx)
    print(f"\nLaudo Excel gerado: {caminho_xlsx}")
    print(f"  (apuração {'CONCLUSIVA' if resumo['conclusivo'] else 'COM PENDÊNCIAS'})")
    print(f"  IR total do espólio: R$ {resumo['ir_espolio_total']:,.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
