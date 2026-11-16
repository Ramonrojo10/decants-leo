"""Quita el fondo blanco de fotos de producto: rellena desde el borde los
pixeles casi blancos y suaviza la orilla. Uso: local_cutout.py <in> <out> [archivos...]"""

import sys
from collections import deque

import numpy as np
from PIL import Image, ImageFilter

SRC, OUT, *names = sys.argv[1:]

for name in names:
    img = Image.open(f"{SRC}/{name}.png").convert("RGB")
    small = img.resize((img.width // 2, img.height // 2))
    a = np.array(small).astype(int)
    white = (a.min(axis=2) > 232) & ((a.max(axis=2) - a.min(axis=2)) < 14)
    h, w = white.shape
    bg = np.zeros_like(white)
    q = deque((y, x) for y in (0, h - 1) for x in range(w) if white[y, x])
    q.extend((y, x) for x in (0, w - 1) for y in range(h) if white[y, x])
    for y, x in q:
        bg[y, x] = True
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and white[ny, nx] and not bg[ny, nx]:
                bg[ny, nx] = True
                q.append((ny, nx))
    if name.startswith("insert"):
        # El anillo es un círculo: nada dentro del radio exterior es fondo,
        # salvo el hueco central (lo que queda dentro del radio interior).
        ys, xs = np.nonzero(~bg)
        cy, cx = (ys.min() + ys.max()) / 2, (xs.min() + xs.max()) / 2
        r_out = (xs.max() - xs.min()) / 2
        yy, xx = np.mgrid[0:h, 0:w]
        rr = np.hypot(yy - cy, xx - cx)
        ring_white = white & (rr < r_out - 1)
        hole = white & (rr < r_out * 0.83)
        bg = (bg & ~(rr < r_out - 1)) | hole
    # Agujeros interiores (centro de insertos): blancos encerrados grandes.
    inner = white & ~bg
    mask = Image.fromarray(((~bg) * 255).astype(np.uint8))
    mask = mask.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.2)).resize(img.size, Image.LANCZOS)
    out = img.convert("RGBA")
    out.putalpha(mask)
    out.save(f"{OUT}/{name}.png")
    print("ok", name)
