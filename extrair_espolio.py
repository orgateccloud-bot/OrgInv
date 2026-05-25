# -*- coding: utf-8 -*-
"""
extrair_espolio.py — Extrai dados de espólio a partir de PDFs via Claude.

Uso:
    python extrair_espolio.py doc1.pdf doc2.pdf            # lê PDFs, exibe JSON
    python extrair_espolio.py *.pdf --saida espolio.json   # grava para análise
    python extrair_espolio.py laudos/*.pdf --instrucao "Espólio localizado em Goiânia"

O JSON gerado pode ser usado diretamente com analise_espolio.py:
    python extrair_espolio.py docs/*.pdf --saida data/espolio.json
    python analise_espolio.py data/espolio.json

Requer ANTHROPIC_API_KEY no ambiente.

Sistema OrgAudi · ORGATEC CONTABILIDADE E AUDITORIA
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
from pathlib import Path

# Force UTF-8 output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from orgaudi_espolio import extrair_de_pdfs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extrai espólio de PDFs via Claude Sonnet",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python extrair_espolio.py inventario.pdf escritura.pdf
  python extrair_espolio.py docs/*.pdf --saida data/espolio.json
  python extrair_espolio.py doc.pdf --instrucao "Imóvel em Goiás, regime separação total"
        """,
    )
    parser.add_argument(
        "pdfs",
        nargs="+",
        metavar="PDF",
        help="Um ou mais arquivos PDF do espólio",
    )
    parser.add_argument(
        "--instrucao",
        metavar="TEXTO",
        default="",
        help="Contexto extra para o Claude (estado, tipo de bens, dúvidas específicas)",
    )
    parser.add_argument(
        "--saida",
        metavar="ARQUIVO",
        help="Grava o JSON extraído neste arquivo (ex.: data/espolio.json)",
    )
    parser.add_argument(
        "--chave",
        metavar="API_KEY",
        help="ANTHROPIC_API_KEY (alternativa à variável de ambiente)",
    )
    args = parser.parse_args()

    api_key = args.chave or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[ERRO] ANTHROPIC_API_KEY não definida.")
        print("       Defina com: set ANTHROPIC_API_KEY=sk-ant-...")
        print("       Ou passe via: --chave sk-ant-...")
        sys.exit(1)

    # Carrega todos os PDFs
    documentos: list[tuple[str, bytes]] = []
    for caminho_str in args.pdfs:
        caminho = Path(caminho_str)
        if not caminho.exists():
            print(f"[ERRO] Arquivo não encontrado: {caminho}")
            sys.exit(1)
        if caminho.suffix.lower() != ".pdf":
            print(f"[AVISO] {caminho.name} não parece ser um PDF — incluindo mesmo assim.")
        documentos.append((caminho.name, caminho.read_bytes()))
        print(f"  ✓ {caminho.name} ({caminho.stat().st_size // 1024} KB)")

    print(f"\nEnviando {len(documentos)} documento(s) ao Claude Sonnet...")
    print("─" * 60)

    try:
        extraido, uso = extrair_de_pdfs(
            documentos,
            instrucao_extra=args.instrucao,
            api_key=api_key,
        )
    except RuntimeError as e:
        print(f"[ERRO] {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERRO] Falha na extração: {type(e).__name__}: {e}")
        sys.exit(1)

    # Converte EspolioExtraido → dict compatível com analise_espolio.py
    dados = extraido.model_dump()

    # Normaliza campos para o formato do analise_espolio.py
    saida_json: dict = {
        "_extraido_por": "extrair_espolio.py (Claude Sonnet)",
        "_documentos": [d[0] for d in documentos],
        "_aviso": "Revise todos os campos antes de rodar analise_espolio.py",
        "nome": dados.get("nome_espolio") or "",
        "cpf_falecido": dados.get("cpf_falecido") or "",
        "data_obito": dados.get("data_obito_iso") or "",
        "data_partilha": dados.get("data_partilha_iso") or "",
        "herdeiros": [
            {
                "nome": h.get("nome") or "",
                "cpf": h.get("cpf") or "",
                "fracao_monte": h.get("fracao_monte") or 0.0,
                "eh_meeiro": h.get("eh_meeiro") or False,
            }
            for h in (dados.get("herdeiros") or [])
        ],
        "bens": [
            {
                "identificacao": b.get("identificacao") or "",
                "matricula": b.get("matricula") or "",
                "municipio": b.get("municipio") or "",
                "custo_aquisicao_dirpf": b.get("custo_aquisicao_dirpf"),
                "data_aquisicao": b.get("data_aquisicao_iso"),
                "valor_partilha": b.get("valor_partilha"),
                "valor_venda": b.get("valor_venda"),
                "regime": b.get("regime_sugerido") or "INDETERMINADO",
                "data_operacao": b.get("data_operacao_iso"),
                "opcao": b.get("opcao_art23") or "NAO_APLICAVEL",
                "eh_imovel": b.get("eh_imovel") if b.get("eh_imovel") is not None else True,
                "_confianca": b.get("confianca"),
                "_rationale": b.get("rationale"),
            }
            for b in (dados.get("bens") or [])
        ],
    }

    if dados.get("observacoes_globais"):
        saida_json["_observacoes"] = dados["observacoes_globais"]

    json_str = json.dumps(saida_json, ensure_ascii=False, indent=2)

    print("\nEXTRAÇÃO CONCLUÍDA")
    print(f"  Nome do espólio : {saida_json['nome'] or '(não identificado)'}")
    print(f"  Herdeiros       : {len(saida_json['herdeiros'])}")
    print(f"  Bens            : {len(saida_json['bens'])}")
    print(f"  Tokens usados   : {uso.get('input_tokens', 0):,} entrada / {uso.get('output_tokens', 0):,} saída")

    if dados.get("observacoes_globais"):
        print("\n⚠  OBSERVAÇÕES DO CLAUDE:")
        for obs in dados["observacoes_globais"]:
            print(f"   • {obs}")

    if args.saida:
        Path(args.saida).write_text(json_str, encoding="utf-8")
        print(f"\nJSON gravado em: {args.saida}")
        print(f"Próximo passo  : python analise_espolio.py {args.saida}")
    else:
        print("\n" + "─" * 60)
        print(json_str)


if __name__ == "__main__":
    main()
