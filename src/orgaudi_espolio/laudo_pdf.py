# -*- coding: utf-8 -*-
"""
laudo_pdf.py — Geração do laudo em PDF via Playwright (Chromium headless).

Renderiza o HTML produzido por laudo_html.py com fidelidade total ao
design system (gradientes de capa, fontes Google, tabelas e componentes
do laudo_detalhado.html). Usa Chromium headless via playwright.

Sistema OrgAudi · ORGATEC CONTABILIDADE E AUDITORIA
"""
from __future__ import annotations

from typing import Optional

from .dominio import Espolio
from .laudo_html import gerar_laudo_html


def gerar_laudo_pdf(
    espolio: Espolio,
    caminho_saida: str,
    analise_ia: Optional[str] = None,
) -> str:
    """
    Gera o laudo em PDF A4 e salva em caminho_saida.

    Usa Playwright (Chromium headless) para renderizar o HTML com
    fidelidade total: gradientes, fontes, cores e layout do design system.
    Retorna o caminho do arquivo gerado.
    """
    from playwright.sync_api import sync_playwright

    html_str = gerar_laudo_html(espolio, analise_ia=analise_ia, tema="light")

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.set_content(html_str, wait_until="networkidle")
        page.pdf(
            path=caminho_saida,
            format="A4",
            print_background=True,   # imprime gradientes e fundos coloridos
            margin={"top": "20mm", "right": "18mm",
                    "bottom": "22mm", "left": "18mm"},
        )
        browser.close()

    return caminho_saida
