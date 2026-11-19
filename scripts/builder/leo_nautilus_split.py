#!/usr/bin/env python3
"""Split Leo's Nautilus-style watch photos into builder layers.

Input : fotos-leo/nautilus/enderezadas/*  (19 front-facing studio photos on white)
Output: fotos-leo/nautilus/partes/<naut-NN>/{strap,case,dial,stack}.png
        fotos-leo/nautilus/partes/shadow-dial.png   (shared inner shadow)
        fotos-leo/nautilus/partes/partes.json
        fotos-leo/nautilus/partes/{catalogo,mezclas}.jpg

Common canvas 1000x2000 RGBA, 1000 px = 48 mm, dial centroid at (500,1000),
case width (flank to flank, crown excluded) = CASE_MM.

Pipeline
 1. white background removal (flood fill from borders, smooth-gradient criterion so the
    soft drop shadow is excluded) -> soft alpha
 2. dial opening: dynamic-programming contour on the polar edge map around a
    superellipse seed (rounded-square cushion)
 3. cut lines where the case lug block meets the first bracelet link / the leather strap
 4. every photo is warped to a COMMON dial contour and COMMON cut-line rows, so dials,
    cases and straps from different photos are interchangeable
 5. per-material exposure / white balance of the metal (steel -> neutral grey,
    rose -> common tone), mild unsharp mask
 6. split: strap (outside the cuts) / case (between cuts, dial opening transparent) /
    dial (+hands, extended a few px under the case) / stack (recomposite proof)

Run:  python scripts/builder/leo_nautilus_split.py
"""
import glob
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.join(ROOT, "fotos-leo", "nautilus", "enderezadas")
OUT = os.path.join(ROOT, "fotos-leo", "nautilus", "partes")

CW, CH = 1000, 2000
PX_PER_MM = 1000 / 48.0
CASE_MM = 41.0
CX0, CY0 = 500.0, 1000.0
NB = 720  # polar bins


# --------------------------------------------------------------------------- mask
def fg_mask(rgb):
    """Hard foreground mask: flood fill of 'smooth near-white' from the borders."""
    f = rgb.astype(np.float32)
    lum = f.mean(2)
    sat = f.max(2) - f.min(2)
    g = cv2.GaussianBlur(lum, (0, 0), 1.5)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1)
    grad = np.hypot(gx, gy) / 8
    cand = ((lum >= 206) & (sat < 14) & (grad < 5)).astype(np.uint8)
    n, lab = cv2.connectedComponents(cand, connectivity=4)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    bg = np.isin(lab, list(border))
    fg = (~bg).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(fg)
    k = 1 + np.argmax(st[1:, 4])
    fg = (lab == k).astype(np.uint8)
    cnt, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = np.zeros_like(fg)
    cv2.drawContours(out, cnt, -1, 1, -1)
    return out


def extend_colors(rgb, valid, iters):
    """Fill pixels where valid==0 from neighbouring valid pixels (normalised convolution)."""
    img = rgb.astype(np.float32)
    v = valid.astype(np.float32)
    acc = img * v[..., None]
    w = v.copy()
    for _ in range(iters):
        a = cv2.blur(acc, (3, 3))
        b = cv2.blur(w, (3, 3))
        new = (a / np.maximum(b, 1e-6)[..., None])
        fill = (w < 0.5) & (b > 1e-6)
        img = np.where(fill[..., None], new, img)
        w = np.where(fill, 1.0, w)
        acc = img * w[..., None]
    return img


# --------------------------------------------------------------------------- geometry
def case_geom(m):
    ys = np.where(m.any(1))[0]
    y0, y1 = int(ys[0]), int(ys[-1])
    L = np.full(m.shape[0], 1e9)
    R = np.full(m.shape[0], -1e9)
    for y in ys:
        xs = np.where(m[y])[0]
        L[y], R[y] = xs[0], xs[-1]
    yy = int(y0 + 0.04 * (y1 - y0))
    cx = (L[yy] + R[yy]) / 2
    lcase = np.percentile(L[ys], 1)
    hc = cx - lcase
    rows = np.where(L <= lcase + 0.05 * hc)[0]
    return dict(cx=float(cx), yc=float((rows.min() + rows.max()) / 2), hc=float(hc),
                y0=y0, y1=y1, lcase=float(lcase))


def edge_map(rgb):
    lab = cv2.cvtColor(cv2.GaussianBlur(rgb, (0, 0), 1.2), cv2.COLOR_RGB2LAB).astype(np.float32)
    g = np.zeros(lab.shape[:2], np.float32)
    for c in range(3):
        gx = cv2.Sobel(lab[..., c], cv2.CV_32F, 1, 0)
        gy = cv2.Sobel(lab[..., c], cv2.CV_32F, 0, 1)
        g += gx ** 2 + gy ** 2
    return np.sqrt(g)


def superellipse(p, n_pts=360):
    cx, cy, a, b, n = p
    t = np.linspace(0, 2 * np.pi, n_pts, endpoint=False)
    c, s = np.cos(t), np.sin(t)
    r = (np.abs(c / a) ** n + np.abs(s / b) ** n) ** (-1.0 / n)
    return cx + r * c, cy + r * s


def fit_seed(rgb, geo):
    """Coarse superellipse fit (maximises mean edge strength along the contour)."""
    E = edge_map(rgb)
    clip = np.percentile(E, 98)
    hc = geo["hc"]

    def score(p):
        x, y = superellipse(p)
        v = cv2.remap(E, x.astype(np.float32)[None], y.astype(np.float32)[None],
                      cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)[0]
        return np.minimum(v, clip).mean()

    p0 = np.array([geo["cx"], geo["yc"], 0.66 * hc, 0.66 * hc, 3.5])
    lo = np.array([p0[0] - 0.08 * hc, p0[1] - 0.12 * hc, 0.55 * hc, 0.55 * hc, 2.4])
    hi = np.array([p0[0] + 0.08 * hc, p0[1] + 0.12 * hc, 0.78 * hc, 0.78 * hc, 5.5])
    p, s = p0.copy(), score(p0)
    steps = np.array([0.03 * hc, 0.03 * hc, 0.03 * hc, 0.03 * hc, 0.4])
    for _ in range(60):
        imp = False
        for i in range(5):
            for d in (-1, 1):
                q = p.copy()
                q[i] = np.clip(q[i] + d * steps[i], lo[i], hi[i])
                sq = score(q)
                if sq > s + 1e-6:
                    p, s, imp = q, sq, True
        if not imp:
            steps *= 0.5
            if steps[0] < 0.4:
                break
    return p


def dial_contour(rgb, geo, p):
    """Free-form closed contour of the dial opening (dynamic programming in polar space)."""
    hc = geo["hc"]
    cx, cy = p[0], p[1]
    lab = cv2.cvtColor(cv2.GaussianBlur(rgb, (0, 0), 1.0), cv2.COLOR_RGB2LAB).astype(np.float32)
    th = np.linspace(0, 2 * np.pi, NB, endpoint=False)
    rs = np.arange(0.52 * hc, 0.78 * hc, 1.0)
    X = (cx + np.cos(th)[:, None] * rs[None]).astype(np.float32)
    Y = (cy + np.sin(th)[:, None] * rs[None]).astype(np.float32)
    P = np.stack([cv2.remap(lab[..., c], X, Y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
                  for c in range(3)], -1)
    k = 3
    Ed = np.zeros(P.shape[:2], np.float32)
    Ed[:, k:-k] = np.linalg.norm(P[:, 2 * k:] - P[:, :-2 * k], axis=-1)
    clip = np.percentile(Ed, 97)
    Ed = np.minimum(Ed, clip) / clip
    a = 0.635 * hc
    c, s = np.cos(th), np.sin(th)
    r0 = (np.abs(c) ** 3.3 + np.abs(s) ** 3.3) ** (-1 / 3.3) * a
    cost = -Ed + 3.0 * np.abs(rs[None] - r0[:, None]) / hc
    T = np.concatenate([cost, cost, cost], 0)
    n, R = T.shape
    acc = np.zeros_like(T)
    bk = np.zeros(T.shape, np.int16)
    acc[0] = T[0]
    for i in range(1, n):
        best = acc[i - 1].copy()
        arg = np.zeros(R, np.int16)
        for d, pen in ((-1, 0.05), (1, 0.05), (-2, 0.2), (2, 0.2)):
            sh = np.full(R, 1e9, np.float32)
            if d > 0:
                sh[d:] = acc[i - 1][:-d] + pen
            else:
                sh[:d] = acc[i - 1][-d:] + pen
            mm = sh < best
            best = np.where(mm, sh, best)
            arg = np.where(mm, d, arg)
        acc[i] = best + T[i]
        bk[i] = arg
    j = int(np.argmin(acc[-1]))
    path = np.zeros(n, int)
    path[-1] = j
    for i in range(n - 1, 0, -1):
        path[i - 1] = path[i] - bk[i][path[i]]
    r = rs[path[NB:2 * NB]]
    rp = np.pad(r, 6, mode="wrap")
    r = np.convolve(rp, np.ones(9) / 9, "valid")[:NB]
    return np.stack([cx + np.cos(th) * r, cy + np.sin(th) * r], 1)


def poly_centroid(pts):
    x, y = pts[:, 0], pts[:, 1]
    x1, y1 = np.roll(x, -1), np.roll(y, -1)
    cr = x * y1 - x1 * y
    A = cr.sum() / 2
    return (((x + x1) * cr).sum() / (6 * A), ((y + y1) * cr).sum() / (6 * A))


def find_cuts(rgb, cx, cy, hc):
    """Rows where the case lug block meets the first bracelet link / the leather strap."""
    g = cv2.GaussianBlur(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32), (0, 0), 1.2)
    gy = np.abs(cv2.Sobel(g, cv2.CV_32F, 0, 1))
    xa = [(int(cx - 0.58 * hc), int(cx - 0.42 * hc)), (int(cx + 0.42 * hc), int(cx + 0.58 * hc))]
    prof = sum(gy[:, a:b].mean(1) for a, b in xa)
    prof = cv2.GaussianBlur(prof[:, None].astype(np.float32), (1, 0), sigmaX=0.1, sigmaY=2)[:, 0]
    res = []
    for sgn, (k0, k1) in ((-1, (0.90, 1.12)), (1, (0.98, 1.20))):
        ys = np.sort(np.arange(int(cy + sgn * k0 * hc), int(cy + sgn * k1 * hc), sgn))
        res.append(int(ys[np.argmax(prof[ys])]))
    return res  # [top, bottom]


# --------------------------------------------------------------------------- warps
def polar_interp(table, ang):
    """table: radius per bin over [0,2pi); ang in radians (any shape)."""
    t = np.linspace(0, 2 * np.pi, len(table), endpoint=False)
    tt = np.concatenate([t, [2 * np.pi]])
    tb = np.concatenate([table, [table[0]]])
    return np.interp(np.mod(ang, 2 * np.pi), tt, tb)


def radii_table(pts_rel):
    ang = np.mod(np.arctan2(pts_rel[:, 1], pts_rel[:, 0]), 2 * np.pi)
    r = np.hypot(pts_rel[:, 0], pts_rel[:, 1])
    o = np.argsort(ang)
    ang, r = ang[o], r[o]
    t = np.linspace(0, 2 * np.pi, NB, endpoint=False)
    return np.interp(t, np.concatenate([ang - 2 * np.pi, ang, ang + 2 * np.pi]),
                     np.concatenate([r, r, r]))


def fwd_vert(dy, dt, db, Dt, Db):
    out = np.where(dy < 0,
                   np.where(dy >= -dt, dy * (Dt / dt), dy + dt - Dt),
                   np.where(dy <= db, dy * (Db / db), dy - db + Db))
    return out


def inv_vert(dy2, dt, db, Dt, Db):
    return np.where(dy2 < 0,
                    np.where(dy2 >= -Dt, dy2 * (dt / Dt), dy2 - dt + Dt),
                    np.where(dy2 <= Db, dy2 * (db / Db), dy2 + db - Db))


LS, LC = 170.0, 230.0   # px over which the join-width correction fades out (strap side / case side)


def hscale(dy, f_ts, f_tc, f_bs, f_bc, Dt, Db):
    """Horizontal scale factor (about the canvas centre line) as a function of the row in
    post-vertical-warp coordinates: makes strap and lug have the SAME width at the cut."""
    sm = lambda t: t * t * (3 - 2 * t)
    f = np.ones_like(dy)
    d = -Dt - dy
    f = np.where(d > 0, 1 + (f_ts - 1) * (1 - sm(np.clip(d / LS, 0, 1))), f)
    d = dy + Dt
    f = np.where((d >= 0) & (dy < 0), 1 + (f_tc - 1) * (1 - sm(np.clip(d / LC, 0, 1))), f)
    d = dy - Db
    f = np.where(d > 0, 1 + (f_bs - 1) * (1 - sm(np.clip(d / LS, 0, 1))), f)
    d = Db - dy
    f = np.where((d >= 0) & (dy >= 0), 1 + (f_bc - 1) * (1 - sm(np.clip(d / LC, 0, 1))), f)
    return f


def row_width(hard, y0, y1):
    ws = []
    for y in range(max(y0, 0), min(y1, hard.shape[0] - 1) + 1):
        xs = np.where(hard[y])[0]
        if len(xs):
            ws.append(xs[-1] - xs[0])
    return float(np.mean(ws)) if ws else None


def fit_superellipse_radii(R):
    """Smooth canonical opening: superellipse |x/a|^n + |y/b|^n = 1 fitted to the mean radii."""
    t = np.linspace(0, 2 * np.pi, NB, endpoint=False)
    c, s_ = np.abs(np.cos(t)), np.abs(np.sin(t))
    a0, b0 = R[0], R[NB // 4]
    best = (1e18, None)
    for n in np.arange(2.4, 5.01, 0.05):
        for a in np.arange(a0 * 0.92, a0 * 1.08, 0.5):
            for b in np.arange(b0 * 0.92, b0 * 1.08, 0.5):
                r = (np.power(c / a, n) + np.power(s_ / b, n)) ** (-1.0 / n)
                e = np.mean((r - R) ** 2)
                if e < best[0]:
                    best = (e, (a, b, n, r))
    a, b, n, r = best[1]
    print("canonical opening superellipse a=%.1f b=%.1f n=%.2f  rms err vs mean contour %.2f px" % (
        a, b, n, np.sqrt(best[0])))
    return r


# --------------------------------------------------------------------------- colour
def to_lin(x):
    return (x / 255.0) ** 2.2


def to_srgb(x):
    return 255.0 * np.clip(x, 0, 1) ** (1 / 2.2)


def lum(c):
    return float(np.dot(c, [0.299, 0.587, 0.114]))


def classify_metal(c):
    """Material guess from a median RGB of the metal."""
    c = np.asarray(c, float)
    if lum(c) < 85:
        return "black"
    if c[0] - c[2] > 28:
        return "rose"
    return "steel"


def unsharp(rgb, sigma=1.3, amount=0.45):
    f = rgb.astype(np.float32)
    b = cv2.GaussianBlur(f, (0, 0), sigma)
    return np.clip(f + amount * (f - b), 0, 255)


# --------------------------------------------------------------------------- main
def main():
    files = sorted(glob.glob(os.path.join(SRC, "*")))
    files = [f for f in files if f.lower().endswith((".png", ".jpg", ".jpeg"))]
    os.makedirs(OUT, exist_ok=True)
    target_w = CASE_MM * PX_PER_MM  # canvas px of the case width
    items = []

    # ---- pass 1: geometry in canvas units
    for i, f in enumerate(files):
        pid = "naut-%02d" % (i + 1)
        rgb = np.array(Image.open(f).convert("RGB"))
        hard = fg_mask(rgb)
        geo = case_geom(hard)
        p = fit_seed(rgb, geo)
        pts = dial_contour(rgb, geo, p)
        cx, cy = poly_centroid(pts)
        yt, yb = find_cuts(rgb, cx, cy, geo["hc"])
        s = (target_w / 2) / geo["hc"]
        it = dict(id=pid, file=f, rgb=rgb, hard=hard, geo=geo, pts=pts, cx=cx, cy=cy,
                  yt=yt, yb=yb, s=s)
        it["dt"] = (cy - yt) * s
        it["db"] = (yb - cy) * s
        items.append(it)
        print("%s %-14s dial centroid=(%.1f,%.1f) bbox x[%.0f..%.0f] y[%.0f..%.0f] (w=%.0f h=%.0f src px) "
              "cuts y=%d/%d  scale=%.3f" % (pid, os.path.basename(f), cx, cy, pts[:, 0].min(), pts[:, 0].max(),
                                          pts[:, 1].min(), pts[:, 1].max(), np.ptp(pts[:, 0]), np.ptp(pts[:, 1]),
                                          yt, yb, s))
    Dt = float(np.median([it["dt"] for it in items]))
    Db = float(np.median([it["db"] for it in items]))
    print("canonical cut distance from dial centre (canvas px): top %.1f  bottom %.1f" % (Dt, Db))

    # post-vertical-warp dial radii per photo
    for it in items:
        rel = (it["pts"] - [it["cx"], it["cy"]]) * it["s"]
        rel[:, 1] = fwd_vert(rel[:, 1], it["dt"], it["db"], Dt, Db)
        it["R"] = radii_table(rel)
    Rcan = np.mean([it["R"] for it in items], 0)
    # symmetrise (left-right and top-bottom): cushion shape of the model
    t = np.linspace(0, 2 * np.pi, NB, endpoint=False)
    sym = (Rcan + polar_interp(Rcan, np.pi - t) + polar_interp(Rcan, -t) + polar_interp(Rcan, np.pi + t)) / 4
    Rcan = np.convolve(np.pad(sym, 4, mode="wrap"), np.ones(5) / 5, "valid")[:NB]
    Rcan = fit_superellipse_radii(Rcan)
    print("canonical dial: width %.0f px (%.1f mm) height %.0f px (%.1f mm)" % (
        2 * Rcan[0], 2 * Rcan[0] / PX_PER_MM, 2 * Rcan[NB // 4], 2 * Rcan[NB // 4] / PX_PER_MM))

    # join widths: lug (case side) and strap side of each cut, canonical = median lug width
    for it in items:
        h, yt, yb, s = it["hard"], it["yt"], it["yb"], it["s"]
        it["wl_t"] = (row_width(h, yt + 4, yt + 10) or 0) * s
        it["ws_t"] = (row_width(h, yt - 10, yt - 4) or 0) * s
        it["wl_b"] = (row_width(h, yb - 10, yb - 4) or 0) * s
        it["ws_b"] = (row_width(h, yb + 4, yb + 10) or 0) * s
    WLt = float(np.median([it["wl_t"] for it in items]))
    WLb = float(np.median([it["wl_b"] for it in items]))
    print("canonical lug width at cuts: top %.0f px, bottom %.0f px" % (WLt, WLb))
    clipf = lambda v: float(np.clip(v, 0.88, 1.12))
    for it in items:
        it["f_tc"] = clipf(WLt / it["wl_t"]) if it["wl_t"] else 1.0
        it["f_ts"] = clipf(WLt / it["ws_t"]) if it["ws_t"] else 1.0
        it["f_bc"] = clipf(WLb / it["wl_b"]) if it["wl_b"] else 1.0
        it["f_bs"] = clipf(WLb / it["ws_b"]) if it["ws_b"] else 1.0
        print("%s join widths top lug/strap %.0f/%.0f bottom lug/strap %.0f/%.0f -> scale case %.3f/%.3f strap %.3f/%.3f"
              % (it["id"], it["wl_t"], it["ws_t"], it["wl_b"], it["ws_b"], it["f_tc"], it["f_bc"], it["f_ts"], it["f_bs"]))

    # canvas helper grids
    uu, vv = np.meshgrid(np.arange(CW, dtype=np.float32), np.arange(CH, dtype=np.float32))
    dx, dy = uu - CX0, vv - CY0
    ang = np.arctan2(dy, dx)
    rr = np.hypot(dx, dy)
    Rc_map = polar_interp(Rcan, ang).astype(np.float32)
    pts_can = np.stack([CX0 + np.cos(t) * Rcan, CY0 + np.sin(t) * Rcan], 1)
    inside = np.zeros((CH, CW), np.uint8)
    cv2.fillPoly(inside, [np.round(pts_can * 16).astype(np.int32)], 1, lineType=cv2.LINE_8, shift=4)
    sd = (cv2.distanceTransform(inside, cv2.DIST_L2, 5) -
          cv2.distanceTransform(1 - inside, cv2.DIST_L2, 5)).astype(np.float32)  # >0 inside
    ytop_row = int(round(CY0 - Dt))
    ybot_row = int(round(CY0 + Db))
    vi = np.arange(CH)[:, None] * np.ones((1, CW))
    band = ((vi >= ytop_row) & (vi <= ybot_row)).astype(np.float32)
    strap_rows = ((vi < ytop_row) | (vi > ybot_row)).astype(np.float32)  # no overlap: rows are exclusive
    # the case opening is grown 2 px outwards (eats the dark glass-rim line, whose width varies
    # between photos) and the dial is extended 8 px outwards, hidden under the case
    GROW, UNDER = 12.0, 22.0
    hole = np.clip(sd + GROW + 0.5, 0, 1)      # case opening (dial visible)
    dial_a = np.clip(sd + UNDER + 0.5, 0, 1)   # dial extends under the case
    ring_case = (sd < -10) & (sd > -90)        # flat bezel area for exposure sampling

    # ---- pass 2: warp, split, sample metal
    for it in items:
        s = it["s"]
        rgb, hard = it["rgb"], it["hard"]
        h0, w0 = hard.shape
        nw, nh = int(round(w0 * s)), int(round(h0 * s))
        interp = cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC
        rgb_s = cv2.resize(rgb, (nw, nh), interpolation=interp)
        # soft alpha: erode 1.2px (kills the white fringe), gentle blur, decontaminate colour
        hs = cv2.resize(hard.astype(np.float32), (nw, nh), interpolation=cv2.INTER_AREA)
        hs = (hs > 0.5).astype(np.uint8)
        er = cv2.erode(hs, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
        alpha_s = cv2.GaussianBlur(er.astype(np.float32), (0, 0), 0.9)
        inner = cv2.erode(hs, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
        rgb_s = extend_colors(rgb_s, inner, 3)
        # backward maps canvas -> scaled source
        r_src = polar_interp(it["R"], ang).astype(np.float32)
        rfar = np.maximum(r_src, Rc_map) + 0.25 * target_w / 2
        r_in = np.where(rr <= Rc_map, rr * r_src / np.maximum(Rc_map, 1e-3),
                        np.where(rr < rfar, r_src + (rr - Rc_map) * (rfar - r_src) / (rfar - Rc_map), rr))
        k = r_in / np.maximum(rr, 1e-3)
        dx2, dy2 = dx * k, dy * k
        dy3 = inv_vert(dy2, it["dt"], it["db"], Dt, Db)
        fx = hscale(dy2, it["f_ts"], it["f_tc"], it["f_bs"], it["f_bc"], Dt, Db)
        mapx = (it["cx"] * s + dx2 / fx).astype(np.float32)
        mapy = (it["cy"] * s + dy3).astype(np.float32)
        warp = cv2.remap(rgb_s.astype(np.float32) * alpha_s[..., None], mapx, mapy, cv2.INTER_LANCZOS4,
                         borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        a = cv2.remap(alpha_s, mapx, mapy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        a = np.clip(a, 0, 1)
        col = np.where(a[..., None] > 1e-3, warp / np.maximum(a, 1e-3)[..., None], 0)
        col = np.clip(col, 0, 255).astype(np.float32)
        it["col"], it["alpha"] = col, a
        # metal samples
        case_px = (ring_case & (band > 0) & (a > 0.99))
        it["case_med"] = np.median(col[case_px], 0)
        strap_top = (vv < ytop_row - 5) & (vv > ytop_row - 260) & (a > 0.99)
        strap_bot = (vv > ybot_row + 5) & (vv < ybot_row + 260) & (a > 0.99)
        sp = strap_top | strap_bot
        sc = col[sp]
        it["strap_med"] = np.median(sc, 0)
        sat = sc.max(1) - sc.min(1)
        l = sc.mean(1)
        it["strap_spec"] = float(((l > 205) & (sat < 30)).mean())
        # strap contact: does the photo run into the image border (truncated strap)?
        it["trunc_top"] = it["geo"]["y0"] <= 6
        it["trunc_bot"] = it["geo"]["y1"] >= h0 - 7
        # dial look
        dm = (sd > 30) & (a > 0.5)
        it["dial_rgb"] = np.median(col[dm], 0)

    # ---- classify materials, compute normalisation targets
    for it in items:
        it["case_mat"] = classify_metal(it["case_med"])
        sm = it["strap_med"]
        spec = it["strap_spec"]
        l = lum(sm)
        if l < 95 and it["case_mat"] != "black":
            kind, mat = "leather", ("black" if abs(sm[2] - sm[0]) < 12 and sm[2] < 70 else
                                    "blue" if sm[2] > sm[0] + 6 else "brown")
        elif l < 95 and it["case_mat"] == "black":
            kind, mat = "bracelet", "black"  # black PVD case: only a PVD bracelet in this set
        elif sm[0] - sm[2] > 28 and l < 120:
            kind, mat = "leather", "brown"
        else:
            kind, mat = "bracelet", classify_metal(sm)
        it["strap_kind"], it["strap_mat"] = kind, mat
    tgt = {}
    for mat in ("steel", "rose", "black"):
        meds = [it["case_med"] for it in items if it["case_mat"] == mat]
        meds += [it["strap_med"] for it in items if it["strap_kind"] == "bracelet" and it["strap_mat"] == mat]
        if not meds:
            continue
        m = np.mean(meds, 0)
        if mat == "steel":
            m = np.array([lum(m)] * 3)  # neutral grey, common luminance
        tgt[mat] = m
    print("normalisation targets (RGB):", {k: np.round(v, 1).tolist() for k, v in tgt.items()})

    # ---- pass 3: normalise, sharpen, split, write
    layers = {}
    meta = []
    for it in items:
        col, a = it["col"].copy(), it["alpha"]
        lin = to_lin(col)

        def gain(med, mat):
            g = to_lin(tgt[mat]) / to_lin(np.maximum(med, 1))
            return np.clip(g, 0.6, 1.7)

        gcase = gain(it["case_med"], it["case_mat"])
        hole_i = hole  # ONE canonical opening for every case
        reg_case = (band * (1 - hole_i))[..., None]
        out = lin.copy()
        out = np.where(reg_case > 0, lin * gcase, out)
        if it["strap_kind"] == "bracelet":
            gs = gain(it["strap_med"], it["strap_mat"])
            reg_strap = (1 - band)[..., None]
            out = np.where(reg_strap > 0, lin * gs, out)
        else:
            gs = np.ones(3)
        col_n = to_srgb(out)
        col_n = unsharp(col_n)
        # open heart: stripes are horizontal and give weak horizontal gradients; a skeleton
        # movement (left/below the centre) gives many strong ones
        gimg = cv2.GaussianBlur(cv2.cvtColor(np.clip(col_n, 0, 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
                                .astype(np.float32), (0, 0), 1.2)
        gxa = np.abs(cv2.Sobel(gimg, cv2.CV_32F, 1, 0)) / 8
        it["open_ratio"] = float((gxa[970:1300, 215:450] > 8).mean())
        it["open_heart"] = it["open_ratio"] > OPEN_THR
        d = os.path.join(OUT, it["id"])
        os.makedirs(d, exist_ok=True)

        def save(name, c, al):
            rgba = np.dstack([np.clip(c, 0, 255), np.clip(al, 0, 1) * 255]).astype(np.uint8)
            Image.fromarray(rgba).save(os.path.join(d, name), optimize=True)
            return rgba

        strap_a = a * strap_rows
        case_a = a * band * (1 - hole_i)
        # dial: pure dial pixels only (sd>=3), then extended outwards under the case
        valid = (sd >= 11) & (a > 0.99)  # skip the photo's own glass rim (up to ~10 px inside the detected edge)
        dcol = extend_colors(col_n, valid, 36)
        dial_alpha = dial_a
        save("strap.png", col_n, strap_a)
        save("case.png", col_n, case_a)
        save("dial.png", dcol, dial_alpha)
        layers[it["id"]] = dict(strap=(col_n.astype(np.uint8), strap_a.astype(np.float32)),
                                case=(col_n.astype(np.uint8), case_a.astype(np.float32)),
                                dial=(np.clip(dcol, 0, 255).astype(np.uint8), dial_alpha.astype(np.float32)))
        it["gcase"], it["gstrap"] = gcase, gs
        it["col_n"] = col_n
    # shared inner shadow of the dial opening (light from top-left: stronger on top/left edge)
    ins = (sd > -GROW).astype(np.float32)
    outside = 1 - ins
    M = np.float32([[1, 0, 3], [0, 1, 6]])
    sh = cv2.warpAffine(outside, M, (CW, CH), borderValue=1)
    sh = cv2.GaussianBlur(sh, (0, 0), 8)
    near = np.exp(-np.maximum(sd + GROW, 0) / 3.0)
    sh_a = np.clip(0.34 * sh * ins + 0.09 * near * ins, 0, 0.45)
    shadow = np.dstack([np.zeros((CH, CW, 3), np.uint8), (sh_a * 255).astype(np.uint8)])
    Image.fromarray(shadow).save(os.path.join(OUT, "shadow-dial.png"))

    def compose(strap_id, dial_id, case_id, bg=255):
        canvas = np.full((CH, CW, 3), float(bg), np.float32)
        for (c, al) in (layers[strap_id]["strap"], layers[dial_id]["dial"]):
            canvas = c * al[..., None] + canvas * (1 - al[..., None])
        canvas = 0 * canvas + canvas * (1 - sh_a[..., None])  # black shadow overlay
        c, al = layers[case_id]["case"]
        canvas = c * al[..., None] + canvas * (1 - al[..., None])
        return canvas

    # stack proof (+ difference against the warped, normalised, sharpened photo)
    for it in items:
        st = compose(it["id"], it["id"], it["id"])
        # reference: same photo, same shadow, white bg
        ref = it["col_n"] * it["alpha"][..., None] + 255 * (1 - it["alpha"][..., None])
        # reference inner shadow applied at the same place for a fair comparison
        ref = ref * (1 - sh_a[..., None] * (sd > -GROW)[..., None])
        diff = np.abs(st - ref).mean(2)
        fgm = it["alpha"] > 0.5
        it["stack_err"] = float(diff[fgm].mean())
        it["stack_err_edge"] = float(np.percentile(diff[fgm], 99.5))
        # transparent stack
        al = np.zeros((CH, CW), np.float32)
        # premultiplied over-compositing
        pm = np.zeros((CH, CW, 3), np.float32)
        for (cc, aa) in (layers[it["id"]]["strap"], layers[it["id"]]["dial"], ("shadow", None),
                         layers[it["id"]]["case"]):
            if isinstance(cc, str):
                aa = sh_a
                cc = np.zeros((CH, CW, 3), np.float32)
            pm = cc * aa[..., None] + pm * (1 - aa[..., None])
            al = aa + al * (1 - aa)
        rgba = np.dstack([np.clip(pm / np.maximum(al, 1e-4)[..., None], 0, 255), al * 255]).astype(np.uint8)
        Image.fromarray(rgba).save(os.path.join(OUT, it["id"], "stack.png"), optimize=True)
        print("%s stack vs warped photo: mean |diff| = %.2f  p99.5 = %.1f" % (it["id"], it["stack_err"],
                                                                          it["stack_err_edge"]))
        # bbox of dial in canvas / mm
    # ---- partes.json
    out = []
    for it in items:
        flags = []
        if it["trunc_top"] or it["trunc_bot"]:
            flags.append("strap_truncated_at_photo_edge(%s)" % ("top" if it["trunc_top"] else "bottom"))
        if it["id"] == "naut-19":
            flags.append("original_jpg_896x1200_upscaled_x%.2f" % it["s"])
        if it["open_heart"]:
            flags.append("open_heart")
        if it["strap_kind"] == "leather":
            flags.append("leather_strap_lug_proportions_differ")
        if abs(it["s"] - np.median([x["s"] for x in items])) / np.median([x["s"] for x in items]) > 0.08:
            flags.append("case_scale_outlier")
        out.append(dict(
            id=it["id"], source=os.path.relpath(it["file"], ROOT), types=["strap", "case", "dial"],
            files=dict(strap="%s/strap.png" % it["id"], case="%s/case.png" % it["id"],
                       dial="%s/dial.png" % it["id"], stack="%s/stack.png" % it["id"]),
            case=dict(material=it["case_mat"], median_rgb=np.round(it["case_med"]).astype(int).tolist()),
            strap=dict(kind=it["strap_kind"], material=it["strap_mat"],
                       median_rgb=np.round(it["strap_med"]).astype(int).tolist()),
            dial=dict(median_rgb=np.round(it["dial_rgb"]).astype(int).tolist(),
                      hex="#%02x%02x%02x" % tuple(np.round(it["dial_rgb"]).astype(int)),
                      open_heart=bool(it["open_heart"]), open_heart_ratio=round(it["open_ratio"], 3),
                      src_bbox=[round(float(x), 1) for x in (it["pts"][:, 0].min(), it["pts"][:, 1].min(),
                                                            it["pts"][:, 0].max(), it["pts"][:, 1].max())]),
            geometry=dict(scale=round(it["s"], 4), src_case_half_width=round(it["geo"]["hc"], 1),
                          src_dial_centre=[round(it["cx"], 1), round(it["cy"], 1)],
                          src_cut_rows=[it["yt"], it["yb"]],
                          gain_case=np.round(it["gcase"], 3).tolist(), gain_strap=np.round(it["gstrap"], 3).tolist()),
            stack_check=dict(mean_abs_diff=round(it["stack_err"], 3), p995=round(it["stack_err_edge"], 2)),
            flags=flags))
    canon = dict(canvas=[CW, CH], px_per_mm=round(PX_PER_MM, 4), case_mm=CASE_MM, dial_centre=[CX0, CY0],
                 dial_bbox=[round(CX0 - Rcan[0]), round(CY0 - Rcan[NB // 4]),
                            round(CX0 + Rcan[0]), round(CY0 + Rcan[NB // 4])],
                 cut_rows=[ytop_row, ybot_row], shadow="shadow-dial.png",
                 z_order=["strap", "dial", "shadow-dial", "case"])
    with open(os.path.join(OUT, "partes.json"), "w") as fh:
        json.dump(dict(canvas=canon, parts=out), fh, indent=2, ensure_ascii=False)

    # ---- catalogue + mixes
    def label(img, text):
        d = ImageDraw.Draw(img)
        try:
            ft = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
        except Exception:
            ft = ImageFont.load_default()
        d.rectangle([0, 0, img.width, 30], fill=(255, 255, 255))
        d.text((6, 3), text, fill=(0, 0, 0), font=ft)
        return img

    tw, th_ = 300, 600
    cols = 7
    rows_ = (len(items) + cols - 1) // cols
    sheet = Image.new("RGB", (tw * cols, th_ * rows_), "white")
    for k, it in enumerate(items):
        st = np.clip(compose(it["id"], it["id"], it["id"]), 0, 255).astype(np.uint8)
        im = Image.fromarray(st).resize((tw, th_), Image.LANCZOS)
        tag = "%s %s/%s/%s%s" % (it["id"], it["case_mat"], it["strap_kind"][:4] + "-" + it["strap_mat"],
                                 "heart" if it["open_heart"] else "dial", "")
        sheet.paste(label(im, tag), ((k % cols) * tw, (k // cols) * th_))
    sheet.save(os.path.join(OUT, "catalogo.jpg"), quality=90)

    ids = {it["id"]: it for it in items}
    by_src = {os.path.basename(it["file"]): it["id"] for it in items}
    mixes = [
        ("caja negra PVD + esfera rosa + brazalete acero", by_src["imagen-10.png"], by_src["enlace-03.png"], by_src["imagen-02.png"]),
        ("caja oro rosa + esfera azul + piel marron", by_src["imagen-17.png"], by_src["enlace-02.png"], by_src["imagen-08.png"]),
        ("caja acero + esfera teal open heart + piel negra", by_src["imagen-16.png"], by_src["imagen-14.png"], by_src["imagen-10.png"]),
        ("caja acero + esfera amarillo-verde + brazalete oro rosa", by_src["imagen-18.png"], by_src["enlace-01.png"], by_src["enlace-02.png"]),
    ]
    mw, mh = 500, 1000
    msheet = Image.new("RGB", (mw * 4, mh), "white")
    for k, (name, sid, did, cid) in enumerate(mixes):
        st = np.clip(compose(sid, did, cid), 0, 255).astype(np.uint8)
        Image.fromarray(st).save(os.path.join(OUT, "mezcla-%d.png" % (k + 1)))
        im = Image.fromarray(st).resize((mw, mh), Image.LANCZOS)
        msheet.paste(label(im, "%d: strap %s / dial %s / case %s" % (k + 1, sid, did, cid)), (k * mw, 0))
        print("mezcla %d: %s -> strap %s dial %s case %s" % (k + 1, name, sid, did, cid))
    msheet.save(os.path.join(OUT, "mezclas.jpg"), quality=92)
    print("done ->", OUT)


OPEN_THR = 0.165

if __name__ == "__main__":
    sys.exit(main())
