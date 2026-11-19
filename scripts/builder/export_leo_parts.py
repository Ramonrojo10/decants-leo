#!/usr/bin/env python3
"""Exporta las piezas de Leo (GMT y Nautilus) a public/builder/leo/<clase>/<tipo>-<id>.webp.

Todas las capas conservan el lienzo de 1000x2000 px (1000 px = 48 mm, centro de
esfera en (500,1000)) para apilarse sin desplazamientos.
La sombra de contacto del bisel GMT se recorta al metal de cada caja
(shadow-bezel-<id>.webp), igual que en leo_gmt_mix.py.

uso: export_leo_parts.py [RAIZ_PROYECTO]
"""
import os, sys
import numpy as np
from PIL import Image

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "..")
SRC = os.path.join(ROOT, "fotos-leo")
OUT = os.path.join(ROOT, "public", "builder", "leo")
Q = 85

GMT_CASE = ["gmt-02", "gmt-05", "gmt-07"]
GMT_DIAL = ["gmt-01", "gmt-02", "gmt-03", "gmt-05", "gmt-08", "gmt-09", "gmt-10", "gmt-11"]
GMT_BEZEL = ["gmt-01", "gmt-02", "gmt-03", "gmt-04", "gmt-05", "gmt-08", "gmt-09", "gmt-11"]
GMT_BRACELET = ["gmt-01", "gmt-02", "gmt-05", "gmt-07", "gmt-08"]

# caja y brazalete de la misma foto encajan mejor en las asas
NAUT_CASE = ["naut-03", "naut-05", "naut-08"]
NAUT_DIAL = [f"naut-{i:02d}" for i in range(1, 20)]
NAUT_STRAP = ["naut-03", "naut-08", "naut-05", "naut-15", "naut-16", "naut-17"]


def save(img, cls, name):
    d = os.path.join(OUT, cls)
    os.makedirs(d, exist_ok=True)
    img.save(os.path.join(d, name + ".webp"), "WEBP", quality=Q, method=6)


def load(*p):
    im = Image.open(os.path.join(SRC, *p)).convert("RGBA")
    assert im.size == (1000, 2000), (p, im.size)
    return im


for i in GMT_CASE:
    save(load("gmt", "partes", i, "case.png"), "gmt", f"case-{i}")
    sb = np.array(load("gmt", "partes", "shadow-bezel.png"))
    ca = np.array(load("gmt", "partes", i, "case.png"))[..., 3]
    sb[..., 3] = (sb[..., 3].astype(np.float32) * ca / 255).astype(np.uint8)
    save(Image.fromarray(sb), "gmt", f"shadowbezel-{i}")
for i in GMT_DIAL: save(load("gmt", "partes", i, "dial.png"), "gmt", f"dial-{i}")
for i in GMT_BEZEL: save(load("gmt", "partes", i, "bezel.png"), "gmt", f"bezel-{i}")
for i in GMT_BRACELET: save(load("gmt", "partes", i, "bracelet.png"), "gmt", f"bracelet-{i}")
save(load("gmt", "partes", "shadow-dial.png"), "gmt", "shadowdial")

for i in NAUT_CASE: save(load("nautilus", "partes", i, "case.png"), "nautilus", f"case-{i}")
for i in NAUT_DIAL: save(load("nautilus", "partes", i, "dial.png"), "nautilus", f"dial-{i}")
for i in NAUT_STRAP: save(load("nautilus", "partes", i, "strap.png"), "nautilus", f"strap-{i}")
save(load("nautilus", "partes", "shadow-dial.png"), "nautilus", "shadowdial")
print("ok")
