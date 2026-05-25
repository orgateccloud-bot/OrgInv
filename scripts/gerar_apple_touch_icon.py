# -*- coding: utf-8 -*-
"""
Gera apple-touch-icon.png (180x180) e icon-192.png (192x192)
a partir de frontend/public/logo.png — emblema sobre fundo navy
arredondado, no estilo "badge" Orgatec.
"""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SRC  = ROOT / "frontend" / "public" / "logo.png"
PUBLIC = ROOT / "frontend" / "public"

# Cor de fundo: navy profundo do gradient do header (#0E1A3A)
BG = (14, 26, 58, 255)
RADIUS_RATIO = 0.22   # iOS suaviza isso, mas mantemos um leve canto


def gerar(size: int, nome: str, padding_ratio: float = 0.18) -> Path:
    emblema = Image.open(SRC).convert("RGBA")
    # quadrado base
    base = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    # máscara de quadrado arredondado
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    radius = int(size * RADIUS_RATIO)
    d.rounded_rectangle((0, 0, size, size), radius=radius, fill=255)

    # camada de fundo navy
    bg_layer = Image.new("RGBA", (size, size), BG)
    base = Image.composite(bg_layer, base, mask)

    # encaixa o emblema com padding
    pad = int(size * padding_ratio)
    box = size - 2 * pad
    emb_resized = emblema.copy()
    # mantém proporção
    ew, eh = emb_resized.size
    ratio = min(box / ew, box / eh)
    emb_resized = emb_resized.resize(
        (int(ew * ratio), int(eh * ratio)),
        Image.LANCZOS,
    )
    nw, nh = emb_resized.size
    pos = ((size - nw) // 2, (size - nh) // 2)
    base.paste(emb_resized, pos, emb_resized)

    saida = PUBLIC / nome
    base.save(saida, "PNG", optimize=True)
    return saida


if __name__ == "__main__":
    paths = [
        gerar(180, "apple-touch-icon.png"),    # iOS padrão
        gerar(192, "icon-192.png"),            # PWA padrão
        gerar(512, "icon-512.png"),            # PWA splash
        gerar(32,  "favicon-32.png", 0.15),    # favicon
    ]
    for p in paths:
        print(f"  ✓ {p.relative_to(ROOT)}")
