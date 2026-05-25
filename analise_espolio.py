# -*- coding: utf-8 -*-
"""
analise_espolio.py — Análise de espólio via linha de comando.

Uso:
    python analise_espolio.py                        # usa data/espolio.json
    python analise_espolio.py data/espolio.json      # arquivo explícito
    python analise_espolio.py --simular              # sem chamar Claude
    python analise_espolio.py --saida relatorio.txt  # grava resultado

Fluxo:
    1. Lê JSON do espólio (ver data/template_espolio.json para o formato)
    2. Roda o motor de cálculo (IR, alíquotas, FR1/FR2)
    3. Verifica isenções e otimizações
    4. Chama Claude (se ANTHROPIC_API_KEY disponível e --simular não usado)
    5. Exibe e/ou grava o relatório completo

Sistema OrgAudi · ORGATEC CONTABILIDADE E AUDITORIA
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

# Force UTF-8 output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from orgaudi_espolio import (
    Bem, Espolio, Herdeiro,
    Regime, OpcaoArt23,
    MotorApuracao, Otimizador,
    verificar_isencoes,
    gerar_relatorio_texto,
)


# ───────────────────────────────────────────────────────────────────────────
# Deserialização do JSON
# ───────────────────────────────────────────────────────────────────────────

def _data(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


_REGIME_ALIAS: dict[str, Regime] = {
    "TRANSMISSAO_HERDEIRO": Regime.TRANSMISSAO_HERDEIRO,
    "transmissao_herdeiro": Regime.TRANSMISSAO_HERDEIRO,
    "VENDA_PELO_ESPOLIO": Regime.VENDA_PELO_ESPOLIO,
    "venda_pelo_espolio": Regime.VENDA_PELO_ESPOLIO,
    "CESSAO_DIREITOS_HEREDITARIOS": Regime.CESSAO_DIREITOS_HEREDITARIOS,
    "cessao_direitos_hereditarios": Regime.CESSAO_DIREITOS_HEREDITARIOS,
    "cessao_direitos": Regime.CESSAO_DIREITOS_HEREDITARIOS,
    "FORA_DO_ESPOLIO": Regime.FORA_DO_ESPOLIO,
    "fora_do_espolio": Regime.FORA_DO_ESPOLIO,
    "fora_do_monte": Regime.FORA_DO_ESPOLIO,
}

_OPCAO_ALIAS: dict[str, OpcaoArt23] = {
    "VALOR_HISTORICO": OpcaoArt23.VALOR_HISTORICO,
    "valor_historico": OpcaoArt23.VALOR_HISTORICO,
    "VALOR_MERCADO": OpcaoArt23.VALOR_MERCADO,
    "valor_mercado": OpcaoArt23.VALOR_MERCADO,
    "NAO_APLICAVEL": OpcaoArt23.NAO_APLICAVEL,
    "nao_aplicavel": OpcaoArt23.NAO_APLICAVEL,
}


def _regime(s: str) -> Regime:
    if s in _REGIME_ALIAS:
        return _REGIME_ALIAS[s]
    try:
        return next(r for r in Regime if r.value == s)
    except StopIteration:
        return Regime.INDETERMINADO


def _opcao(s: str) -> OpcaoArt23:
    if s in _OPCAO_ALIAS:
        return _OPCAO_ALIAS[s]
    try:
        return next(o for o in OpcaoArt23 if o.value == s)
    except StopIteration:
        return OpcaoArt23.NAO_APLICAVEL


def carregar_espolio(caminho: Path) -> Espolio:
    with open(caminho, encoding="utf-8") as f:
        d = json.load(f)

    e = Espolio(
        nome=d["nome"],
        cpf_falecido=d.get("cpf_falecido", ""),
        data_obito=_data(d.get("data_obito")) or date.today(),
        data_partilha=_data(d.get("data_partilha")) or date.today(),
    )

    for h in d.get("herdeiros", []):
        if not h.get("nome", "").strip():
            continue
        e.adicionar_herdeiro(Herdeiro(
            nome=h["nome"],
            cpf=h.get("cpf", ""),
            fracao_monte=float(h.get("fracao_monte", 0)),
            eh_meeiro=bool(h.get("eh_meeiro", False)),
        ))

    for b in d.get("bens", []):
        if not b.get("identificacao", "").strip():
            continue
        e.adicionar_bem(Bem(
            identificacao=b["identificacao"],
            matricula=b.get("matricula", ""),
            municipio=b.get("municipio", ""),
            custo_aquisicao_dirpf=b.get("custo_aquisicao_dirpf"),
            data_aquisicao=_data(b.get("data_aquisicao")),
            valor_partilha=b.get("valor_partilha"),
            valor_venda=b.get("valor_venda"),
            regime=_regime(b.get("regime", "")),
            data_operacao=_data(b.get("data_operacao")),
            opcao=_opcao(b.get("opcao", "")),
            eh_imovel=bool(b.get("eh_imovel", True)),
        ))

    return e


# ───────────────────────────────────────────────────────────────────────────
# Relatório local (sem IA)
# ───────────────────────────────────────────────────────────────────────────

def relatorio_local(espolio: Espolio) -> str:
    motor = MotorApuracao(espolio)
    resumo = motor.apurar()
    recomendacoes = Otimizador(espolio).otimizar()

    linhas: list[str] = []
    add = linhas.append

    add("=" * 70)
    add("RELATÓRIO DE APURAÇÃO — ORGAUDI ESPÓLIO")
    add("=" * 70)
    add("")
    add(gerar_relatorio_texto(espolio))
    add("")
    add("─" * 70)
    add("RESUMO")
    add(f"  IR total do espólio : R$ {resumo['ir_espolio_total']:>12,.2f}")
    add(f"  Bens conclusivos    : {resumo['bens_conclusivos']}")
    add(f"  Bens pendentes      : {resumo['bens_pendentes']}")
    add(f"  Apuração conclusiva : {'SIM' if resumo['conclusivo'] else 'NÃO — há pendências'}")
    add("")

    isencoes_encontradas = False
    for b in espolio.bens:
        for v in verificar_isencoes(b):
            if not isencoes_encontradas:
                add("─" * 70)
                add("ISENÇÕES A VERIFICAR")
                isencoes_encontradas = True
            sit = "elegível em tese" if v.elegivel_em_tese else "não elegível"
            add(f"  {b.identificacao}: {v.isencao} ({sit})")
            if v.observacao:
                add(f"    → {v.observacao}")
    if isencoes_encontradas:
        add("")

    if recomendacoes:
        add("─" * 70)
        add("CENÁRIOS DE OTIMIZAÇÃO")
        for rec in recomendacoes:
            add(f"  {rec.bem.identificacao}")
            add(f"    Recomendado : {rec.recomendado.descricao}")
            add(f"    Economia vs pior: R$ {rec.economia_vs_pior:,.2f}")
            add(f"    Nota: {rec.nota_decisao}")
        add("")

    add("=" * 70)
    return "\n".join(linhas)


# ───────────────────────────────────────────────────────────────────────────
# Análise com Claude (streaming)
# ───────────────────────────────────────────────────────────────────────────

def analisar_com_claude(espolio: Espolio) -> str:
    try:
        import anthropic
    except ImportError:
        print("[AVISO] Pacote 'anthropic' não instalado. Rode: pip install anthropic")
        return ""

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[AVISO] ANTHROPIC_API_KEY não definida. Exportando apenas o relatório técnico.")
        return ""

    from orgaudi_espolio.ai_analista import _montar_contexto, SYSTEM_PROMPT, MODELO, MAX_TOKENS

    client = anthropic.Anthropic(api_key=api_key)
    contexto = _montar_contexto(espolio)

    print("\n" + "─" * 70)
    print("ANÁLISE PROFISSIONAL — CLAUDE (streaming)")
    print("─" * 70)

    partes: list[str] = []
    with client.messages.stream(
        model=MODELO,
        max_tokens=MAX_TOKENS,
        thinking={"type": "adaptive"},
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{
            "role": "user",
            "content": (
                "Faça a leitura profissional do relatório abaixo conforme "
                "as instruções. Seja específico aos dados deste espólio — "
                "não escreva em termos genéricos.\n\n" + contexto
            ),
        }],
    ) as stream:
        for delta in stream.text_stream:
            print(delta, end="", flush=True)
            partes.append(delta)

    print()
    return "".join(partes)


# ───────────────────────────────────────────────────────────────────────────
# Entry point
# ───────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Análise de espólio ORGAUDI via linha de comando",
    )
    parser.add_argument(
        "arquivo",
        nargs="?",
        default="data/espolio.json",
        help="JSON do espólio (padrão: data/espolio.json)",
    )
    parser.add_argument(
        "--simular",
        action="store_true",
        help="Apenas relatório técnico, sem chamar Claude",
    )
    parser.add_argument(
        "--saida",
        metavar="ARQUIVO",
        help="Grava o relatório neste arquivo .txt",
    )
    args = parser.parse_args()

    caminho = Path(args.arquivo)
    if not caminho.exists():
        print(f"[ERRO] Arquivo não encontrado: {caminho}")
        print(f"       Crie o arquivo com base em: data/template_espolio.json")
        sys.exit(1)

    print(f"Carregando: {caminho}")
    espolio = carregar_espolio(caminho)
    print(f"Espólio: {espolio.nome}")
    print(f"Bens: {len(espolio.bens)} | Herdeiros: {len(espolio.herdeiros)}")

    relatorio = relatorio_local(espolio)
    print(relatorio)

    analise_ia = ""
    if not args.simular:
        analise_ia = analisar_com_claude(espolio)

    if args.saida:
        conteudo = relatorio
        if analise_ia:
            conteudo += "\n\nANÁLISE PROFISSIONAL — CLAUDE\n" + "─" * 70 + "\n" + analise_ia
        Path(args.saida).write_text(conteudo, encoding="utf-8")
        print(f"\nRelatório gravado em: {args.saida}")


if __name__ == "__main__":
    main()
