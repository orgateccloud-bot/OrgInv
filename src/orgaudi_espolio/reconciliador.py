# -*- coding: utf-8 -*-
"""
reconciliador.py — Reconciliação de valores divergentes entre documentos.

PROBLEMA QUE RESOLVE:
  Documentos fiscais do mesmo espólio frequentemente atribuem valores
  DIFERENTES ao mesmo bem. Exemplo real (espólio Adilson): um imóvel
  avaliado a R$ 110.000 na escritura de inventário e a R$ 25.000 no
  demonstrativo de ITCD. Um sistema que escolhesse sozinho estaria
  adivinhando — e escondendo a adivinhação.

O QUE FAZ:
  Agrupa os valores candidatos por bem, detecta divergências, e produz
  um QUADRO DE CONFLITOS para decisão humana. O motor só recebe valores
  depois que um humano resolveu cada conflito explicitamente.

PRINCÍPIO: o software aponta a divergência; ele NÃO a resolve.

Sistema OrgAudi · ORGATEC CONTABILIDADE E AUDITORIA
"""

from __future__ import annotations
from dataclasses import dataclass, field
from .ingestao import ValorCandidato


@dataclass
class Conflito:
    """Uma divergência de valor entre fontes para o mesmo campo/bem."""
    bem: str
    campo: str                       # ex.: 'valor_partilha', 'custo'
    candidatos: list[ValorCandidato]
    resolvido: bool = False
    valor_escolhido: float | None = None
    justificativa_escolha: str = ""

    def resolver(self, valor: float, justificativa: str) -> None:
        """
        Resolve o conflito por DECISÃO HUMANA. Exige justificativa —
        um valor escolhido sem fundamento não é auditável.
        """
        if not justificativa or len(justificativa.strip()) < 10:
            raise ValueError(
                "A escolha de valor exige justificativa substantiva "
                "(qual documento prevalece e por quê).")
        self.valor_escolhido = valor
        self.justificativa_escolha = justificativa.strip()
        self.resolvido = True


@dataclass
class QuadroReconciliacao:
    """Conjunto de conflitos de um espólio, mais os valores sem conflito."""
    conflitos: list[Conflito] = field(default_factory=list)
    valores_unicos: dict = field(default_factory=dict)  # campo -> valor

    def pendentes(self) -> list[Conflito]:
        return [c for c in self.conflitos if not c.resolvido]

    def tudo_resolvido(self) -> bool:
        return len(self.pendentes()) == 0


def reconciliar(candidatos_por_campo: dict[str, list[ValorCandidato]],
                tolerancia: float = 0.01) -> QuadroReconciliacao:
    """
    Recebe um dict {campo: [candidatos]} e devolve um quadro de
    reconciliação. Campos com um só valor (ou valores idênticos dentro
    da tolerância) passam direto; campos com valores divergentes viram
    Conflito a resolver.

    `candidatos_por_campo` é montado pelo profissional ao associar cada
    valor extraído a um campo do bem — essa associação em si já é uma
    revisão humana do que o parser encontrou.
    """
    quadro = QuadroReconciliacao()

    for campo, cands in candidatos_por_campo.items():
        if not cands:
            continue
        valores = [c.valor for c in cands]
        v_min, v_max = min(valores), max(valores)

        # valores praticamente iguais -> sem conflito
        if v_max - v_min <= tolerancia:
            quadro.valores_unicos[campo] = v_min
        else:
            # divergência real -> conflito para decisão humana
            quadro.conflitos.append(Conflito(
                bem=campo.split(":")[0] if ":" in campo else "(bem)",
                campo=campo,
                candidatos=cands))
    return quadro


def relatorio_conflitos(quadro: QuadroReconciliacao) -> str:
    """Quadro de conflitos legível, para a mesa do profissional."""
    L = ["=" * 70, "QUADRO DE RECONCILIAÇÃO — DIVERGÊNCIAS ENTRE DOCUMENTOS",
         "=" * 70]
    if not quadro.conflitos:
        L.append("Nenhuma divergência detectada entre as fontes.")
    for i, c in enumerate(quadro.conflitos, 1):
        L.append(f"\nCONFLITO {i} — campo '{c.campo}'")
        for cand in c.candidatos:
            L.append(f"  • R$ {cand.valor:,.2f}  "
                     f"(fonte: {cand.documento}, pág.{cand.pagina})")
            L.append(f"    trecho: …{cand.trecho[:80]}…")
        if c.resolvido:
            L.append(f"  ✓ RESOLVIDO: R$ {c.valor_escolhido:,.2f}")
            L.append(f"    justificativa: {c.justificativa_escolha}")
        else:
            L.append("  ⚠ PENDENTE — exige decisão humana fundamentada. "
                     "O motor não calcula este bem até a resolução.")
    L.append("\n" + "=" * 70)
    if quadro.tudo_resolvido():
        L.append("Todos os conflitos resolvidos. Apuração pode prosseguir.")
    else:
        L.append(f"{len(quadro.pendentes())} conflito(s) pendente(s). "
                 f"Apuração BLOQUEADA até resolução.")
    return "\n".join(L)


# ───────────────────────────────────────────────────────────────────────
# RECONCILIADOR COGNITIVO — Validação IA vs Motor Determinístico
# ───────────────────────────────────────────────────────────────────────

from pydantic import BaseModel, Field
import os
import json
import httpx
import anthropic
from typing import Any, Optional
from .dominio import Espolio, Bem, Regime, OpcaoArt23, StatusApuracao
from .motor import MotorApuracao

class EstimativaBem(BaseModel):
    bem: str = Field(description="Identificação ou descrição do bem.")
    regime: str = Field(description="Regime tributário: 'TRANSMISSAO_HERDEIRO', 'VENDA_PELO_ESPOLIO', 'CESSAO_DIREITOS_HEREDITARIOS', 'FORA_DO_ESPOLIO', ou 'INDETERMINADO'.")
    ir_espolio_estimado: float = Field(description="Valor estimado de IR devido pelo espólio para este bem.")
    base_custo_herdeiro: Optional[float] = Field(default=None, description="Base de custo que o herdeiro recebe (apenas para TRANSMISSAO_HERDEIRO).")
    justificativa: str = Field(description="Breve justificativa/raciocínio contábil em português.")

class EstimativaApuracao(BaseModel):
    bens: list[EstimativaBem] = Field(default_factory=list)

@dataclass
class DivergenciaCognitiva:
    bem: str
    campo: str           # 'regime', 'ir_espolio', 'base_custo_herdeiro'
    valor_motor: Any
    valor_ia: Any
    justificativa_ia: str
    observacao: str

SYSTEM_PROMPT_DOUBLE_CHECK = """\
Você é um auditor fiscal independente de segundo nível (Double-Check). 
Sua tarefa é analisar os dados de entrada de um espólio e, de forma 100% independente, estimar para cada bem:
1. O regime tributário correto: 'TRANSMISSAO_HERDEIRO', 'VENDA_PELO_ESPOLIO', 'CESSAO_DIREITOS_HEREDITARIOS', 'FORA_DO_ESPOLIO', ou 'INDETERMINADO'.
2. O IR estimado devido pelo espólio (se houver).
3. A base de custo do herdeiro (apenas para TRANSMISSAO_HERDEIRO, e dependendo se optou por valor histórico ou mercado).

Regras de negócio:
- TRANSMISSAO_HERDEIRO:
  * Valor Histórico (§2º Art. 23): IR no espólio = 0.0. A base de custo do herdeiro = custo original * fração herança. A meação mantém o custo histórico original * fração meação.
  * Valor Mercado (§1º Art. 23): IR no espólio = aliquota progressiva * ganho de capital (partilha - custo) * fração herança. Base de custo do herdeiro = valor partilha * fração herança.
- VENDA_PELO_ESPOLIO:
  * Ganho de capital = valor venda - custo.
  * Aplica fatores de redução FR1/FR2 e Lei 7.713/88 se for imóvel.
  * IR espólio = aliquota progressiva * base tributável * fração herança.
- CESSAO_DIREITOS_HEREDITARIOS:
  * IR no espólio = 0.0 (pois o ganho e o imposto pertencem e devem ser pagos pelos cedentes nas declarações de PF).
- FORA_DO_ESPOLIO:
  * IR espólio = 0.0.

Lembre-se:
- A meação do meeiro sobrevivente NÃO entra na herança transmitida (fração meação = soma das frações dos herdeiros que são meeiros).
- Bens particulares: o meeiro tem meação zero neste bem específico.
- Aplique o raciocínio lógico detalhado e retorne estritamente o formato JSON solicitado.
"""

class ReconciliadorCognitivo:
    """ Realiza a validação paralela cruzando o Motor Python e o Claude 3.5 Sonnet. """

    @staticmethod
    def reconciliar_apuracao(espolio: Espolio, api_key: Optional[str] = None) -> list[DivergenciaCognitiva]:
        # 1. Roda o motor matemático para ter os resultados exatos e populos
        motor = MotorApuracao(espolio)
        motor.apurar()

        # 2. Constrói o prompt com os dados limpos do espólio (sem os resultados do motor)
        dados_entrada = {
            "nome_espolio": espolio.nome,
            "data_obito": espolio.data_obito.isoformat() if espolio.data_obito else None,
            "data_partilha": espolio.data_partilha.isoformat() if espolio.data_partilha else None,
            "herdeiros": [
                {
                    "nome": h.nome,
                    "fracao_monte": h.fracao_monte,
                    "eh_meeiro": h.eh_meeiro
                } for h in espolio.herdeiros
            ],
            "bens": [
                {
                    "identificacao": b.identificacao,
                    "custo_aquisicao_dirpf": b.custo_aquisicao_dirpf,
                    "data_aquisicao": b.data_aquisicao.isoformat() if b.data_aquisicao else None,
                    "valor_partilha": b.valor_partilha,
                    "valor_venda": b.valor_venda,
                    "data_operacao": b.data_operacao.isoformat() if b.data_operacao else None,
                    "regime": b.regime.value,
                    "opcao": b.opcao.value,
                    "eh_imovel": b.eh_imovel,
                    "eh_imovel_rural": b.eh_imovel_rural,
                    "eh_bem_particular": b.eh_bem_particular
                } for b in espolio.bens
            ]
        }

        # 3. Chama a API do Claude Sonnet para obter a estimativa da IA
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY ausente. Defina a env var ou passe api_key.")
        
        # Define timeout global igual ao analista
        HTTPX_TIMEOUT = httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=5.0)
        client = anthropic.Anthropic(api_key=key, http_client=httpx.Client(timeout=HTTPX_TIMEOUT))

        prompt = f"Analise estes dados de entrada do espólio e estime os regimes, IR e bases de custo por bem:\n\n{json.dumps(dados_entrada, indent=2, ensure_ascii=False)}"

        response = client.messages.parse(
            model="claude-sonnet-4-6",
            max_tokens=8000,
            thinking={"type": "adaptive"},
            system=[{
                "type": "text",
                "text": SYSTEM_PROMPT_DOUBLE_CHECK,
                "cache_control": {"type": "ephemeral"}
            }],
            messages=[{"role": "user", "content": prompt}],
            output_format=EstimativaApuracao
        )

        estimativas = response.parsed_output
        if estimativas is None:
            raise RuntimeError("Sonnet retornou parsed_output nulo na reconciliação cognitiva.")

        divergencias = []

        # 4. Compara os valores
        for est in estimativas.bens:
            # Encontra o bem correspondente
            bem_motor = next((b for b in espolio.bens if b.identificacao.strip().lower() == est.bem.strip().lower()), None)
            if not bem_motor:
                continue

            r = bem_motor.resultado or {}
            if r.get("status") != StatusApuracao.OK:
                continue # Pula se estiver pendente no motor

            # 4.1 Compara Regime
            regime_ia = est.regime.upper()
            regime_motor = bem_motor.regime.value
            if regime_ia != regime_motor and regime_ia != "INDETERMINADO":
                # Mapeamento tolerante
                if not (regime_ia == "TRANSMISSAO_HERDEIRO" and regime_motor == "TRANSMISSAO_HERDEIRO"):
                    divergencias.append(DivergenciaCognitiva(
                        bem=bem_motor.identificacao,
                        campo="regime",
                        valor_motor=regime_motor,
                        valor_ia=regime_ia,
                        justificativa_ia=est.justificativa,
                        observacao="Divergência de classificação jurídica da operação."
                    ))

            # 4.2 Compara IR Espólio (com tolerância de R$ 5,00 para arredondamentos e simplificações de FR)
            ir_motor = r.get("ir_espolio") or 0.0
            ir_ia = est.ir_espolio_estimado
            if abs(ir_motor - ir_ia) > 5.0:
                divergencias.append(DivergenciaCognitiva(
                    bem=bem_motor.identificacao,
                    campo="ir_espolio",
                    valor_motor=round(ir_motor, 2),
                    valor_ia=round(ir_ia, 2),
                    justificativa_ia=est.justificativa,
                    observacao="O cálculo aritmético do motor difere da estimativa lógica da IA por mais de R$ 5,00."
                ))

            # 4.3 Compara Base Custo Herdeiro (apenas se aplicável no motor)
            base_motor = r.get("base_custo_herdeiro")
            base_ia = est.base_custo_herdeiro
            if base_motor is not None and base_ia is not None:
                if abs(base_motor - base_ia) > 5.0:
                    divergencias.append(DivergenciaCognitiva(
                        bem=bem_motor.identificacao,
                        campo="base_custo_herdeiro",
                        valor_motor=round(base_motor, 2),
                        valor_ia=round(base_ia, 2),
                        justificativa_ia=est.justificativa,
                        observacao="A base de custo recebida pelo herdeiro difere da estimativa lógica da IA por mais de R$ 5,00."
                    ))

        return divergencias

