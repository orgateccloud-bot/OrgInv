# -*- coding: utf-8 -*-
"""
ingestao.py — Extração de valores de documentos fiscais em PDF.

FILOSOFIA — leia antes de usar:
  O parsing é automático; a CONFIRMAÇÃO de cada dado é um ato humano.
  Cada valor extraído carrega a sua ORIGEM. Documentos do mesmo espólio
  divergem entre si para o mesmo bem; o extrator coleta CANDIDATOS e
  nunca decide qual está certo — isso é tarefa do reconciliador, com
  decisão humana. O motor de cálculo recusa valor não-confirmado.

LIMITAÇÃO: extração de PDF é heurística. PDF escaneado pode falhar.
O resultado é uma MINUTA que o profissional revisa, não dado final.

Sistema OrgAudi · ORGATEC CONTABILIDADE E AUDITORIA
"""

from __future__ import annotations
from dataclasses import dataclass, field
import re

try:
    import pdfplumber
    _PDF_OK = True
except ImportError:
    _PDF_OK = False


@dataclass
class ValorCandidato:
    """Um valor monetário extraído de um documento, COM origem.
    'confirmado' só vira True por ação humana no reconciliador."""
    valor: float
    rotulo: str
    documento: str
    pagina: int
    trecho: str
    confirmado: bool = False


@dataclass
class ExtracaoDocumento:
    documento: str
    paginas: int
    candidatos: list[ValorCandidato] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


_RE_MOEDA = re.compile(r'R?\$?\s*([0-9]{1,3}(?:\.[0-9]{3})*,[0-9]{2})')


def _br_para_float(s: str) -> float:
    """'1.536.000,00' -> 1536000.0"""
    return float(s.replace(".", "").replace(",", "."))


def _contexto(texto: str, ini: int, fim: int, janela: int = 70) -> str:
    a = max(0, ini - janela)
    b = min(len(texto), fim + janela)
    return re.sub(r'\s+', ' ', texto[a:b]).strip()


def extrair_valores_pdf(caminho: str,
                        nome_exibicao: str = "") -> ExtracaoDocumento:
    """
    Extrai todos os valores monetários de um PDF, cada um com origem.
    NÃO interpreta qual valor é o correto — apenas coleta candidatos.
    """
    nome = nome_exibicao or caminho.split("/")[-1]
    ext = ExtracaoDocumento(documento=nome, paginas=0)

    if not _PDF_OK:
        ext.avisos.append(
            "pdfplumber não instalado — extração indisponível. "
            "Instalar: pip install pdfplumber")
        return ext

    try:
        with pdfplumber.open(caminho) as pdf:
            ext.paginas = len(pdf.pages)
            for i, pag in enumerate(pdf.pages, start=1):
                txt = pag.extract_text() or ""
                if not txt.strip():
                    ext.avisos.append(
                        f"Página {i}: sem texto extraível — possível "
                        f"PDF escaneado. Exige OCR ou conferência manual.")
                    continue
                for m in _RE_MOEDA.finditer(txt):
                    ext.candidatos.append(ValorCandidato(
                        valor=_br_para_float(m.group(1)),
                        rotulo="(rótulo a definir — ver trecho)",
                        documento=nome,
                        pagina=i,
                        trecho=_contexto(txt, m.start(), m.end()),
                    ))
    except Exception as e:
        ext.avisos.append(f"Falha ao abrir/ler o PDF: {e}")

    if not ext.candidatos and not ext.avisos:
        ext.avisos.append("Nenhum valor monetário reconhecido no documento.")
    return ext


def resumo_extracao(ext: ExtracaoDocumento) -> str:
    """Resumo legível de uma extração, para revisão humana."""
    L = [f"Documento: {ext.documento}  ({ext.paginas} página(s))",
         f"Valores candidatos encontrados: {len(ext.candidatos)}"]
    for av in ext.avisos:
        L.append(f"  ⚠ {av}")
    for c in ext.candidatos:
        L.append(f"  • R$ {c.valor:,.2f}  [pág.{c.pagina}]  "
                 f"…{c.trecho[:90]}…")
    L.append("\nNENHUM destes valores deve ser usado em cálculo antes de "
             "passar pelo reconciliador e ser confirmado por um humano.")
    return "\n".join(L)
