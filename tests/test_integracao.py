# -*- coding: utf-8 -*-
"""
test_integracao.py — Testes de integração do pacote orgaudi_espolio e da API backend.
Rodar: python -m pytest tests/test_integracao.py -v
"""
import sys
import os
import tempfile
from datetime import date
from fastapi.testclient import TestClient

# Adiciona src/ e a raiz do projeto ao path
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "src"))
sys.path.insert(0, _ROOT)

from orgaudi_espolio import (
    Bem, Espolio, Herdeiro, Regime, OpcaoArt23, StatusApuracao,
    MotorApuracao, Otimizador, verificar_isencoes
)
from orgaudi_espolio.servicos import EspolioService
from orgaudi_espolio.relatorio import gerar_relatorio_texto
from orgaudi_espolio.laudo_xlsx import gerar_laudo_xlsx
from orgaudi_espolio.laudo_pdf import gerar_laudo_pdf

# Importa o app da API
from backend.api import app

def _criar_espolio_integracao() -> Espolio:
    e = Espolio("Espolio Integracao S.A.", "999.999.999-99", date(2023, 10, 1), date(2025, 5, 20))
    e.adicionar_herdeiro(Herdeiro("Herdeiro 1", "111.111.111-11", 0.5))
    e.adicionar_herdeiro(Herdeiro("Meeiro Sobrevivente", "222.222.222-22", 0.5, eh_meeiro=True))
    
    # Adiciona bens em regimes variados
    e.adicionar_bem(Bem(
        identificacao="Apartamento Centro",
        custo_aquisicao_dirpf=200_000,
        valor_partilha=600_000,
        regime=Regime.TRANSMISSAO_HERDEIRO,
        opcao=OpcaoArt23.VALOR_MERCADO,
        eh_imovel=True,
        data_aquisicao=date(2000, 1, 1)
    ))
    e.adicionar_bem(Bem(
        identificacao="Casa Praia",
        custo_aquisicao_dirpf=150_000,
        valor_venda=500_000,
        regime=Regime.VENDA_PELO_ESPOLIO,
        eh_imovel=True,
        data_aquisicao=date(1995, 6, 1),
        data_operacao=date(2024, 12, 1)
    ))
    return e


def test_integracao_fluxo_completo():
    """1. Fluxo completo de apuração e otimização."""
    espolio = _criar_espolio_integracao()
    motor = MotorApuracao(espolio)
    resumo = motor.apurar()
    
    assert resumo["conclusivo"] is True
    assert resumo["ir_espolio_total"] > 0
    assert resumo["bens_conclusivos"] == 2
    
    # Roda otimizador
    otm = Otimizador(espolio)
    recomenda = otm.otimizar()
    assert len(recomenda) == 2
    
    # Verifica isenções
    isencoes_b1 = verificar_isencoes(espolio.bens[0])
    assert len(isencoes_b1) > 0
    print("OK: test_integracao_fluxo_completo")


def test_integracao_relatorio_txt():
    """2. Geração e conformidade do relatório textual (.txt)."""
    espolio = _criar_espolio_integracao()
    texto = gerar_relatorio_texto(espolio)
    
    assert "RELATÓRIO DE APURAÇÃO" in texto
    assert "Espolio Integracao S.A." in texto
    assert "IR FINAL DO ESPÓLIO" in texto
    assert "GCAP" in texto
    assert "COMPARATIVO" in texto
    print("OK: test_integracao_relatorio_txt")


def test_integracao_laudo_xlsx():
    """3. Geração e exportação do laudo em formato Excel (.xlsx)."""
    espolio = _criar_espolio_integracao()
    # Executa apuração para popular resultados
    MotorApuracao(espolio).apurar()
    
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp_name = tmp.name
        
    try:
        gerar_laudo_xlsx(espolio, tmp_name)
        assert os.path.exists(tmp_name)
        assert os.path.getsize(tmp_name) > 0
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
    print("OK: test_integracao_laudo_xlsx")


def test_integracao_laudo_pdf_reactive():
    """4. Geração do laudo PDF e documento reativo."""
    espolio = _criar_espolio_integracao()
    MotorApuracao(espolio).apurar()
    
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_name = tmp.name
        
    try:
        gerar_laudo_pdf(espolio, tmp_name, analise_ia="Test analysis text")
        assert os.path.exists(tmp_name)
        assert os.path.getsize(tmp_name) > 0
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
    print("OK: test_integracao_laudo_pdf_reactive")


def test_integracao_api_endpoints():
    """5. Teste de endpoints HTTP via FastAPI TestClient."""
    client = TestClient(app)
    
    # 5.1 Health check
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    
    # 5.2 Exemplo
    res = client.get("/api/exemplo")
    assert res.status_code == 200
    ex = res.json()
    assert "nome" in ex
    assert len(ex["bens"]) > 0
    
    # 5.3 Apurar
    res = client.post("/api/apurar", json=ex)
    assert res.status_code == 200
    assert "resumo" in res.json()
    
    # 5.4 Relatório
    res = client.post("/api/relatorio", json=ex)
    assert res.status_code == 200
    assert "texto" in res.json()
    
    # 5.5 Laudo XLSX
    res = client.post("/api/laudo/xlsx", json=ex)
    assert res.status_code == 200
    assert len(res.content) > 0
    
    # 5.6 Laudo PDF
    pdf_payload = {"espolio": ex, "analise_ia": "Analise de Teste"}
    res = client.post("/api/laudo/pdf", json=pdf_payload)
    assert res.status_code == 200
    assert len(res.content) > 0
    
    # 5.7 Laudo Reativo Markdown
    res = client.post("/api/laudo/reactive", json=ex)
    assert res.status_code == 200
    assert len(res.content) > 0
    
    print("OK: test_integracao_api_endpoints")


def test_integracao_reconciliador_cognitivo():
    """6. Valida o ReconciliadorCognitivo e o endpoint /api/reconciliar usando mock para evitar chamadas de API reais."""
    from unittest.mock import patch, MagicMock
    from orgaudi_espolio.reconciliador import ReconciliadorCognitivo, EstimativaApuracao, EstimativaBem
    
    espolio = _criar_espolio_integracao()
    
    # Prepara mock da resposta do Claude com uma divergência induzida de IR
    mock_parsed_output = EstimativaApuracao(
        bens=[
            EstimativaBem(
                bem="Apartamento Centro",
                regime="TRANSMISSAO_HERDEIRO",
                ir_espolio_estimado=9999.0, # Divergente do motor (que calculou zero ou outro valor)
                base_custo_herdeiro=100000.0,
                justificativa="Cálculo simulado divergente."
            )
        ]
    )
    
    with patch("anthropic.resources.Messages.parse") as mock_parse:
        mock_response = MagicMock()
        mock_response.parsed_output = mock_parsed_output
        mock_response.usage = MagicMock(input_tokens=10, output_tokens=10)
        mock_parse.return_value = mock_response
        
        # 1. Teste direto da classe ReconciliadorCognitivo
        divergencias = ReconciliadorCognitivo.reconciliar_apuracao(espolio, api_key="fake-key")
        
        assert len(divergencias) > 0
        assert any(d.campo == "ir_espolio" for d in divergencias)
        assert any(d.bem == "Apartamento Centro" for d in divergencias)
        
        # 2. Teste do endpoint /api/reconciliar via TestClient
        client = TestClient(app)
        ex = client.get("/api/exemplo").json()
        
        # Altera o nome do bem no mock para casar com o do exemplo
        mock_parsed_output.bens[0].bem = "Lote A — Casa residencial"
        
        res = client.post("/api/reconciliar", json={"espolio": ex, "api_key": "fake-key"})
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) > 0
        print("OK: test_integracao_reconciliador_cognitivo")

