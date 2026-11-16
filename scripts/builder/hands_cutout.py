"""Recorta manecillas sobre fondo blanco conservando los agujeros del eje.

El fondo es el blanco conectado al borde; además, las zonas blancas pequeñas
y encerradas (los agujeros de los tubos) también se vuelven transparentes.
Las zonas blancas grandes encerradas (lume) se conservan.
Uso: hands_cutout.py <in> <out> archivos...
"""

import sys
from collections import deque

import numpy as np
from PIL import Image, ImageFilter

SRC, OUT, *names = sys.argv[1:]


def components(mask):
    h, w = mask.shape
    lab = np.zeros((h, w), dtype=np.int32)
    n = 0
    for y, x in zip(*np.nonzero(mask)):
        if lab[y, x]:
            continue
        n += 1
        q = deque([(y, x)])
        lab[y, x] = n
        while q:
            cy, cx = q.popleft()
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = cy + dy, cx + dx
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not lab[ny, nx]:
                    lab[ny, nx] = n
                    q.append((ny, nx))
    return lab, n


for name in names:
    img = Image.open(f"{SRC}/{name}.png").convert("RGB")
    small = img.resize((img.width // 2, img.height // 2))
    a = np.array(small).astype(int)
    white = (a.min(axis=2) > 236) & ((a.max(axis=2) - a.min(axis=2)) < 16)
    lab, n = components(white)
    h, w = white.shape
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    transparent = np.isin(lab, list(border))
    sizes = np.bincount(lab.ravel())
    for i in range(1, n + 1):
        if i not in border and sizes[i] < 2500:  # agujero del eje
            transparent |= lab == i
    mask = Image.fromarray(((~transparent) * 255).astype(np.uint8))
    mask = mask.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.0)).resize(img.size, Image.LANCZOS)
    out = img.convert("RGBA")
    out.putalpha(mask)
    out.save(f"{OUT}/{name}.png")
    print("ok", name)
