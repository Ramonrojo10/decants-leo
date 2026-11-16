"""Alinea en lote las piezas recortadas y las exporta como capas WebP del armador.

Uso: batch_align.py <parts-list.txt> <carpeta_recortes> <carpeta_salida>
Cada línea de parts-list: <id> <mm> <archivo-proveedor>. El tipo sale del
prefijo del id (case-, dial-, insert-, hands-).
"""

import sys
from collections import deque

import numpy as np
from PIL import Image

LIST, SRC, OUT = sys.argv[1:4]
CANVAS = 1000
MM = CANVAS / 48.0  # lienzo = 48 mm
C = CANVAS / 2
MINUTE_LEN = 12.4


def flood_outside(mask):
    h, w = mask.shape
    out = np.zeros_like(mask)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if not mask[y, x]:
                out[y, x] = True
                q.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if not mask[y, x] and not out[y, x]:
                out[y, x] = True
                q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not mask[ny, nx] and not out[ny, nx]:
                out[ny, nx] = True
                q.append((ny, nx))
    return out


def holes(mask):
    return ~mask & ~flood_outside(mask)


def bbox(mask):
    ys, xs = np.nonzero(mask)
    return xs.min(), ys.min(), xs.max(), ys.max()


def place(img, scale, center, rotate=0.0):
    w, h = img.size
    img = img.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)
    cx, cy = center[0] * scale, center[1] * scale
    if rotate:
        img = img.rotate(-rotate, resample=Image.BICUBIC, center=(cx, cy))
    canvas = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    canvas.alpha_composite(img, (round(C - cx), round(C - cy)))
    return canvas


def save(img, name):
    img.save(f"{OUT}/{name}.webp", "WEBP", quality=88, method=6)


def do_case(name, mm):
    img = Image.open(f"{SRC}/{name}.png").convert("RGBA")
    a = np.array(img)[:, :, 3] > 30
    small = a[::4, ::4]
    hl = holes(small)
    hy, hx = np.nonzero(hl)
    if len(hx) == 0:
        raise SystemExit(f"{name}: sin agujero central")
    center = (hx.mean() * 4 + 2, hy.mean() * 4 + 2)
    x0, _, _, _ = bbox(a)
    body = 2 * (center[0] - x0)
    save(place(img, mm * MM / body, center), name)


def do_round(name, mm):
    img = Image.open(f"{SRC}/{name}.png").convert("RGBA")
    a = np.array(img)[:, :, 3] > 30
    x0, y0, x1, y1 = bbox(a)
    save(place(img, mm * MM / (x1 - x0), ((x0 + x1) / 2, (y0 + y1) / 2)), name)


def do_hands(name):
    img = Image.open(f"{SRC}/{name}.png").convert("RGBA")
    arr = np.array(img)
    ink = arr[:, :, 3] > 40
    small = ink[::2, ::2]
    h, w = small.shape
    labels = np.zeros((h, w), dtype=np.int32)
    n = 0
    for y, x in zip(*np.nonzero(small)):
        if labels[y, x]:
            continue
        n += 1
        q = deque([(y, x)])
        labels[y, x] = n
        while q:
            cy, cx = q.popleft()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < h and 0 <= nx < w and small[ny, nx] and not labels[ny, nx]:
                        labels[ny, nx] = n
                        q.append((ny, nx))
    comps = sorted(((labels == i).sum(), i) for i in range(1, n + 1))[-3:]
    parts = []
    for _, i in comps:
        m = labels == i
        x0, y0, x1, y1 = bbox(m)
        sub = np.pad(m[y0 : y1 + 1, x0 : x1 + 1], 1)
        hl = holes(sub)[1:-1, 1:-1]
        ys, xs = np.nonzero(m)
        if hl.sum() > 0:
            py, px = np.nonzero(hl)
            pivot = ((px.mean() + x0) * 2, (py.mean() + y0) * 2)
        else:
            # sin agujero visible: el eje es el extremo más ancho
            pivot = None
        if pivot is None:
            continue
        d = np.hypot(xs * 2 - pivot[0], ys * 2 - pivot[1])
        k = d.argmax()
        tip = (xs[k] * 2, ys[k] * 2)
        length = float(np.hypot(tip[0] - pivot[0], tip[1] - pivot[1]))
        angle = float(np.degrees(np.arctan2(tip[0] - pivot[0], -(tip[1] - pivot[1]))))
        full = np.kron(m, np.ones((2, 2), dtype=bool))[: arr.shape[0], : arr.shape[1]]
        for _ in range(3):
            full[1:] |= full[:-1]
            full[:-1] |= full[1:]
            full[:, 1:] |= full[:, :-1]
            full[:, :-1] |= full[:, 1:]
        parts.append({"mask": full, "pivot": pivot, "length": length, "angle": angle})
    if len(parts) < 3:
        raise SystemExit(f"{name}: solo {len(parts)} manecillas detectadas")
    parts.sort(key=lambda p: p["length"])
    hour, minute, seconds = parts
    scale = MINUTE_LEN * MM / minute["length"]
    for part, target, suffix in ((hour, 305.0, "hour"), (minute, 60.0, "minute"), (seconds, 192.0, "seconds")):
        layer = arr.copy()
        layer[:, :, 3][~part["mask"]] = 0
        save(place(Image.fromarray(layer), scale, part["pivot"], target - part["angle"]), f"{name}-{suffix}")


for line in open(LIST):
    pid, mm, _ = line.split()
    try:
        if pid.startswith("case-"):
            do_case(pid, float(mm))
        elif pid.startswith(("dial-", "insert-")):
            do_round(pid, float(mm))
        elif pid.startswith("hands-"):
            do_hands(pid)
        print("ok", pid)
    except FileNotFoundError:
        print("falta", pid)
    except SystemExit as e:
        print("ERROR", e)
