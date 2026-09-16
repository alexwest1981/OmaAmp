#!/usr/bin/env python3
"""Ritar OmaAmp-ikonen i 512, 256 och 128 px (8-bitars RGBA).

Kör: python3 ikon/gor-ikonen.py     (kräver Pillow)

Motivet är valt för att läsas i liststorlek: fem breda staplar, en enda gul
accent på mittenstapeln, cyan baslinje — och inga bokstäver. Hel fyrkant utan
rundning, skugga eller glöd, eftersom butiken och skrivbordet lägger på sin egen
mask. Färgerna kommer ur themes/classic_retro.json.

Ritas i 2048 px och skalas ned med Lanczos; det ger mjuka kanter utan att något
behöver kantutjämnas för hand. Ändra `heights` för en annan vågform.
"""
import os
from PIL import Image, ImageDraw

S = 2048                                    # ritytan
OUT = os.path.dirname(os.path.abspath(__file__))

TOP = (52, 54, 68)                          # #343644
BOTTOM = (24, 25, 31)                       # #18191f
GREEN = (0, 255, 51)                        # #00ff33 (lcd_text)
YELLOW = (255, 234, 0)                      # #ffea00 (vis_bars_mid)
CYAN = (0, 190, 216)                        # nedtonad #00e5ff (titlebar_text)

img = Image.new("RGB", (S, S), BOTTOM)
d = ImageDraw.Draw(img)
for y in range(S):
    t = y / (S - 1)
    d.line([(0, y), (S, y)], fill=tuple(int(TOP[i] + (BOTTOM[i] - TOP[i]) * t) for i in range(3)))

# Fem staplar: udda antal ger en centrerad accent, och fem läsbara former i 32 px.
heights = [0.34, 0.56, 0.88, 0.60, 0.38]
m = int(S * 0.155)                          # sidmarginal
base_y = int(S * 0.735)                     # staplarnas bas
top_y = int(S * 0.16)                       # högsta möjliga topp
n = len(heights)
gap = int(S * 0.045)
bw = int((S - 2 * m - gap * (n - 1)) / n)
usable = base_y - top_y
radius = int(bw * 0.24)

for i, h in enumerate(heights):
    x0 = m + i * (bw + gap)
    bh = int(usable * h)
    y0 = base_y - bh
    d.rounded_rectangle([x0, y0, x0 + bw, base_y], radius=radius, fill=GREEN)
    if h >= 0.8:
        # Gul topp: rundad överkant, fyrkantig underkant. Övergången mot det
        # gröna blir då en rak, skarvfri linje i stället för två rundade kanter
        # som möts (den skarven syntes tydligt i första versionen).
        cut = y0 + int(bh * 0.32)
        d.rounded_rectangle([x0, y0, x0 + bw, cut + radius], radius=radius, fill=YELLOW)
        d.rectangle([x0, cut, x0 + bw, cut + radius + 1], fill=YELLOW)

line_h = int(S * 0.032)
ly = int(S * 0.845)
d.rounded_rectangle([m, ly, S - m, ly + line_h], radius=int(line_h / 2), fill=CYAN)

base = img.convert("RGBA")
for tag, size in {"512": 512, "256": 256, "128": 128}.items():
    p = os.path.join(OUT, f"omaamp-{tag}.png")
    base.resize((size, size), Image.LANCZOS).save(p, "PNG", optimize=True)
    print(f"{os.path.basename(p)}: {size}×{size} · {os.path.getsize(p)} byte")
