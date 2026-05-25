# -*- coding: utf-8 -*-
"""
test_motor.py — Testes do motor de apuração.
Rodar: cd orgaudi-espolio && python -m pytest tests/ -v
       (ou: python tests/test_motor.py para execução direta)
"""
import sys, os
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from orgaudi_espolio import (Bem, Espolio, Herdeiro, Regime, OpcaoArt23,
                             StatusApuracao, MotorApuracao, classificar,
                             Fatos, ir_ganho_capital)


def _espolio_base():
    e = Espolio("Espólio Teste", "000.000.000-00",
                date(2023, 9, 27), date(2025, 7, 16))
    e.adicionar_herdeiro(Herdeiro("Herdeiro A", "1", 0.25))
    e.adicionar_herdeiro(Herdeiro("Herdeiro B", "2", 0.25))
    e.adicionar_herdeiro(Herdeiro("Herdeiro C", "3", 0.25))
    e.adicionar_herdeiro(Herdeiro("Meeiro", "4", 0.25, eh_meeiro=True))
    return e


def test_aliquota_progressiva():
    assert ir_ganho_capital(0) == 0.0
    assert ir_ganho_capital(-100) == 0.0
    assert ir_ganho_capital(1_000_000) == 150_000.0
    # ganho de 6 milhões: 5M a 15% + 1M a 17,5%
    assert ir_ganho_capital(6_000_000) == 750_000 + 175_000
    print("OK  alíquota progressiva")


def test_transmissao_historico_difere():
    e = _espolio_base()
    b = Bem("Lote X", custo_aquisicao_dirpf=12_500,
            valor_partilha=130_000, regime=Regime.TRANSMISSAO_HERDEIRO,
            opcao=OpcaoArt23.VALOR_HISTORICO)
    e.adicionar_bem(b)
    MotorApuracao(e).apurar()
    assert b.resultado["ir_espolio"] == 0.0
    # base do herdeiro = histórico, NÃO partilha
    assert b.resultado["base_custo_herdeiro"] == 9_375.0
    assert b.resultado["base_custo_meeiro"] == 3_125.0
    assert b.resultado["ganho_diferido"] == 88_125.0
    print("OK  transmissão §2º difere e base = histórico")


def test_transmissao_mercado_tributa():
    e = _espolio_base()
    b = Bem("Lote Y", custo_aquisicao_dirpf=12_500,
            valor_partilha=130_000, regime=Regime.TRANSMISSAO_HERDEIRO,
            opcao=OpcaoArt23.VALOR_MERCADO)
    e.adicionar_bem(b)
    MotorApuracao(e).apurar()
    assert b.resultado["ir_espolio"] == ir_ganho_capital(88_125.0)
    # base do herdeiro = partilha (atualizada)
    assert b.resultado["base_custo_herdeiro"] == 97_500.0
    assert b.resultado["base_custo_meeiro"] == 3_125.0
    print("OK  transmissão §1º tributa e base = partilha")


def test_venda_pelo_espolio_aplica_fr_e_tributa():
    e = _espolio_base()
    b = Bem("Lote Z", custo_aquisicao_dirpf=42_000, valor_venda=1_536_000,
            data_aquisicao=date(2003, 7, 24), eh_imovel=True,
            regime=Regime.VENDA_PELO_ESPOLIO, data_operacao=date(2025, 6, 26))
    e.adicionar_bem(b)
    MotorApuracao(e).apurar()
    r = b.resultado
    # ganho bruto = 1.494.000; com FR aplicado a base cai bem abaixo disso
    assert r["ganho_bruto"] == 1_494_000
    assert r["base_tributavel"] < r["ganho_bruto"]   # FR reduziu de fato
    assert r["ir_espolio"] > 0                       # mas ainda há IR
    print("OK  venda pelo espólio: FR reduz a base, IR continua > 0")


def test_cota_societaria_nao_tem_fr():
    """Cota societária (BRADIV) não é imóvel — sem direito a FR1/FR2."""
    e = Espolio("Espólio Teste", "000.000.000-00",
                date(2023, 9, 27), date(2025, 7, 16))
    e.adicionar_herdeiro(Herdeiro("Herdeiro A", "1", 1.0))
    b = Bem("Cotas BRADIV", custo_aquisicao_dirpf=1_050_000,
            valor_venda=4_000_000, data_aquisicao=date(2020, 6, 5),
            eh_imovel=False,   # <- cota, não imóvel
            regime=Regime.VENDA_PELO_ESPOLIO, data_operacao=date(2024, 9, 3))
    e.adicionar_bem(b)
    MotorApuracao(e).apurar()
    r = b.resultado
    # sem FR: base tributável = ganho bruto integral
    assert r["base_tributavel"] == r["ganho_bruto"]
    assert r["fatores_reducao"].aplicavel is False
    print("OK  cota societária não recebe FR1/FR2")


def test_pendencia_quando_falta_custo():
    e = _espolio_base()
    b = Bem("Lote sem custo", valor_partilha=130_000,
            regime=Regime.TRANSMISSAO_HERDEIRO,
            opcao=OpcaoArt23.VALOR_HISTORICO)  # custo = None
    e.adicionar_bem(b)
    res = MotorApuracao(e).apurar()
    assert b.resultado["status"] == StatusApuracao.PENDENTE
    assert b.resultado["ir_espolio"] is None  # não inventou zero
    assert res["conclusivo"] is False
    print("OK  custo ausente vira pendência, não zero")


def test_classificador_pede_fato_faltante():
    b = Bem("Lote ambíguo")
    regime, avisos = classificar(b, Fatos(), date(2025, 7, 16))
    assert regime == Regime.INDETERMINADO
    assert any("FATO FALTANTE" in a for a in avisos)
    print("OK  classificador devolve pendência quando faltam fatos")


def test_classificador_detecta_venda_pos_partilha():
    b = Bem("Lote vendido depois")
    f = Fatos(houve_alienacao=True, alienou_o_espolio=True,
              bem_pertencia_ao_de_cujus_no_obito=True,
              data_alienacao=date(2025, 8, 1))   # após partilha
    regime, avisos = classificar(b, f, date(2025, 7, 16))
    assert any("INCONSISTÊNCIA" in a for a in avisos)
    print("OK  classificador alerta venda posterior à partilha")


def test_segregacao_meacao():
    e = Espolio("Espólio com Meeiro", "000.000.000-00",
                date(2023, 9, 27), date(2025, 7, 16))
    e.adicionar_herdeiro(Herdeiro("Herdeiro A", "1", 0.5))
    e.adicionar_herdeiro(Herdeiro("Meeiro", "2", 0.5, eh_meeiro=True))
    
    b = Bem("Imóvel Comum", custo_aquisicao_dirpf=100_000, valor_venda=300_000,
            data_aquisicao=date(2010, 1, 1), eh_imovel=True,
            regime=Regime.VENDA_PELO_ESPOLIO, data_operacao=date(2024, 1, 1))
    e.adicionar_bem(b)
    
    MotorApuracao(e).apurar()
    r = b.resultado
    
    assert r["ganho_bruto"] == 200_000
    assert r["base_tributavel"] == r["base_tributavel_meeiro"]
    assert r["ir_espolio"] == ir_ganho_capital(r["base_tributavel"])
    assert r["ir_meeiro"] == ir_ganho_capital(r["base_tributavel_meeiro"])
    print("OK  segregação de meação aritmética")


def test_alerta_reducao_ausente_em_transmissao_historico():
    """C-4: TRANSMISSAO §2º não deve gerar alerta de FR1/FR2 no resultado."""
    e = _espolio_base()
    b = Bem(
        "Lote C4",
        custo_aquisicao_dirpf=10_000,
        valor_partilha=200_000,
        data_aquisicao=date(1985, 1, 1),  # elegível a FR se fosse alienação
        eh_imovel=True,
        regime=Regime.TRANSMISSAO_HERDEIRO,
        opcao=OpcaoArt23.VALOR_HISTORICO,
    )
    e.adicionar_bem(b)
    MotorApuracao(e).apurar()
    assert b.resultado["alerta_reducao"] is None, (
        "TRANSMISSAO §2º não deve gerar alerta de FR1/FR2 — "
        f"obtido: {b.resultado['alerta_reducao']!r}"
    )
    print("OK  alerta FR1/FR2 ausente em TRANSMISSAO §2º (C-4)")


def test_progressividade_cessao_multiplos_bens():
    """C-2: IR na cessão calculado sobre base agregada por herdeiro, não por bem.

    Cenário: cedente único com 100% em dois bens não-imóveis.
      Bem-1: custo 1M, venda 5M → ganho 4M
      Bem-2: custo 1M, venda 4M → ganho 3M
      Base total: 7M → faixa: 5M×15% + 2M×17,5% = 1.100.000
      Cálculo errado por-bem: 4M×15% + 3M×15% = 1.050.000
      Diferença subestimada sem C-2: R$ 50.000
    """
    e = Espolio("Espólio C2", "000.000.000-00",
                date(2023, 1, 1), date(2025, 1, 1))
    e.adicionar_herdeiro(Herdeiro("Cedente Único", "1", 1.0))

    b1 = Bem("Cessão Bem-1",
             custo_aquisicao_dirpf=1_000_000,
             valor_venda=5_000_000,
             eh_imovel=False,
             regime=Regime.CESSAO_DIREITOS_HEREDITARIOS,
             data_aquisicao=date(2020, 1, 1),
             data_operacao=date(2025, 3, 1))
    b2 = Bem("Cessão Bem-2",
             custo_aquisicao_dirpf=1_000_000,
             valor_venda=4_000_000,
             eh_imovel=False,
             regime=Regime.CESSAO_DIREITOS_HEREDITARIOS,
             data_aquisicao=date(2020, 1, 1),
             data_operacao=date(2025, 3, 1))

    e.adicionar_bem(b1)
    e.adicionar_bem(b2)
    MotorApuracao(e).apurar()

    ir1 = b1.resultado["ir_herdeiros"]["Cedente Único"]["ir"]
    ir2 = b2.resultado["ir_herdeiros"]["Cedente Único"]["ir"]
    ir_total = round(ir1 + ir2, 2)

    ir_esperado = ir_ganho_capital(7_000_000)            # 1.100.000
    ir_por_bem_isolado = (ir_ganho_capital(4_000_000)    # 600.000
                          + ir_ganho_capital(3_000_000)) # 450.000 → 1.050.000

    assert ir_esperado > ir_por_bem_isolado, "Pré-condição: agregado > por-bem"
    assert abs(ir_total - ir_esperado) < 1.0, (
        f"IR agregado esperado {ir_esperado:,.2f}, obtido {ir_total:,.2f} "
        f"(por-bem isolado seria {ir_por_bem_isolado:,.2f})"
    )
    print(f"OK  progressividade cessão agregada: IR={ir_total:,.2f} "
          f"(por-bem seria {ir_por_bem_isolado:,.2f}, corrigido em "
          f"R$ {ir_total - ir_por_bem_isolado:,.2f}) (C-2)")


def test_calculadora_reforma_custo_none_nao_assume_zero():
    """C-3: CalculadoraReforma não deve tratar custo None como zero."""
    from orgaudi_espolio.servicos import CalculadoraReforma

    e = Espolio("Espólio C3", "000.000.000-00",
                date(2023, 1, 1), date(2025, 1, 1))
    e.adicionar_herdeiro(Herdeiro("H1", "1", 1.0))
    b = Bem("Bem sem custo",
            custo_aquisicao_dirpf=None,   # ausente — lacuna, não zero
            valor_venda=500_000,
            regime=Regime.VENDA_PELO_ESPOLIO)
    e.adicionar_bem(b)

    resultado = CalculadoraReforma.calcular_cenario_reforma(e)
    bem_r = resultado["bens"][0]

    assert bem_r["ganho_total"] is None, (
        "ganho_total deve ser None quando custo é ausente — "
        f"obtido {bem_r['ganho_total']!r}"
    )
    assert "pendencia" in bem_r, "Deve incluir campo 'pendencia' sinalizando a lacuna"
    print("OK  CalculadoraReforma não assume custo zero quando None (C-3)")


def test_imovel_rural_dispara_pendencia():
    """B-2: bem com eh_imovel_rural=True deve receber aviso AVISO_IMOVEL_RURAL
    como pendência, impedindo apuração silenciosa pela regra de imóvel urbano."""
    from orgaudi_espolio.dominio import AVISO_IMOVEL_RURAL

    e = _espolio_base()
    b = Bem(
        "Chácara Rural B-2",
        custo_aquisicao_dirpf=80_000,
        valor_venda=500_000,
        eh_imovel=True,
        eh_imovel_rural=True,                   # flag rural
        regime=Regime.VENDA_PELO_ESPOLIO,
        data_aquisicao=date(2010, 1, 1),
        data_operacao=date(2025, 1, 1),
    )
    e.adicionar_bem(b)
    MotorApuracao(e).apurar()

    assert b.resultado["status"] == StatusApuracao.PENDENTE, (
        "Im\u00f3vel rural deve gerar pend\u00eancia at\u00e9 que rural.py seja implementado"
    )
    assert any(AVISO_IMOVEL_RURAL[:30] in p for p in b.pendencias), (
        f"AVISO_IMOVEL_RURAL ausente nas pend\u00eancias: {b.pendencias!r}"
    )
    print("OK  im\u00f3vel rural dispara pend\u00eancia expl\u00edcita (B-2)")


def test_audit_hash_distingue_none_de_zero():
    """B-4: hash com custo=None deve diferir do hash com custo=0.0.
    Antes da corre\u00e7\u00e3o, ambos geravam o mesmo hash (via `or 0.0`)."""
    from orgaudi_espolio.servicos import EspolioService

    e_none = _espolio_base()
    e_none.adicionar_bem(Bem(
        "Bem Hash Test",
        custo_aquisicao_dirpf=None,         # lacuna
        regime=Regime.TRANSMISSAO_HERDEIRO,
        opcao=OpcaoArt23.VALOR_HISTORICO,
        valor_partilha=300_000,
    ))

    e_zero = _espolio_base()
    e_zero.adicionar_bem(Bem(
        "Bem Hash Test",
        custo_aquisicao_dirpf=0.0,          # custo zero explícito
        regime=Regime.TRANSMISSAO_HERDEIRO,
        opcao=OpcaoArt23.VALOR_HISTORICO,
        valor_partilha=300_000,
    ))

    h_none = EspolioService.calcular_audit_hash(e_none)
    h_zero = EspolioService.calcular_audit_hash(e_zero)

    assert h_none != h_zero, (
        "Hash(custo=None) n\u00e3o deve igualar Hash(custo=0.0) \u2014 "
        f"ambos produziram {h_none!r}"
    )
    print(f"OK  audit_hash distingue None de 0.0 (B-4)  "
          f"[None={h_none[:8]}\u2026, 0.0={h_zero[:8]}\u2026]")


def test_isencao_imovel_unico_cobertura_transmissao_mercado():
    """M-1: Verifica se isenção de imóvel único (Lei 9.250/95, art. 23)
    cobre Regime.TRANSMISSAO_HERDEIRO com OpcaoArt23.VALOR_MERCADO (abaixo de R$ 440 mil)."""
    from orgaudi_espolio.isencoes import verificar_imovel_unico
    
    b_elegivel = Bem(
        "Apartamento Elegível",
        custo_aquisicao_dirpf=100_000,
        valor_partilha=400_000, # <= 440_000
        regime=Regime.TRANSMISSAO_HERDEIRO,
        opcao=OpcaoArt23.VALOR_MERCADO,
        eh_imovel=True
    )
    res = verificar_imovel_unico(b_elegivel)
    assert res is not None
    assert res.elegivel_em_tese is True
    assert "Lei 9.250/95" in res.base_legal

    b_inelegivel = Bem(
        "Apartamento Inelegível",
        custo_aquisicao_dirpf=100_000,
        valor_partilha=450_000, # > 440_000
        regime=Regime.TRANSMISSAO_HERDEIRO,
        opcao=OpcaoArt23.VALOR_MERCADO,
        eh_imovel=True
    )
    res_in = verificar_imovel_unico(b_inelegivel)
    assert res_in is not None
    assert res_in.elegivel_em_tese is False
    print("OK  isenção imóvel único cobertura transmissão mercado (M-1)")


def test_fracao_herdeiros_diferente_de_um():
    """Verifica comportamento e consistência quando frações não somam 1.0."""
    e = Espolio("Espólio Inconsistente", "000.000.000-00",
                date(2023, 9, 27), date(2025, 7, 16))
    e.adicionar_herdeiro(Herdeiro("Herdeiro A", "1", 0.3))
    e.adicionar_herdeiro(Herdeiro("Herdeiro B", "2", 0.3)) # soma = 0.6
    
    b = Bem("Bem X", custo_aquisicao_dirpf=100_000, valor_partilha=200_000,
            regime=Regime.TRANSMISSAO_HERDEIRO, opcao=OpcaoArt23.VALOR_HISTORICO)
    e.adicionar_bem(b)
    
    res = MotorApuracao(e).apurar()
    assert abs(res["soma_fracoes_herdeiros"] - 0.6) < 1e-5
    print("OK  frações herdeiros diferente de 1.0")


def test_custo_zero_vs_custo_none():
    """Verifica que custo zero é processado normalmente, mas None gera pendência."""
    e = _espolio_base()
    b_zero = Bem("Bem Custo Zero", custo_aquisicao_dirpf=0.0,
                 valor_venda=100_000, regime=Regime.VENDA_PELO_ESPOLIO,
                 data_aquisicao=date(2010, 1, 1), data_operacao=date(2025, 1, 1), eh_imovel=False)
    
    b_none = Bem("Bem Custo None", custo_aquisicao_dirpf=None,
                 valor_venda=100_000, regime=Regime.VENDA_PELO_ESPOLIO,
                 data_aquisicao=date(2010, 1, 1), data_operacao=date(2025, 1, 1), eh_imovel=False)
                 
    e.adicionar_bem(b_zero)
    e.adicionar_bem(b_none)
    MotorApuracao(e).apurar()
    
    assert b_zero.resultado["status"] == StatusApuracao.OK
    assert b_zero.resultado["ganho_bruto"] == 100_000.0
    
    assert b_none.resultado["status"] == StatusApuracao.PENDENTE
    print("OK  custo zero vs custo None")


def test_aliquota_progressiva_faixa_2():
    """Valida alíquota progressiva na faixa 2 (17.5% para ganhos de R$ 5M a R$ 10M).
    Pela Lei 13.259/16, para ganhos > 5M e <= 10M:
    5.000.000 * 15% = 750.000
    Restante * 17.5%
    Ex: 8.000.000 de ganho:
    750.000 + 3.000.000 * 17.5% = 750.000 + 525.000 = 1.275.000
    """
    assert ir_ganho_capital(8_000_000) == 1_275_000.0
    print("OK  alíquota progressiva faixa 2")


def test_aliquota_progressiva_faixa_3():
    """Valida alíquota progressiva na faixa 3 (20% para ganhos de R$ 10M a R$ 30M).
    Pela Lei 13.259/16:
    Até 5M: 15% (750.000)
    De 5M a 10M: 17.5% (875.000)
    De 10M a 30M: 20%
    Ex: 15.000.000 de ganho:
    750.000 + 875.000 + (15M - 10M) * 20% = 1.625.000 + 1.000.000 = 2.625.000
    """
    assert ir_ganho_capital(15_000_000) == 2_625_000.0
    print("OK  alíquota progressiva faixa 3")


def test_aliquota_progressiva_faixa_4():
    """Valida alíquota progressiva na faixa 4 (22.5% para ganhos acima de R$ 30M).
    Pela Lei 13.259/16:
    Até 5M: 15% (750.000)
    De 5M a 10M: 17.5% (875.000)
    De 10M a 30M: 20% (4.000.000)
    Acima de 30M: 22.5%
    Ex: 40.000.000 de ganho:
    750.000 + 875.000 + 4.000.000 + (40M - 30M) * 22.5% = 5.625.000 + 2.250.000 = 7.875.000
    """
    assert ir_ganho_capital(40_000_000) == 7_875_000.0
    print("OK  alíquota progressiva faixa 4")


def test_anonimizador_pii_reversao():
    """A-2: Valida se a anonimização e reversão de PII funcionam de ponta a ponta
    com o placeholder 'ANOM-HHHHH' e sem colisões ou substituições parciais."""
    from orgaudi_espolio.anonimizador import AnonimizadorPII
    
    e = Espolio("Fulano de Tal", "123.456.789-00", date(2023, 1, 1), date(2023, 6, 1))
    e.adicionar_herdeiro(Herdeiro("Herdeiro 1 Real", "111.111.111-11", 0.5))
    e.adicionar_herdeiro(Herdeiro("Herdeiro 2 Real", "222.222.222-22", 0.5))
    
    e_anom, mapa = AnonimizadorPII.anonimizar(e)
    
    assert "Fulano" not in e_anom.nome
    assert "Autor da Heranca" in e_anom.nome
    assert e_anom.cpf_falecido.startswith("ANOM-")
    assert e_anom.cpf_falecido != "123.456.789-00"
    
    assert "111.111.111-11" not in [h.cpf for h in e_anom.herdeiros]
    
    texto_gerado = f"O relatório de {e_anom.nome} com CPF {e_anom.cpf_falecido} indica que {e_anom.herdeiros[0].nome} ({e_anom.herdeiros[0].cpf}) deve receber a herança."
    texto_reverso = AnonimizadorPII.desanonimizar(texto_gerado, mapa)
    
    assert "Fulano de Tal" in texto_reverso
    assert "123.456.789-00" in texto_reverso
    assert "Herdeiro 1 Real" in texto_reverso
    assert "111.111.111-11" in texto_reverso
    print("OK  anonimizador PII e reversão (A-2)")


def test_data_aquisicao_pre_1996_m1_calculo():
    """Valida se m1 para imóvel adquirido pré-1996 inicia em jan/1996."""
    from orgaudi_espolio.fatores_reducao import calcular_fatores_reducao
    
    # Adquirido em 1990 (antes de 1996). Alienação após vigência de FR.
    # m1: Jan/1996 até Nov/2005 = 118 meses.
    # Com convenção "inclusiva": n + 1 = 118 + 1 = 119 meses.
    res = calcular_fatores_reducao(100_000.0, date(1990, 5, 10), date(2025, 1, 15), eh_imovel=True)
    assert res.aplicavel is True
    assert res.m1 == 119
    print("OK  data aquisição pré-1996 m1 cálculo")


def test_data_aquisicao_pos_1996_m1_calculo():
    """Valida se m1 para imóvel adquirido pós-1996 inicia na data real."""
    from orgaudi_espolio.fatores_reducao import calcular_fatores_reducao
    
    # Adquirido em Junho/2000.
    # m1: Jun/2000 até Nov/2005.
    # Exclusivo: (2005 - 2000)*12 + (11 - 6) = 60 + 5 = 65 meses.
    # Inclusivo: 65 + 1 = 66 meses.
    res = calcular_fatores_reducao(100_000.0, date(2000, 6, 15), date(2025, 1, 15), eh_imovel=True)
    assert res.aplicavel is True
    assert res.m1 == 66
    print("OK  data aquisição pós-1996 m1 cálculo")


def test_geracao_audit_hash_identicos():
    """Garante que o mesmo espólio gera exatamente o mesmo hash audit."""
    from orgaudi_espolio.servicos import EspolioService
    
    e1 = _espolio_base()
    e1.adicionar_bem(Bem("Bem X", custo_aquisicao_dirpf=100_000, valor_partilha=200_000,
            regime=Regime.TRANSMISSAO_HERDEIRO, opcao=OpcaoArt23.VALOR_HISTORICO))
            
    e2 = _espolio_base()
    e2.adicionar_bem(Bem("Bem X", custo_aquisicao_dirpf=100_000, valor_partilha=200_000,
            regime=Regime.TRANSMISSAO_HERDEIRO, opcao=OpcaoArt23.VALOR_HISTORICO))
            
    h1 = EspolioService.calcular_audit_hash(e1)
    h2 = EspolioService.calcular_audit_hash(e2)
    assert h1 == h2
    print("OK  geração audit hash idênticos")


def test_convenao_contagem_meses_inclusiva_vs_exclusiva():
    """M-3: Valida a convenção de contagem de meses inclusiva vs exclusiva."""
    from orgaudi_espolio.fatores_reducao import calcular_fatores_reducao
    import orgaudi_espolio.fatores_reducao as fr_mod
    
    # Com "inclusiva"
    fr_mod.CONVENCAO_CONTAGEM_MESES = "inclusiva"
    res_inc = calcular_fatores_reducao(100_000.0, date(2000, 6, 15), date(2025, 1, 15), eh_imovel=True)
    
    # Com "exclusiva"
    fr_mod.CONVENCAO_CONTAGEM_MESES = "exclusiva"
    res_exc = calcular_fatores_reducao(100_000.0, date(2000, 6, 15), date(2025, 1, 15), eh_imovel=True)
    
    # Restaura
    fr_mod.CONVENCAO_CONTAGEM_MESES = "inclusiva"
    
    # Inclusiva deve contar 1 mês a mais que Exclusiva
    assert res_inc.m1 == res_exc.m1 + 1
    assert res_inc.m2 == res_exc.m2 + 1
    print("OK  convenção contagem meses inclusiva vs exclusiva (M-3)")


if __name__ == "__main__":
    for nome, fn in list(globals().items()):
        if nome.startswith("test_") and callable(fn):
            fn()
    print("\nTodos os testes passaram.")

