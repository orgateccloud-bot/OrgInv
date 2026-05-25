# -*- coding: utf-8 -*-
"""
ai_analista.py — Análise auditorial do espólio via Claude Sonnet.

Após o motor apurar, o resultado é um dicionário de números + listas de
pendências. Este módulo envia o relatório técnico ao AuditTax Compliance
Specialist (v3.4) que emite uma leitura auditorial estruturada em PT-BR:
classificação jurídica, fundamentação normativa, rotulagem de confiança
([CONFIRMADO]/[CONDICIONAL]/[NÃO VERIFICÁVEL]), alerta de risco qualitativo
e plano de autorregularização.

A IA NÃO substitui o motor — ela explica o motor com rastreabilidade total.
Toda a aritmética (alíquotas, FR1/FR2, rateio por quinhão) já foi feita em
código verificável. O Sonnet redige e audita; não recalcula.

Sistema OrgAudi · ORGATEC CONTABILIDADE E AUDITORIA
"""
from __future__ import annotations

import os
import httpx
from typing import Iterator, Optional

import anthropic

from .dominio import Espolio, StatusApuracao
from .motor import MotorApuracao
from .otimizador import Otimizador
from .isencoes import verificar_isencoes
from .relatorio import gerar_relatorio_texto

MODELO = "claude-sonnet-4-6"
MAX_TOKENS = 8000
# A-5: timeout global para requisições ao Anthropic.
# connect=10s evita espera infinita se a rede cair;
# read=120s cobre respostas longas do Sonnet (8k tokens, extended thinking).
HTTPX_TIMEOUT = httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=5.0)


SYSTEM_PROMPT = """\
- **Decreto 9.580/2018 (RIR/2018)** — Regulamento do Imposto de Renda; art. 551 reproduz o art. 23 da Lei 9.532/97.
- **Instruções Normativas RFB** aplicáveis (IN 84/2001 e IN 599/2005, entre outras).

## MISSÃO E OBJETIVOS
1. Auditar operações de espólios com a distinção estrita entre sucessão causa mortis (art. 23, Lei 9.532/97) e alienação onerosa (art. 21, Lei 8.981/95 c/c Lei 13.259/16).
2. Distinguir, dentro da titularidade, a fração de meação (bem já pertencente ao cônjuge/companheiro — sem transmissão, sem incidência do art. 23) da fração de herança (transmissão causa mortis). A meação depende do regime de bens e da data de aquisição de cada bem.
3. Impedir a aplicação indevida do valor histórico ou de mercado sem a devida concordância com as regras de sucessão causa mortis, meação, alienação onerosa e cessão de direitos hereditários.
4. Identificar com clareza a natureza jurídica da operação para cada bem.
5. Emitir pareceres com base estritamente nos dados fornecidos pelo motor de cálculo verificado.

## ESTRUTURA DO PARECER (OBRIGATÓRIA)
Você deve estruturar a resposta em exatamente quatro blocos com cabeçalhos em negrito Markdown (sem numeração interna extra nos cabeçalhos, apenas o texto literal abaixo):

**1. Resumo executivo**
Situação geral da apuração, IR total devido consolidado pelo motor e se a apuração está conclusiva ou pendente de informações cruciais.
- Se houver qualquer irregularidade ou risco identificado, classifique explicitamente o risco de autuação como: **Baixo**, **Médio** ou **Elevado-Crítico**.
- Se a apuração estiver PENDENTE, o resumo executivo DEVE alertar que o IR total ainda NÃO é definitivo.

**2. Pontos por bem**
Para cada bem listado no relatório técnico:
- Identifique o bem e descreva resumidamente a operação (sucessão causa mortis, meação, alienação onerosa, etc.).
- Indique o regime aplicado, o valor do IR apurado pelo motor e os pontos sensíveis que o profissional precisa conferir (datas de aquisição, custos históricos, fatores de redução FR1/FR2 e elegibilidade).
- CITE explicitamente a base legal aplicável (artigo de lei e IN aplicáveis). Jurisprudência só pode ser mencionada após a devida fundamentação legal.

**3. Decisões pendentes**
Bullets objetivos do que exige juízo e ação humana imediata:
- Escolha estratégica entre o §1º (mercado) e §2º (histórico) do Art. 23 da Lei 9.532/97.
- Solicitação obrigatória da **DIRPF do autor da herança/alienante** se o custo de aquisição for indeterminado ou estimado (declare que sem ela o valor do imposto é um cenário-teto condicional).
- Confirmação sobre se a Declaração Final de Espólio (DFE) já foi processada (se sim, restrinja a atuação a retificações).
- Escolhas pendentes de isenções e regimes de meação. Se nada estiver pendente, declare expressamente.

**4. Riscos e prazos**
Pontos críticos e planos de contingência:
- Prazos regulamentares para emissão e pagamento do DARF de ganho de capital (último dia útil do mês seguinte ao da ocorrência do fato gerador).
- Penalidades incidentes em caso de atraso: multa de mora (0,33% ao dia, limitada a 20% nos termos da Lei 9.430/96, art. 61) e juros de mora acumulados pela taxa Selic (Lei 9.065/95, art. 13).
- **PLANO DE AÇÃO**: Proponha autorregularização via retificação ou recolhimento em atraso. Havendo possibilidade, fundamente o pedido na denúncia espontânea (art. 138 do CTN), destacando que ela afasta a multa de mora desde que realizada antes de iniciado qualquer procedimento de fiscalização (e observada a Súmula 360 do STJ).

## RESTRIÇÕES DE ESTILO E LINGUAGEM
- Linguagem direta, formal e estritamente técnica, sem ambiguidades ou floreios comerciais.
- Sem emojis. Sem frases de cortesia como "fico à disposição" ou "espero ter ajudado".
- NUNCA invente números ou recalcule valores aritméticos. Utilize APENAS os dados fornecidos no relatório técnico do motor.
- Se o custo de aquisição for indeterminado, não emita resultado conclusivo de imposto; declare a indeterminação e trate o valor apurado como cenário-teto condicional.
- Estruture a resposta usando rigorosamente os quatro cabeçalhos em negrito especificados acima para garantir a correta renderização na interface do sistema."""


def _client(api_key: Optional[str] = None) -> anthropic.Anthropic:
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY ausente. Defina a env var ou passe api_key.")
    return anthropic.Anthropic(api_key=key, http_client=httpx.Client(timeout=HTTPX_TIMEOUT))


def _montar_contexto(espolio: Espolio) -> str:
    """Concatena tudo que o motor produziu — entrada para a IA."""
    motor = MotorApuracao(espolio)
    resumo = motor.apurar()
    recomendacoes = Otimizador(espolio).otimizar()

    L: list[str] = []
    add = L.append
    add("# RELATÓRIO TÉCNICO DO MOTOR")
    add("")
    add(gerar_relatorio_texto(espolio))
    add("")
    add("# RESUMO ESTRUTURADO (do motor — não recalcular)")
    add(f"IR total do espólio: R$ {resumo['ir_espolio_total']:,.2f}")
    add(f"Bens conclusivos: {resumo['bens_conclusivos']}")
    add(f"Bens pendentes: {resumo['bens_pendentes']}")
    add(f"Apuração CONCLUSIVA: {resumo['conclusivo']}")
    add(f"Soma das frações dos herdeiros: {resumo['soma_fracoes_herdeiros']}")
    add("")
    add("# ISENÇÕES A VERIFICAR (não aplicadas pelo motor)")
    qualquer = False
    for b in espolio.bens:
        verifs = verificar_isencoes(b)
        for v in verifs:
            qualquer = True
            sit = "elegível em tese" if v.elegivel_em_tese else "NÃO elegível"
            add(f"- {b.identificacao} → {v.isencao} ({v.base_legal}): {sit}")
            if v.observacao:
                add(f"  {v.observacao}")
    if not qualquer:
        add("(nenhuma verificação aplicável)")
    add("")
    add("# CENÁRIOS DE OTIMIZAÇÃO (motor)")
    if not recomendacoes:
        add("(sem cenários — regimes sem escolha ou bens pendentes)")
    for rec in recomendacoes:
        add(f"- {rec.bem.identificacao}: recomendado "
            f"'{rec.recomendado.descricao}' (economia vs pior: "
            f"R$ {rec.economia_vs_pior:,.2f}) — {rec.nota_decisao}")

    return "\n".join(L)


# ───────────────────────────────────────────────────────────────────────
# API pública
# ───────────────────────────────────────────────────────────────────────

def analisar(espolio: Espolio,
             api_key: Optional[str] = None) -> tuple[str, dict]:
    """
    Versão não-streaming. Devolve (texto_completo, uso).
    Útil para gravar no laudo PDF.
    """
    client = _client(api_key)
    contexto = _montar_contexto(espolio)

    response = client.messages.create(
        model=MODELO,
        max_tokens=MAX_TOKENS,
        thinking={"type": "adaptive"},
        system=[{
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{
            "role": "user",
            "content": (
                "Faça a leitura profissional do relatório abaixo conforme "
                "as instruções. Seja específico aos dados deste espólio — "
                "não escreva em termos genéricos.\n\n" + contexto)
        }],
    )

    texto = "\n".join(b.text for b in response.content if b.type == "text")
    uso = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "cache_creation_input_tokens":
            getattr(response.usage, "cache_creation_input_tokens", 0),
        "cache_read_input_tokens":
            getattr(response.usage, "cache_read_input_tokens", 0),
        "stop_reason": response.stop_reason,
    }
    return texto, uso


def analisar_stream(espolio: Espolio,
                    api_key: Optional[str] = None) -> Iterator[str]:
    """
    Versão streaming — gera tokens à medida que chegam. Para uso com
    `st.write_stream()` no Streamlit. NÃO inclui o `uso` ao final.
    """
    client = _client(api_key)
    contexto = _montar_contexto(espolio)

    with client.messages.stream(
        model=MODELO,
        max_tokens=MAX_TOKENS,
        thinking={"type": "adaptive"},
        system=[{
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{
            "role": "user",
            "content": (
                "Faça a leitura profissional do relatório abaixo conforme "
                "as instruções. Seja específico aos dados deste espólio — "
                "não escreva em termos genéricos.\n\n" + contexto)
        }],
    ) as stream:
        for delta in stream.text_stream:
            yield delta
