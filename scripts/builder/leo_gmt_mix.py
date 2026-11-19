#!/usr/bin/env python3
"""Make mezclas.jpg, catalogo.jpg and partes.json from the output of leo_gmt_batch.py.

usage: leo_gmt_mix.py PARTES_DIR RAW_DIR
RAW_DIR = layers produced with leo_gmt_batch.py --raw-out (no realism pass) for comparison.
"""
import sys, os, json
import numpy as np, cv2
from PIL import Image, ImageDraw

P, RAW = sys.argv[1], sys.argv[2]
W, H = 1000, 2000
det = json.load(open(os.path.join(P, "detection.json")))
ids = sorted(det)
rd = lambda p: cv2.imread(p, cv2.IMREAD_UNCHANGED)


def over(base, top):
    """base, top: float32 HxWx4 straight-alpha (0..255). returns straight-alpha over."""
    ab, at = base[..., 3:] / 255, top[..., 3:] / 255
    ao = at + ab * (1 - at)
    c = (top[..., :3] * at + base[..., :3] * ab * (1 - at)) / np.maximum(ao, 1e-6)
    return np.concatenate([c, ao * 255], 2)


def layer(root, pid, k):
    return rd(os.path.join(root, pid, k + ".png")).astype(np.float32)


def build(c, d, z, b, real):
    root = P if real else RAW
    acc = layer(root, b, "bracelet")
    case = layer(root, c, "case")
    acc = over(acc, case)
    if real:
        sb = rd(os.path.join(P, "shadow-bezel.png")).astype(np.float32)
        sb[..., 3] *= acc[..., 3] / 255        # contact shadow only where there is metal
        acc = over(acc, sb)
    acc = over(acc, layer(root, d, "dial"))
    if real:
        acc = over(acc, rd(os.path.join(P, "shadow-dial.png")).astype(np.float32))
    acc = over(acc, layer(root, z, "bezel"))
    return acc


def flat(a, bg=(236, 236, 236)):
    al = a[..., 3:] / 255
    return (a[..., :3] * al + np.float32(bg[::-1]) * (1 - al)).clip(0, 255).astype(np.uint8)


def label(img, text, h=34):
    pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)); d = ImageDraw.Draw(pil)
    d.text((8, 4), text, fill=(20, 20, 20))
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


def strip(w, text, h=34):
    return label(np.full((h, w, 3), 236, np.uint8), text)


COMBOS = [("gmt-02", "gmt-01", "gmt-08", "gmt-05"),
          ("gmt-07", "gmt-03", "gmt-02", "gmt-11"),
          ("gmt-05", "gmt-04", "gmt-09", "gmt-01"),
          ("gmt-11", "gmt-05", "gmt-03", "gmt-08")]
cells = []
y0, y1, x0, x1 = 150, 1850, 100, 900
for c, d, z, b in COMBOS:
    pair = []
    for real in (True, False):
        im = flat(build(c, d, z, b, real))[y0:y1, x0:x1]
        pair.append(cv2.resize(im, (480, 1020), interpolation=cv2.INTER_AREA))
    row = np.hstack(pair)
    txt = f"caja {c[4:]} / esfera {d[4:]} / bisel {z[4:]} / brazalete {b[4:]}"
    cells.append(np.vstack([strip(960, txt), strip(960, "con ajuste + sombras                    |  sin ajuste (crudo)"), row]))
grid = np.vstack([np.hstack(cells[:2]), np.hstack(cells[2:])])
cv2.imwrite(os.path.join(P, "mezclas.jpg"), grid, [cv2.IMWRITE_JPEG_QUALITY, 92])

# catalogue
def thumb(pid, k):
    a = layer(P, pid, k)
    if k in ("bezel", "dial"):
        a = a[1000 - 430:1000 + 430, 500 - 430:500 + 430]; s = 220 / 860
    else:
        a = a[150:1850, 100:900]; s = 220 / 800
    f = flat(a, (210, 214, 208))
    f = cv2.resize(f, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    return label(f, pid)

rows = []
for k, name in (("bezel", "BISELES"), ("dial", "ESFERAS (con manecillas)"), ("case", "CAJAS"), ("bracelet", "BRAZALETES")):
    ts = [thumb(p, k) for p in ids]
    hh = max(t.shape[0] for t in ts)
    ts = [np.pad(t, ((0, hh - t.shape[0]), (4, 4), (0, 0)), constant_values=236) for t in ts]
    rows.append(strip(sum(t.shape[1] for t in ts), name, 30)); rows.append(np.hstack(ts))
wmax = max(r.shape[1] for r in rows)
rows = [np.pad(r, ((0, 0), (0, wmax - r.shape[1]), (0, 0)), constant_values=236) for r in rows]
cv2.imwrite(os.path.join(P, "catalogo.jpg"), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 90])

parts = []
for pid in ids:
    dd = det[pid]
    for k in ("bezel", "dial", "case", "bracelet"):
        parts.append(dict(id=f"{pid}-{k}", type=k, sourcePhoto=f"gmt/originales/{dd['source']}",
                          file=f"{pid}/{k}.png", name="",
                          lowRes=bool(dd["upscaled"]), upscale=dd["scale"],
                          steelMatched=dd["steel_matched"]))
json.dump(dict(canvas=dict(width=W, height=H, dialCenter=[500, 1000], pxPerMm=1000 / 48, bezelOuterMm=40),
               stackOrder=["bracelet", "case", "shadow-bezel", "dial", "shadow-dial", "bezel"],
               shadows=dict(bezel="shadow-bezel.png", dial="shadow-dial.png"),
               note="lowRes = source photo upscaled more than 1.35x to reach the common scale",
               parts=parts), open(os.path.join(P, "partes.json"), "w"), indent=1, ensure_ascii=False)
print(len(parts), "parts")
