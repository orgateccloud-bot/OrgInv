"""Captura screenshots da app para análise visual."""
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent
URL = "http://localhost:5180/"

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto(URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(1500)  # font/css settle

    # Full page
    page.screenshot(path=str(OUT / "shot_full.png"), full_page=True)
    print(f"shot_full.png saved")

    # Viewport
    page.screenshot(path=str(OUT / "shot_viewport.png"))
    print(f"shot_viewport.png saved")

    # Tab Espólio (1ª agora)
    try:
        page.click('button[role="tab"]:has-text("Espólio")', timeout=5000)
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / "shot_espolio.png"), full_page=True)
        print("shot_espolio.png saved")
    except Exception as e:
        print(f"Espólio click failed: {e}")

    # Tab Documentos
    try:
        page.click('button[role="tab"]:has-text("Documentos")', timeout=5000)
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / "shot_docs.png"), full_page=True)
        print("shot_docs.png saved")
    except Exception as e:
        print(f"Documentos click failed: {e}")

    # Tab Bens
    try:
        page.click('button[role="tab"]:has-text("Bens")', timeout=5000)
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / "shot_bens.png"), full_page=True)
        print("shot_bens.png saved")
    except Exception as e:
        print(f"Bens click failed: {e}")

    # Tab Apuração
    try:
        page.click('button[role="tab"]:has-text("Apuração")', timeout=5000)
        page.wait_for_timeout(800)
        page.screenshot(path=str(OUT / "shot_apuracao.png"), full_page=True)
        print("shot_apuracao.png saved")
    except Exception as e:
        print(f"Apuração click failed: {e}")

    # Tab Laudo
    try:
        page.click('button[role="tab"]:has-text("Laudo")', timeout=5000)
        page.wait_for_timeout(800)
        page.screenshot(path=str(OUT / "shot_laudo.png"), full_page=True)
        print("shot_laudo.png saved")
    except Exception as e:
        print(f"Laudo click failed: {e}")

    browser.close()
print("done")
