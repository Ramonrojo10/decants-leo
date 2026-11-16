"""Alinea correas planas (dos piezas lado a lado) como capa del armador.

La foto del proveedor trae la pieza de la hebilla a la izquierda y la de los
agujeros a la derecha, ambas con el extremo de la asa hacia arriba. Aquí:
  - la pieza de la hebilla se gira 180° y va arriba del reloj,
  - la pieza de los agujeros va abajo,
  - ambas se escalan a 22 mm de ancho y su extremo de asa queda escondido
    bajo la caja (a STRAP_END mm del centro).

Salida: <id>.webp, lienzo de 1000 x 2000 px (48 x 96 mm) para la vista normal,
y <id>-full.webp, lienzo de 1000 x 7000 px (48 x 336 mm) con la correa
completa para la vista alejada. Mismo eje que las demás capas.
Uso: strap_align.py <carpeta_recortes> <carpeta_salida> ids...
"""

import sys
from collections import deque

import numpy as np
from PIL import Image

SRC, OUT, *names = sys.argv[1:]
W, H = 1000, 2000
FULL_H = 7000
MM = W / 48.0
CX, CY = W / 2, H / 2
WIDTH_MM = 22.0
STRAP_END = 17.0  # mm desde el centro hasta el extremo de la asa


def pieces(alpha):
    small = alpha[::4, ::4] > 60
    h, w = small.shape
    lab = np.zeros((h, w), dtype=np.int32)
    n = 0
    for y, x in zip(*np.nonzero(small)):
        if lab[y, x]:
            continue
        n += 1
        q = deque([(y, x)])
        lab[y, x] = n
        while q:
            cy, cx = q.popleft()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < h and 0 <= nx < w and small[ny, nx] and not lab[ny, nx]:
                        lab[ny, nx] = n
                        q.append((ny, nx))
    sizes = sorted(((lab == i).sum(), i) for i in range(1, n + 1))[-2:]
    boxes = []
    for _, i in sizes:
        ys, xs = np.nonzero(lab == i)
        boxes.append((xs.min() * 4, ys.min() * 4, xs.max() * 4 + 4, ys.max() * 4 + 4))
    return sorted(boxes)  # izquierda (hebilla) primero


for name in names:
    img = Image.open(f"{SRC}/{name}.png").convert("RGBA")
    alpha = np.array(img)[:, :, 3]
    (bx0, by0, bx1, by1), (tx0, ty0, tx1, ty1) = pieces(alpha)
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    full = Image.new("RGBA", (W, FULL_H), (0, 0, 0, 0))
    for (x0, y0, x1, y1), top in (((bx0, by0, bx1, by1), True), ((tx0, ty0, tx1, ty1), False)):
        piece = img.crop((x0, y0, x1, y1))
        # ancho medido cerca del extremo de la asa (parte superior de la pieza)
        a = np.array(piece)[:, :, 3] > 60
        rows = a[int(a.shape[0] * 0.04) : int(a.shape[0] * 0.12)]
        width_px = np.median(rows.sum(axis=1))
        scale = WIDTH_MM * MM / width_px
        piece = piece.resize((round(piece.width * scale), round(piece.height * scale)), Image.LANCZOS)
        if top:
            piece = piece.rotate(180)
            y = CY - STRAP_END * MM - piece.height
        else:
            y = CY + STRAP_END * MM
        x = round(CX - piece.width / 2)
        canvas.alpha_composite(piece, (x, round(y)))
        full.alpha_composite(piece, (x, round(y + (FULL_H - H) / 2)))
    canvas.save(f"{OUT}/{name}.webp", "WEBP", quality=85, method=6)
    full.save(f"{OUT}/{name}-full.webp", "WEBP", quality=82, method=6)
    print("ok", name)
