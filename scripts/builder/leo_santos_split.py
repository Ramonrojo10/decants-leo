#!/usr/bin/env python3
"""Split Leo's Santos-style watch photos into builder layers.

Input : fotos-leo/santos/originales/*.webp and fotos-leo/santos/enderezadas/*.png
        (front-facing studio photos on white; hands stay in the dial layer)
Output: fotos-leo/santos/partes/<santos-NN>/{strap,case,dial}.png
        fotos-leo/santos/partes/shadow-dial.png
        fotos-leo/santos/partes/{catalogo,mezclas}.jpg   (review sheets)
        public/builder/leo/santos/{case,dial,strap}-<id>.webp + shadowdial.webp

Common canvas 1000x2000 RGBA, 1000 px = 48 mm, dial window centred at (500,1000).
Every photo is warped so that
  * its dial window (outer edge of the bevel lip, annotated by hand in WIN) lands on one
    canonical 540x540 square,
  * the seam where the case lug block meets the first bracelet link / leather strap lands
    on common rows (CT / CB) and the strap width equals the common lug width.
Layers: strap / dial / shadowdial / case, stacked in that order.
 - case : case + bezel + crown, canonical opening and the strap zones transparent
 - dial : the window content cut with the canonical rounded square, a few px larger
          than the opening so it tucks under the case (no gap)
 - strap: everything beyond the seams, faded at both ends

Run:  python scripts/builder/leo_santos_split.py [export|sheets|all]
"""
import glob
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRCD = os.path.join(ROOT, "fotos-leo", "santos")
OUT = os.path.join(SRCD, "partes")
WEB = os.path.join(ROOT, "public", "builder", "leo", "santos")
Q = 85
CW, CH = 1000, 2000
CX, CY = 500, 1000
WIN_W = 540.0                       # canonical window (bevel lip outer edge), square
WT, WB = CY - WIN_W / 2, CY + WIN_W / 2
OPEN_IN = 14.0                      # case opening = window shrunk by this (keeps the lip)
DIAL_IN = 6.0                       # dial cut = window shrunk by this (tucks under the lip)
BAND_TOP, BAND_BOT = 85, 108        # depth of the strap band between the lug horns
EROSION = {'16': 3, '14': 3}       # source-edge erosion (px): dark PVD parts show white fringes
CORNER = 0.12                       # corner radius / window width

# which folder each photo comes from
KIND = {"01": "e", "02": "o", "03": "e", "04": "o", "05": "o", "07": "o", "08": "o", "09": "e",
        "10": "e", "11": "o", "12": "e", "13": "e", "14": "e", "15": "e", "16": "o"}
# dial window (bevel lip outer edge) in source pixels: left, top, right, bottom (hand annotated)
WIN = {
    '01': (390, 539, 1044, 1197), '02': (245, 236, 536, 525), '03': (398, 537, 1058, 1199),
    '04': (304, 308, 687, 684), '05': (214, 326, 551, 664), '07': (191, 309, 567, 682),
    '08': (210, 284, 560, 646), '09': (395, 527, 1048, 1160), '10': (432, 657, 997, 1140),
    '11': (208, 305, 556, 648), '12': (393, 559, 1044, 1208), '13': (342, 563, 1043, 1216),
    '14': (384, 557, 1059, 1229), '15': (304, 517, 1064, 1247), '16': (203, 306, 563, 658),
}

CASE_IDS = ["08", "05", "12", "16"]
DIAL_IDS = ["08", "02", "01", "11", "10", "15", "09", "13", "16", "07", "03", "14", "04", "05"]
STRAP_IDS = ["08", "16", "09", "12", "15"]


def src_path(i):
    d = "enderezadas" if KIND[i] == "e" else "originales"
    return glob.glob(os.path.join(SRCD, d, f"santos-{i}-*"))[0]


# ----------------------------------------------------------------------------- mask
def fg_mask(rgb):
    """Hard foreground mask: flood fill of 'smooth near-white' from the borders."""
    f = rgb.astype(np.float32)
    lum = f.mean(2)
    sat = f.max(2) - f.min(2)
    g = cv2.GaussianBlur(lum, (0, 0), 1.5)
    grad = np.hypot(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1)) / 8
    cand = ((lum >= 206) & (sat < 14) & (grad < 5)).astype(np.uint8)
    n, lab = cv2.connectedComponents(cand, connectivity=4)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    fg = (~np.isin(lab, list(border))).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(fg)
    fg = (lab == 1 + np.argmax(st[1:, 4])).astype(np.uint8)
    cnt, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = np.zeros_like(fg)
    cv2.drawContours(out, cnt, -1, 1, -1)
    return out


def extend_colors(rgb, valid, iters):
    img = rgb.astype(np.float32)
    v = valid.astype(np.float32)
    acc = img * v[..., None]
    w = v.copy()
    for _ in range(iters):
        a = cv2.blur(acc, (3, 3))
        b = cv2.blur(w, (3, 3))
        new = a / np.maximum(b, 1e-6)[..., None]
        fill = (w < 0.5) & (b > 1e-6)
        img = np.where(fill[..., None], new, img)
        w = np.where(fill, 1.0, w)
        acc = img * w[..., None]
    return img


# ----------------------------------------------------------------------------- measures
def find_cuts(m, win):
    """Seam rows = where the case outline flares out from the strap/lug block
    (largest jump of the silhouette width above / below the window)."""
    l, t, r, b = win
    H = b - t
    x0 = max(0, int(l - 0.5 * (r - l)))
    x1 = int(r + 0.02 * (r - l))
    wid = np.zeros(m.shape[0], np.float32)
    for y in range(m.shape[0]):
        xs = np.where(m[y, x0:x1])[0]
        wid[y] = (xs[-1] - xs[0] + 1) if len(xs) else 0
    wid = cv2.GaussianBlur(wid[:, None], (1, 0), sigmaX=0.1, sigmaY=2.0)[:, 0]
    d = np.gradient(wid)
    thr_hi = 0.005 * (r - l)            # px/row: steep = shoulder
    thr_lo = 0.0018 * (r - l)           # px/row: back to the (nearly straight) strap
    res = []
    for sgn in (-1, 1):
        y = int((t if sgn < 0 else b) + sgn * 0.02 * H)
        seen = False
        while 5 < y < len(wid) - 6:
            g = -sgn * d[y]             # positive = widening towards the window
            if g > thr_hi:
                seen = True
            elif seen and g < thr_lo:
                break
            y += sgn
        res.append(y)
    return res  # [top, bottom]


def row_extent(m, y0, y1):
    ws, cs = [], []
    for y in range(max(0, y0), min(m.shape[0], y1)):
        xs = np.where(m[y])[0]
        if len(xs):
            ws.append(xs[-1] - xs[0] + 1)
            cs.append((xs[-1] + xs[0]) / 2)
    return (float(np.median(ws)), float(np.median(cs))) if ws else (0.0, 0.0)


def analyse(i):
    rgb = np.array(Image.open(src_path(i)).convert("RGB"))
    m = fg_mask(rgb)
    win = WIN[i]
    ct, cb = find_cuts(m, win)
    wt_, ct_c = row_extent(m, ct - 35, ct - 15)
    wb_, cb_c = row_extent(m, cb + 15, cb + 35)
    return dict(id=i, rgb=rgb, m=m, win=win, ct=ct, cb=cb, lug=(wt_ + wb_) / 2, ctc=ct_c, cbc=cb_c)


# ----------------------------------------------------------------------------- warp
def rrect(shape, cx, cy, half, rad, ss=4):
    """Anti-aliased rounded square (float 0..1)."""
    h, w = shape
    im = Image.new("L", (w * ss, h * ss), 0)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([(cx - half) * ss, (cy - half) * ss, (cx + half) * ss - 1, (cy + half) * ss - 1],
                        radius=rad * ss, fill=255)
    im = im.resize((w, h), Image.LANCZOS)
    return np.asarray(im, np.float32) / 255.0


def build_maps(a, canon):
    """Inverse maps canvas -> source for one photo."""
    l, t, r, b = a["win"]
    wcx = (l + r) / 2
    sxw = WIN_W / (r - l)
    ss = canon["lug"] / a["lug"]
    CT, CB = canon["CT"], canon["CB"]
    Y = np.arange(CH, dtype=np.float32)
    y_src = np.empty(CH, np.float32)
    hs = np.empty(CH, np.float32)
    xc = np.empty(CH, np.float32)
    for k, yy in enumerate(Y):
        if yy < CT:
            y_src[k] = a["ct"] - (CT - yy) / ss
            hs[k], xc[k] = ss, a["ctc"]
        elif yy < WT:
            u = (yy - CT) / (WT - CT)
            y_src[k] = a["ct"] + u * (t - a["ct"])
            hs[k] = ss + u * (sxw - ss)
            xc[k] = a["ctc"] + u * (wcx - a["ctc"])
        elif yy <= WB:
            u = (yy - WT) / (WB - WT)
            y_src[k] = t + u * (b - t)
            hs[k], xc[k] = sxw, wcx
        elif yy < CB:
            u = (yy - WB) / (CB - WB)
            y_src[k] = b + u * (a["cb"] - b)
            hs[k] = sxw + u * (ss - sxw)
            xc[k] = wcx + u * (a["cbc"] - wcx)
        else:
            y_src[k] = a["cb"] + (yy - CB) / ss
            hs[k], xc[k] = ss, a["cbc"]
    X = np.arange(CW, dtype=np.float32)
    mapx = xc[:, None] + (X[None, :] - CX) / hs[:, None]
    mapy = np.repeat(y_src[:, None], CW, 1)
    return mapx.astype(np.float32), mapy.astype(np.float32), ss


def warp(img, mx, my, interp=cv2.INTER_CUBIC):
    return cv2.remap(img, mx, my, interp, borderMode=cv2.BORDER_REPLICATE)


def ramp(v, a, b):
    return np.clip((v - a) / (b - a), 0, 1)


def make_layers(a, canon):
    mx, my, ss = build_maps(a, canon)
    rgb = warp(a["rgb"], mx, my)
    # soft alpha of the whole watch (slightly eroded so no white fringe survives)
    hard = cv2.erode(a["m"], np.ones((3, 3), np.uint8), iterations=EROSION.get(a['id'], 2))
    al = warp(cv2.GaussianBlur(hard.astype(np.float32), (0, 0), 0.8), mx, my, cv2.INTER_LINEAR)
    al = np.clip((al - 0.55) / 0.3, 0, 1)
    valid = (al > 0.98).astype(np.uint8)
    col = extend_colors(rgb, cv2.erode(valid, np.ones((3, 3), np.uint8)), 6)
    col = np.clip(col, 0, 255)
    # mild sharpening (sources are upscaled or shrunk)
    bl = cv2.GaussianBlur(col, (0, 0), 1.3)
    col = np.clip(col + 0.4 * (col - bl), 0, 255)

    yy = np.arange(CH, dtype=np.float32)[:, None]
    CT, CB = canon["CT"], canon["CB"]
    half_open = WIN_W / 2 - OPEN_IN
    half_dial = WIN_W / 2 - DIAL_IN
    opening = rrect((CH, CW), CX, CY, half_open, half_open * 2 * CORNER)
    dialcut = rrect((CH, CW), CX, CY, half_dial, half_dial * 2 * CORNER)

    zone_case = ramp(yy, CT - 0.5, CT + 0.5) * (1 - ramp(yy, CB - 0.5, CB + 0.5))
    # between the lug horns the strap runs on up to the bezel (leather photos show it there):
    # that central band belongs to the strap layer, not to the case layer
    xx = np.arange(CW, dtype=np.float32)[None, :]
    lw = canon["lug"] / 2
    band_w = 1 - ramp(np.abs(xx - CX), lw - 2, lw - 1)
    rows_b = (ramp(yy, CT - 0.5, CT + 0.5) * (1 - ramp(yy, CT + BAND_TOP, CT + BAND_TOP + 1))
              + ramp(yy, CB - BAND_BOT - 1, CB - BAND_BOT) * (1 - ramp(yy, CB - 0.5, CB + 0.5)))
    case_a = al * zone_case * (1 - opening) * (1 - np.clip(rows_b * band_w, 0, 1))
    # strap goes a little under the case, and fills the central band
    zone_strap = 1 - ramp(yy, CT - 0.5, CT + 0.5) * (1 - ramp(yy, CB - 0.5, CB + 0.5))
    band_s = 1 - ramp(np.abs(xx - CX), lw + 3, lw + 4)
    rows_s = (ramp(yy, CT - 0.5, CT + 0.5) * (1 - ramp(yy, CT + BAND_TOP + 2, CT + BAND_TOP + 3))
              + ramp(yy, CB - BAND_BOT - 3, CB - BAND_BOT - 2) * (1 - ramp(yy, CB - 0.5, CB + 0.5)))
    strap_a = al * np.maximum(zone_strap, np.clip(rows_s * band_s, 0, 1))
    # fade both ends of the strap (also guarantees it never reaches the canvas edge)
    rows = np.where(strap_a.max(1) > 0.5)[0]
    top_end, bot_end = rows[0], rows[-1]
    fade = 150.0
    f_top = ramp(yy, top_end, top_end + fade)
    f_bot = 1 - ramp(yy, bot_end - fade, bot_end)
    strap_a = strap_a * np.where(yy < CY, f_top, f_bot)
    dial_a = dialcut
    return col, case_a, strap_a, dial_a


def to_rgba(col, alpha):
    return Image.fromarray(np.dstack([col.astype(np.uint8), (np.clip(alpha, 0, 1) * 255 + 0.5).astype(np.uint8)]), "RGBA")


def shadow_layer():
    half_open = WIN_W / 2 - OPEN_IN
    ins = rrect((CH, CW), CX, CY, half_open + 2, (half_open + 2) * 2 * CORNER)
    outside = 1 - ins
    M = np.float32([[1, 0, 3], [0, 1, 6]])
    sh = cv2.warpAffine(outside, M, (CW, CH), borderValue=1)
    sh = cv2.GaussianBlur(sh, (0, 0), 8)
    near = cv2.GaussianBlur(outside, (0, 0), 3)
    a = np.clip(0.34 * sh * ins + 0.09 * near * ins, 0, 0.45)
    return Image.fromarray(np.dstack([np.zeros((CH, CW, 3), np.uint8), (a * 255).astype(np.uint8)]), "RGBA")


def stack(layers):
    base = Image.new("RGBA", (CW, CH), (255, 255, 255, 255))
    for im in layers:
        base.alpha_composite(im)
    return base


# ----------------------------------------------------------------------------- main
def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    A = {i: analyse(i) for i in KIND}
    # canonical lug width and cut rows from the median of all photos
    lug_ratio = np.median([a["lug"] / (a["win"][2] - a["win"][0]) for a in A.values()])
    dt = np.median([(a["win"][1] - a["ct"]) / (a["win"][3] - a["win"][1]) for a in A.values()])
    db = np.median([(a["cb"] - a["win"][3]) / (a["win"][3] - a["win"][1]) for a in A.values()])
    canon = dict(lug=lug_ratio * WIN_W, CT=WT - dt * WIN_W, CB=WB + db * WIN_W)
    print("canon", canon)
    for i, a in A.items():
        print(i, "cuts", a["ct"], a["cb"], "lug", round(a["lug"]), "ratio", round(a["lug"] / (a["win"][2] - a["win"][0]), 3),
              "dt", round((a["win"][1] - a["ct"]) / (a["win"][3] - a["win"][1]), 3),
              "db", round((a["cb"] - a["win"][3]) / (a["win"][3] - a["win"][1]), 3))
    os.makedirs(OUT, exist_ok=True)
    shadow = shadow_layer()
    shadow.save(os.path.join(OUT, "shadow-dial.png"))
    L = {}
    for i, a in A.items():
        col, case_a, strap_a, dial_a = make_layers(a, canon)
        L[i] = dict(case=to_rgba(col, case_a), strap=to_rgba(col, strap_a), dial=to_rgba(col, dial_a))
        d = os.path.join(OUT, f"santos-{i}")
        os.makedirs(d, exist_ok=True)
        for k, im in L[i].items():
            im.save(os.path.join(d, k + ".png"))
    if mode in ("export", "all"):
        os.makedirs(WEB, exist_ok=True)
        for i in CASE_IDS: L[i]["case"].save(os.path.join(WEB, f"case-santos-{i}.webp"), "WEBP", quality=Q, method=6)
        for i in DIAL_IDS: L[i]["dial"].save(os.path.join(WEB, f"dial-santos-{i}.webp"), "WEBP", quality=Q, method=6)
        for i in STRAP_IDS: L[i]["strap"].save(os.path.join(WEB, f"strap-santos-{i}.webp"), "WEBP", quality=Q, method=6)
        shadow.save(os.path.join(WEB, "shadowdial.webp"), "WEBP", quality=Q, method=6)
    if mode in ("sheets", "all"):
        sheets(L, shadow)
    print("ok")


MIXES = [
    ("16", "03", "09", "PVD + Time Is Money blanca + cuero azul"),
    ("12", "11", "08", "dorada + verde + brazalete acero"),
    ("05", "07", "12", "bisel negro + skeleton + cuero cafe"),
    ("08", "10", "16", "acero + roja + brazalete PVD"),
    ("08", "13", "15", "acero + arabe azul + cuero negro"),
    ("16", "16", "16", "PVD + arabe arena + brazalete PVD"),
    ("12", "01", "12", "dorada + guilloche + cuero cafe"),
    ("08", "04", "08", "acero + World Is Yours + acero"),
]


def sheets(L, shadow):
    def compose(c, d, s):
        return stack([L[s]["strap"], L[d]["dial"], shadow, L[c]["case"]])
    tiles = []
    for c, d, s, name in MIXES:
        im = compose(c, d, s).convert("RGB")
        im = im.crop((0, 200, 1000, 1800)).resize((375, 600), Image.LANCZOS)
        tiles.append(im)
    sh = Image.new("RGB", (375 * 4, 600 * 2), "white")
    for k, t in enumerate(tiles):
        sh.paste(t, ((k % 4) * 375, (k // 4) * 600))
    sh.save(os.path.join(OUT, "mezclas.jpg"), quality=90)
    # catalogue: every exported part on white (cases alone, dials alone, straps alone)
    cells = []
    for i in CASE_IDS: cells.append(("case " + i, stack([L[i]["case"]])))
    for i in DIAL_IDS: cells.append(("dial " + i, stack([L[i]["dial"], shadow])))
    for i in STRAP_IDS: cells.append(("strap " + i, stack([L[i]["strap"]])))
    from PIL import ImageFont
    cols = 8
    rows = (len(cells) + cols - 1) // cols
    cw, ch = 250, 500
    sh = Image.new("RGB", (cw * cols, ch * rows), "white")
    dr = ImageDraw.Draw(sh)
    for k, (name, im) in enumerate(cells):
        t = im.convert("RGB").crop((0, 200, 1000, 1800)).resize((cw - 6, int((cw - 6) * 1.6)), Image.LANCZOS)
        x, y = (k % cols) * cw, (k // cols) * ch
        sh.paste(t, (x + 3, y + 20))
        dr.text((x + 6, y + 4), name, fill=(200, 0, 0))
    sh.save(os.path.join(OUT, "catalogo.jpg"), quality=90)


if __name__ == "__main__":
    sys.exit(main())
