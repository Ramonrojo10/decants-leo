#!/usr/bin/env python3
"""Split one front-on GMT watch photo into stackable transparent layers.

usage: leo_gmt_split.py INPUT.jpg OUTDIR [--cx N --cy N --rin N --rout N]

All layers share one 1000x2000 canvas, dial center at (500,1000),
scale: bezel outer diameter = 40 mm with 1000 px = 48 mm.
Stack order: bracelet -> case -> dial -> bezel.
Needs numpy, opencv-python-headless, pillow.
"""
import sys, argparse, os
import numpy as np, cv2

W, H, CX, CY = 1000, 2000, 500, 1000
MM = 1000 / 48
BEZEL_MM = 40
OVERLAP = 3  # px (source) layers overlap under the layer above (same pixels, hides seams)


def fit_circle(P):
    A = np.c_[2 * P[:, 0], 2 * P[:, 1], np.ones(len(P))]
    s = np.linalg.lstsq(A, (P ** 2).sum(1), rcond=None)[0]
    return s[0], s[1], np.sqrt(s[2] + s[0] ** 2 + s[1] ** 2)


def detect(im):
    """Fit the red-bezel outer circle (works for coke/pepsi-like red bezels);
    use --cx/--cy/--rin/--rout for other colours."""
    b, g, r = [im[..., i].astype(int) for i in range(3)]
    red = (r - g > 70) & (r - b > 60)
    ys, xs = np.nonzero(red)
    cx, cy = xs.mean(), ys.mean()
    for _ in range(3):
        ang = np.arctan2(ys - cy, xs - cx); d = np.hypot(xs - cx, ys - cy)
        bins = ((ang + np.pi) / (2 * np.pi) * 360).astype(int) % 360
        P = []
        for k in range(360):
            m = bins == k
            if m.sum() > 5:
                dd = np.percentile(d[m], 99); a = (k + .5) / 360 * 2 * np.pi - np.pi
                P.append([cx + dd * np.cos(a), cy + dd * np.sin(a)])
        cx, cy, ro = fit_circle(np.array(P))
    # inner red edge: min radius of red per angle, ignoring pixels near centre (red GMT hand)
    d = np.hypot(xs - cx, ys - cy); ang = np.degrees(np.arctan2(ys - cy, xs - cx)) % 360
    ins = []
    for a in range(0, 360, 5):
        m = (abs(ang - a) < 2) & (d > 0.6 * ro)
        if m.sum() > 20: ins.append(np.percentile(d[m], 0.5))
    rin = float(np.median(ins))
    return cx, cy, rin, ro


def silhouette(im):
    bg = np.median(np.concatenate([im[:8].reshape(-1, 3), im[-8:].reshape(-1, 3)]), 0)
    dist = np.abs(im.astype(int) - bg).max(2)
    cand = (dist <= 12).astype(np.uint8)
    n, lab = cv2.connectedComponents(cand, connectivity=4)
    border = set(lab[0]) | set(lab[-1]) | set(lab[:, 0]) | set(lab[:, -1])
    border.discard(0)
    bgm = np.isin(lab, list(border))
    fg = (~bgm).astype(np.uint8)
    # fill holes (inner regions never touching border)
    n, lab = cv2.connectedComponents(1 - fg, connectivity=4)
    bl = (set(lab[0]) | set(lab[-1]) | set(lab[:, 0]) | set(lab[:, -1])) - {0}
    fg = (~np.isin(lab, list(bl))).astype(np.uint8)
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    return fg.astype(np.float32)


def feather(m, s=0.8):
    return np.clip(cv2.GaussianBlur(m, (0, 0), s), 0, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp"); ap.add_argument("out")
    ap.add_argument("--cx", type=float); ap.add_argument("--cy", type=float)
    ap.add_argument("--rin", type=float); ap.add_argument("--rout", type=float)
    ap.add_argument("--rout-extra", type=float, default=21.0,
                    help="px beyond red edge to include steel bezel teeth")
    ap.add_argument("--rin-margin", type=float, default=-2.0)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    im = cv2.imread(a.inp); h, w = im.shape[:2]
    cx, cy, rin, ro_red = detect(im)
    if a.cx is not None: cx = a.cx
    if a.cy is not None: cy = a.cy
    if a.rin is not None: rin = a.rin
    rout = a.rout if a.rout is not None else ro_red + a.rout_extra
    rin += a.rin_margin
    print(f"center=({cx:.1f},{cy:.1f}) red_outer={ro_red:.1f} bezel_outer={rout:.1f} dial_r={rin:.1f}")

    sil = silhouette(im)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rr = np.hypot(xx - cx, yy - cy)
    # lug line: rows where silhouette is much wider than the bracelet
    widths = sil.sum(1)
    bw = np.median(widths[: int(cy - rout - 40)][widths[: int(cy - rout - 40)] > 0]) if cy - rout > 60 else widths.min()
    wide = np.nonzero(widths > bw * 1.25)[0]
    yt, yb = int(wide.min()), int(wide.max())
    print(f"bracelet width~{bw:.0f}px, lug rows top={yt} bottom={yb}")

    rows = yy
    top_or_bot = ((rows < yt + OVERLAP) | (rows > yb - OVERLAP)).astype(np.float32)
    case_rows = ((rows >= yt) & (rows <= yb)).astype(np.float32)
    A = {}
    A["bracelet"] = feather(sil * top_or_bot, 0.7) * sil
    hole = (rr < rout - OVERLAP).astype(np.float32)
    A["case"] = feather(sil * case_rows * (1 - hole), 0.7) * sil
    ring = ((rr <= rout) & (rr >= rin)).astype(np.float32)
    A["bezel"] = feather(ring, 0.8)
    A["dial"] = feather((rr <= rin + OVERLAP).astype(np.float32), 0.8)

    s = BEZEL_MM * MM / (2 * rout)
    M = np.float32([[s, 0, CX - s * cx], [0, s, CY - s * cy]])
    print(f"scale={s:.4f}  canvas={W}x{H}  dial center=({CX},{CY})  bezel d={2*rout*s:.0f}px dial r={rin*s:.0f}px")
    col = cv2.warpAffine(im, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    layers = {}
    for k in ["bracelet", "case", "dial", "bezel"]:
        al = cv2.warpAffine(A[k], M, (W, H), flags=cv2.INTER_LINEAR)
        rgba = np.dstack([col, (np.clip(al, 0, 1) * 255).round().astype(np.uint8)])
        layers[k] = rgba
        cv2.imwrite(os.path.join(a.out, k + ".png"), rgba)

    # stack
    acc = np.zeros((H, W, 3), np.float32); aa = np.zeros((H, W), np.float32)
    for k in ["bracelet", "case", "dial", "bezel"]:
        L = layers[k].astype(np.float32); al = L[..., 3] / 255
        acc = L[..., :3] * al[..., None] + acc * (1 - al[..., None])
        # premultiplied-style over: keep acc as color-over (works since opaque colors same photo)
        aa = al + aa * (1 - al)
    # color accumulation above is not premultiplied-correct for partial alpha; redo properly
    pc = np.zeros((H, W, 3), np.float32); pa = np.zeros((H, W), np.float32)
    for k in ["bracelet", "case", "dial", "bezel"]:
        L = layers[k].astype(np.float32); al = L[..., 3:] / 255
        pc = L[..., :3] * al + pc * (1 - al); pa = al[..., 0] + pa * (1 - al[..., 0])
    stack = np.dstack([pc / np.maximum(pa, 1e-6)[..., None], pa * 255]).clip(0, 255).astype(np.uint8)
    # un-premultiply: pc is premultiplied-by-construction (pc = c*a + pc*(1-a)) -> divide by pa
    cv2.imwrite(os.path.join(a.out, "stack.png"), stack)

    # preview
    bgc = np.median(np.concatenate([im[:8].reshape(-1, 3), im[-8:].reshape(-1, 3)]), 0).astype(np.float32)
    def on_bg(rgba, bgcol):
        al = rgba[..., 3:].astype(np.float32) / 255
        return (rgba[..., :3] * al + bgcol * (1 - al)).astype(np.uint8)
    def checker(rgba, sz=16):
        g = (np.indices(rgba.shape[:2]).sum(0) // sz) % 2
        c = np.where(g[..., None] == 0, 200, 150).astype(np.float32) * np.ones(3, np.float32)
        al = rgba[..., 3:].astype(np.float32) / 255
        return (rgba[..., :3] * al + c * (1 - al)).astype(np.uint8)
    # crop canvas rows to content, same crop for all: y 1000-700..1000+780
    y0, y1, x0, x1 = 280, 1800, 0, 1000
    th = 700
    def fit(img, hh=th):
        sc = hh / img.shape[0]; return cv2.resize(img, (int(img.shape[1] * sc), hh), interpolation=cv2.INTER_AREA)
    top = np.hstack([fit(im), fit(on_bg(stack, bgc)[y0:y1, x0:x1])])
    row2 = np.hstack([fit(checker(layers[k])[y0:y1, x0:x1], 520) for k in ["bracelet", "case", "dial", "bezel"]])
    Wp = max(top.shape[1], row2.shape[1])
    pad = lambda x: np.hstack([x, np.full((x.shape[0], Wp - x.shape[1], 3), 255, np.uint8)])
    cv2.imwrite(os.path.join(a.out, "preview.jpg"), np.vstack([pad(top), pad(row2)]), [cv2.IMWRITE_JPEG_QUALITY, 92])
    # diff vs original (stack warped original vs stack)
    ref = on_bg(np.dstack([col, (cv2.warpAffine(sil, M, (W, H)) * 255).astype(np.uint8)]), bgc)
    d = np.abs(on_bg(stack, bgc).astype(int) - ref.astype(int)).max(2)
    print(f"stack vs original (inside silhouette): mean diff={d.mean():.3f}, px>20: {(d>20).sum()}")

main()
